"""Verify own-account post evidence without publishing any content."""
import tempfile
import time
import unittest
from pathlib import Path
from services.social.store import Store


class ReceiptMatchingTests(unittest.TestCase):
    def test_matches_full_caption_time_and_canonical_link_only(self):
        from services.social.verification import find_tiktok_receipt
        payload = {'status_code': 0, 'item_list': [{'item_id':'12345', 'desc':'Caption\n#tag', 'post_time':'1000', 'status':102}]}
        links = ['https://www.tiktok.com/@owner/video/12345', 'https://www.tiktok.com/@other/video/98765']
        self.assertEqual(find_tiktok_receipt(payload, links, 'Caption #tag', 995, 1010), links[0])
        for changed in ({'desc':'Caption'}, {'post_time':'900'}, {'status':0}, {'item_id':'oops'}):
            bad = {'status_code':0, 'item_list':[{**payload['item_list'][0], **changed}]}
            self.assertIsNone(find_tiktok_receipt(bad, links, 'Caption #tag', 995, 1010))
        self.assertIsNone(find_tiktok_receipt(payload, ['https://evil.test/@owner/video/12345'], 'Caption #tag', 995, 1010))
        self.assertIsNone(find_tiktok_receipt({'status_code':1, **{'item_list':payload['item_list']}}, links, 'Caption #tag', 995, 1010))
        duplicate = {'status_code':0, 'item_list':payload['item_list'] + [{**payload['item_list'][0], 'item_id':'98765'}]}
        self.assertIsNone(find_tiktok_receipt(duplicate, links, 'Caption #tag', 995, 1010))

    def test_reconciliation_updates_only_matching_task_and_releases_profile(self):
        from services.social.verification import reconcile_pending
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = Store(root/'social.sqlite3'); media=root/'test.mp4';media.write_bytes(b'video')
            login = store.begin_login('tiktok');store.complete_login('tiktok', login, 'owner')
            now=time.time()
            store.create_batch('video', str(media), 'Caption', now, False, 'request', platforms=['tiktok'])
            task=store.claim_next('worker', now=now);store.mark_submitting(task['id'], 'worker')
            store.finish(task['id'], 'worker', 'needs_review', 'Receipt missing')
            def collect(root, identity, tasks):
                self.assertEqual(identity, 'owner')
                return {tasks[0]['id']:'https://www.tiktok.com/@owner/video/12345'}
            self.assertEqual(reconcile_pending(store, root, collector=collect), 1)
            self.assertEqual(store.task_state(task['id']), 'published')
            self.assertIn('video', store.published_video_ids())
            account=next(a for a in store.accounts() if a['platform']=='tiktok')
            self.assertIsNone(account['lease_owner'])
            self.assertEqual(account['identity'], 'owner')
            self.assertEqual(reconcile_pending(store, root, collector=lambda *args:self.fail('No pending task')), 0)

    def test_already_assigned_post_cannot_confirm_another_video(self):
        from services.social.verification import reconcile_pending
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=Store(root/'social.sqlite3');media=root/'test.mp4';media.write_bytes(b'video')
            login=store.begin_login('tiktok');store.complete_login('tiktok',login,'owner');now=time.time()
            for video, state in [('first','published'), ('second','needs_review')]:
                store.create_batch(video,str(media),'Identical caption',now,False,video,platforms=['tiktok'])
                task=store.claim_next('worker',now=now);store.mark_submitting(task['id'],'worker')
                store.finish(task['id'],'worker',state,url='https://www.tiktok.com/@owner/video/12345?share=1' if state=='published' else '')
            result=reconcile_pending(store,root,collector=lambda root,identity,tasks:{task['id']:'https://www.tiktok.com/@owner/video/12345'})
            self.assertEqual(result,0)
            self.assertEqual(store.task_state(task['id']),'needs_review')

    def test_missed_schedule_that_never_uploaded_is_not_a_receipt_candidate(self):
        from services.social.verification import reconcile_pending
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=Store(root/'social.sqlite3');media=root/'test.mp4';media.write_bytes(b'video')
            login=store.begin_login('tiktok');store.complete_login('tiktok',login,'owner');now=time.time()
            batch=store.create_batch('video',str(media),'Caption',now-1200,False,'missed',platforms=['tiktok'])
            self.assertIsNone(store.claim_next('worker',now=now))
            def collect(*args):
                self.fail('Never-uploaded schedule must not be checked against existing posts')
            with self.assertNoLogs('services.social.verification',level='WARNING'):
                self.assertEqual(reconcile_pending(store,root,collector=collect),0)

    def test_busy_profile_and_collector_failure_do_not_confirm_or_lose_session(self):
        from services.social.verification import reconcile_pending
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=Store(root/'social.sqlite3');media=root/'test.mp4';media.write_bytes(b'video')
            login=store.begin_login('tiktok');store.complete_login('tiktok', login, 'owner');now=time.time()
            store.create_batch('video', str(media), 'Caption', now, False, 'request', platforms=['tiktok'])
            task=store.claim_next('worker',now=now);store.mark_submitting(task['id'],'worker');store.finish(task['id'],'worker','needs_review')
            with store.transaction() as db:db.execute("UPDATE accounts SET lease_owner='busy',lease_until=? WHERE platform='tiktok'",(now+600,))
            self.assertEqual(reconcile_pending(store,root,collector=lambda *args:self.fail('Profile busy')),0)
            with store.transaction() as db:db.execute("UPDATE accounts SET lease_owner=NULL,lease_until=0 WHERE platform='tiktok'")
            def fail(*args):raise RuntimeError('Browser unavailable')
            self.assertEqual(reconcile_pending(store,root,collector=fail),0)
            self.assertEqual(store.task_state(task['id']),'needs_review')
            self.assertIsNone(next(a for a in store.accounts() if a['platform']=='tiktok')['lease_owner'])

if __name__=='__main__':unittest.main()
