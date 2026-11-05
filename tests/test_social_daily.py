import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from services.social.store import Store, Conflict
from services.social.daily import DailyScheduler, validate_config, ready_content


def instant(value):
    return datetime.fromisoformat(value).timestamp()


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'social.db')
        self.items = []
        for index in range(3):
            path = self.root / f'{index}.mp4'
            path.write_bytes(f'video-{index}'.encode())
            self.items.append({'id':f'video-{index}', 'caption':f'Existing caption #{index}', 'media_path':str(path)})
        owner = self.store.begin_login('facebook', now=1)
        self.store.complete_login('facebook', owner, 'personal-account', now=2)
        self.config = {'enabled':True,'times':['08:00','12:00'],'timezone':'Asia/Bangkok',
                       'selection':'fifo','made_for_kids':False}
        self.store.save_daily(self.config, now=instant('2026-11-04T07:00:00+07:00'))
        self.scheduler = DailyScheduler(self.store, lambda: self.items)

    def test_at_each_daily_time_take_one_unused_video_for_all_five_platforms(self):
        first = self.scheduler.tick(now=instant('2026-11-04T08:00:02+07:00'))
        self.assertEqual(first['video_id'], 'video-0')
        self.assertEqual(first['caption'], 'Existing caption #0')
        self.assertEqual(len(first['tasks']), 5)
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T08:00:04+07:00')))
        second = self.scheduler.tick(now=instant('2026-11-04T12:00:02+07:00'))
        self.assertEqual(second['video_id'], 'video-1')
        tomorrow = self.scheduler.tick(now=instant('2026-11-05T08:00:02+07:00'))
        self.assertEqual(tomorrow['video_id'], 'video-2')

    def test_concurrent_ticks_create_only_one_batch(self):
        now = instant('2026-11-04T08:00:02+07:00')
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: DailyScheduler(self.store, lambda: self.items).tick(now=now), range(2)))
        self.assertEqual(len(self.store.list_batches()), 1)

    def test_manual_history_is_excluded_even_if_cancelled(self):
        old = self.store.create_batch('video-0', self.items[0]['media_path'], 'caption', 1, False, 'manual-one')
        self.store.cancel_batch(old['id'])
        result = self.scheduler.tick(now=instant('2026-11-04T08:00:02+07:00'))
        self.assertEqual(result['video_id'], 'video-1')

    def test_empty_slot_does_not_publish_content_added_after_that_slot(self):
        self.items.clear()
        now = instant('2026-11-04T08:00:02+07:00')
        self.assertIsNone(self.scheduler.tick(now=now))
        self.assertEqual(self.store.daily_runs()[0]['state'], 'empty')
        self.items.append({'id':'later','caption':'later','media_path':str(self.root / '0.mp4')})
        self.assertIsNone(self.scheduler.tick(now=now + 5))
        self.assertEqual(len(self.store.list_batches()), 0)

    def test_downtime_skips_old_slots_instead_of_posting_a_burst(self):
        batch = self.scheduler.tick(now=instant('2026-11-04T12:05:00+07:00'))
        self.assertEqual(batch['video_id'], 'video-0')
        states = {r['slot_at']:r['state'] for r in self.store.daily_runs()}
        self.assertEqual(states[instant('2026-11-04T08:00:00+07:00')], 'skipped')
        self.assertEqual(len(self.store.list_batches()), 1)

    def test_more_than_fifteen_minutes_late_skips_without_consuming_video(self):
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T08:16:00+07:00')))
        result = self.scheduler.tick(now=instant('2026-11-04T12:00:00+07:00'))
        self.assertEqual(result['video_id'], 'video-0')

    def test_saving_settings_does_not_backfill_past_hours(self):
        self.store.save_daily(self.config, now=instant('2026-11-04T09:00:00+07:00'))
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T09:00:01+07:00')))
        self.assertEqual(self.store.daily_runs(), [])

    def test_pause_does_not_allocate_a_video(self):
        self.store.save_daily({**self.config, 'enabled':False}, now=instant('2026-11-04T07:01:00+07:00'))
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T08:00:00+07:00')))
        self.assertEqual(self.store.list_batches(), [])

    def test_crash_resumes_same_reserved_video(self):
        now = instant('2026-11-04T08:00:02+07:00')
        with patch.object(self.store, 'create_batch', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.scheduler.tick(now=now)
        recovered = DailyScheduler(self.store, lambda: list(reversed(self.items))).tick(now=now + 2)
        self.assertEqual(recovered['video_id'], 'video-0')
        self.assertEqual(len(self.store.list_batches()), 1)

    def test_crash_after_batch_creation_recovers_even_if_source_is_deleted(self):
        now = instant('2026-11-04T08:00:02+07:00')
        original = self.store.create_batch
        def create_then_crash(*args, **kwargs):
            original(*args, **kwargs)
            raise KeyboardInterrupt
        with patch.object(self.store, 'create_batch', side_effect=create_then_crash):
            with self.assertRaises(KeyboardInterrupt):
                self.scheduler.tick(now=now)
        self.items.clear()
        self.assertIsNotNone(self.scheduler.tick(now=now + 2))
        self.assertEqual(len(self.store.list_batches()), 1)
        self.assertEqual(self.store.daily_runs()[0]['state'], 'scheduled')

    def test_pause_during_snapshot_prevents_stale_batch_creation(self):
        original = self.store.create_batch
        def pause_then_create(*args, **kwargs):
            self.store.save_daily({**self.config,'enabled':False})
            return original(*args, **kwargs)
        with patch.object(self.store, 'create_batch', side_effect=pause_then_create):
            self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T08:00:02+07:00')))
        self.assertEqual(self.store.list_batches(), [])

    def test_random_policy_chooses_from_unused_candidates(self):
        self.store.save_daily({**self.config,'selection':'random'}, now=instant('2026-11-04T07:00:00+07:00'))
        with patch('services.social.daily.random.choice', return_value=self.items[2]):
            batch = self.scheduler.tick(now=instant('2026-11-04T08:00:00+07:00'))
        self.assertEqual(batch['video_id'], 'video-2')

    def test_no_connected_platform_does_not_consume_video(self):
        with self.store.transaction() as db:
            db.execute("UPDATE accounts SET state='disconnected'")
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T08:00:00+07:00')))
        self.assertEqual(self.store.daily_runs()[0]['state'], 'blocked')
        self.assertEqual(self.store.used_video_ids(), set())

    def test_validation_rejects_malformed_hours_and_requires_audience_when_enabled(self):
        for changes in [{'times':['25:00']}, {'times':['8:00']}, {'times':[]}, {'times':'08:00'},
                        {'enabled':'true'}, {'made_for_kids':None}, {'timezone':'Invalid/Zone'}, {'selection':'unknown'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_config({**self.config, **changes})
        validated = validate_config({**self.config,'times':['12:00','08:00','08:00']})
        self.assertEqual(validated['times'], ['08:00','12:00'])

    def test_candidate_discovery_only_includes_completed_safe_outputs(self):
        videos = [{'id':'one','status':'completed','title':'existing caption','output_filename':'0.mp4'},
                  {'id':'two','status':'processing','title':'no','output_filename':'1.mp4'},
                  {'id':'three','status':'completed','title':'no','output_filename':'../outside.mp4'}]
        self.assertEqual([v['id'] for v in ready_content(videos, self.root)], ['one'])

    def test_new_install_defaults_to_random_and_does_not_enable_posting(self):
        fresh = Store(self.root / 'fresh.db')
        self.assertEqual(fresh.get_daily()['selection'], 'random')
        self.assertFalse(fresh.get_daily()['enabled'])

    def test_random_selection_never_reuses_an_allocated_video(self):
        self.store.save_daily({**self.config,'selection':'random'}, now=instant('2026-11-04T07:00:00+07:00'))
        def choose_last(candidates):
            return candidates[-1]
        with patch('services.social.daily.random.choice', side_effect=choose_last):
            first = self.scheduler.tick(now=instant('2026-11-04T08:00:00+07:00'))
            second = self.scheduler.tick(now=instant('2026-11-04T12:00:00+07:00'))
        self.assertEqual(first['video_id'], 'video-2')
        self.assertEqual(second['video_id'], 'video-1')

    def test_slot_is_converted_from_chosen_timezone_not_host_timezone(self):
        self.assertIsNone(self.scheduler.tick(now=instant('2026-11-04T00:59:00+00:00')))
        batch = self.scheduler.tick(now=instant('2026-11-04T01:00:01+00:00'))
        self.assertEqual(batch['scheduled_at'], instant('2026-11-04T08:00:00+07:00'))

    def test_scheduler_thread_ticks_independently_of_browser_worker(self):
        import threading
        stop = threading.Event()
        done = threading.Event()
        def provider():
            done.set()
            stop.set()
            return self.items
        scheduler = DailyScheduler(self.store, provider)
        thread = threading.Thread(target=scheduler.run, args=(stop,))
        thread.start()
        self.assertTrue(done.wait(3))
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())


if __name__ == '__main__':
    unittest.main()
