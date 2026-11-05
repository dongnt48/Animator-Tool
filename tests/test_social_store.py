import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from services.social.store import Store, PLATFORMS, Conflict


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.media = self.root / 'video.mp4'
        self.media.write_bytes(b'rendered video')
        self.store = Store(self.root / 'social.sqlite3')

    def batch(self, key='request-one', at=1000):
        return self.store.create_batch('video-one', str(self.media), 'Caption #test', at, False, key)

    def connect(self, platform):
        owner = self.store.begin_login(platform, now=900)
        self.store.complete_login(platform, owner, 'account-one', now=901)

    def test_schedule_snapshots_caption_and_creates_five_independent_targets(self):
        batch = self.batch()
        self.assertEqual(batch['caption'], 'Caption #test')
        self.assertEqual({t['platform'] for t in batch['tasks']}, set(PLATFORMS))
        self.assertEqual(len(batch['tasks']), 5)
        self.assertTrue(batch['media_hash'])

    def test_request_key_is_idempotent_but_cannot_change_payload(self):
        first = self.batch()
        self.assertEqual(self.batch()['id'], first['id'])
        with self.assertRaises(Conflict):
            self.store.create_batch('other', str(self.media), 'changed', 1000, False, 'request-one')

    def test_claim_is_atomic_across_connections(self):
        self.batch()
        self.connect('facebook')
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda owner: Store(self.store.path).claim_next(owner, now=1000), ['one', 'two']))
        self.assertEqual(sum(t is not None for t in claims), 1)

    def test_not_due_jobs_do_not_start(self):
        self.batch(at=1100)
        self.connect('facebook')
        self.assertIsNone(self.store.claim_next('worker', now=1000))

    def test_missing_login_blocks_only_affected_platform(self):
        batch = self.batch()
        self.connect('youtube')
        task = self.store.claim_next('worker', now=1000)
        self.assertEqual(task['platform'], 'youtube')
        states = {t['platform']: t['state'] for t in self.store.get_batch(batch['id'])['tasks']}
        self.assertEqual(states['facebook'], 'needs_login')
        self.assertEqual(states['youtube'], 'running')

    def test_active_login_lease_prevents_double_profile_use(self):
        self.batch()
        self.store.begin_login('facebook', now=999)
        with self.assertRaises(Conflict):
            self.store.begin_login('facebook', now=1000)
        self.assertIsNone(self.store.claim_next('worker', now=1000))

    def test_restart_does_not_republish_ambiguous_submission(self):
        batch = self.batch()
        self.connect('facebook')
        task = self.store.claim_next('worker', now=1000)
        self.store.mark_submitting(task['id'], 'worker')
        self.store.recover_interrupted()
        saved = next(t for t in self.store.get_batch(batch['id'])['tasks'] if t['id'] == task['id'])
        self.assertEqual(saved['state'], 'needs_review')
        with self.assertRaises(Conflict):
            self.store.retry(task['id'], now=1001)
        self.store.retry(task['id'], confirmed_not_posted=True, now=1001)
        self.assertEqual(self.store.claim_next('next-worker', now=1001)['id'], task['id'])

    def test_wrong_owner_cannot_cross_publication_checkpoint(self):
        self.batch()
        self.connect('facebook')
        task = self.store.claim_next('worker', now=1000)
        with self.assertRaises(Conflict):
            self.store.mark_submitting(task['id'], 'imposter')

    def test_success_cannot_be_retried(self):
        self.batch()
        self.connect('facebook')
        task = self.store.claim_next('worker', now=1000)
        self.store.mark_submitting(task['id'], 'worker')
        self.store.finish(task['id'], 'worker', 'published', 'OK', 'https://www.facebook.com/reel/12345')
        with self.assertRaises(Conflict):
            self.store.retry(task['id'], confirmed_not_posted=True, now=1002)

    def test_downtime_over_fifteen_minutes_requires_review(self):
        batch = self.batch(at=1000)
        self.connect('facebook')
        self.assertIsNone(self.store.claim_next('worker', now=1901))
        self.assertEqual({t['state'] for t in self.store.get_batch(batch['id'])['tasks']}, {'needs_review'})

    def test_cancel_does_not_cancel_already_running_target(self):
        batch = self.batch()
        self.connect('facebook')
        task = self.store.claim_next('worker', now=1000)
        self.store.cancel_batch(batch['id'])
        states = {t['id']: t['state'] for t in self.store.get_batch(batch['id'])['tasks']}
        self.assertEqual(states[task['id']], 'running')
        self.assertTrue(all(s == 'cancelled' for key, s in states.items() if key != task['id']))

    def test_sessions_cannot_be_saved_after_lease_expires(self):
        owner = self.store.begin_login('facebook', now=1000)
        with self.assertRaises(Conflict):
            self.store.complete_login('facebook', owner, 'one', now=3000)

    def test_account_switch_after_scheduling_does_not_publish_to_new_identity(self):
        self.connect('facebook')
        batch = self.batch()
        owner = self.store.begin_login('facebook', now=950)
        self.store.complete_login('facebook', owner, 'different-account', now=951)
        self.assertIsNone(self.store.claim_next('worker', now=1000))
        facebook = next(t for t in self.store.get_batch(batch['id'])['tasks'] if t['platform'] == 'facebook')
        self.assertEqual(facebook['state'], 'needs_login')

    def test_manual_receipt_can_resolve_ambiguous_post_but_not_running_job(self):
        batch = self.batch()
        self.connect('facebook')
        task = self.store.claim_next('worker', now=1000)
        with self.assertRaises(Conflict):
            self.store.resolve(task['id'], 'https://www.facebook.com/reel/12345')
        self.store.mark_submitting(task['id'], 'worker')
        self.store.recover_interrupted()
        self.store.resolve(task['id'], 'https://www.facebook.com/reel/12345')
        facebook = next(t for t in self.store.get_batch(batch['id'])['tasks'] if t['id'] == task['id'])
        self.assertEqual(facebook['state'], 'published')
        with self.assertRaises(Conflict):
            self.store.retry(task['id'], confirmed_not_posted=True)


if __name__ == '__main__':
    unittest.main()
