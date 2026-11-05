import tempfile
import unittest
from pathlib import Path
from services.social.store import Store
from services.social.worker import Worker
from services.social.browser import Receipt, LoginRequired, valid_permalink, session_identity, account_identity


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.media = root / 'video.mp4'
        self.media.write_bytes(b'video')
        self.store = Store(root / 'social.db')
        self.batch = self.store.create_batch('one', str(self.media), 'Caption #tag', 1000, False, 'one')
        owner = self.store.begin_login('facebook', now=900)
        self.store.complete_login('facebook', owner, '42', now=901)

    def facebook(self):
        return next(t for t in self.store.get_batch(self.batch['id'])['tasks'] if t['platform'] == 'facebook')

    def test_success_requires_publication_checkpoint_and_valid_receipt(self):
        def publisher(task, checkpoint):
            self.assertEqual(task['caption'], 'Caption #tag')
            checkpoint()
            return Receipt('https://www.facebook.com/reel/12345', 'Đã đăng')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'published')
        self.assertEqual(self.facebook()['url'], 'https://www.facebook.com/reel/12345')

    def test_exception_after_publication_is_not_automatically_retryable(self):
        def publisher(task, checkpoint):
            checkpoint()
            raise TimeoutError('Lost receipt')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'needs_review')

    def test_failure_before_publication_can_be_retried(self):
        def publisher(task, checkpoint):
            raise RuntimeError('Upload input missing')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'failed')

    def test_missing_session_marks_account_for_login(self):
        def publisher(task, checkpoint):
            raise LoginRequired('Please log in')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'needs_login')
        account = next(a for a in self.store.accounts() if a['platform'] == 'facebook')
        self.assertEqual(account['state'], 'needs_login')

    def test_changed_media_is_not_published(self):
        Path(self.batch['media_path']).write_bytes(b'different render')
        def publisher(task, checkpoint):
            self.fail('Changed video must not reach browser')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'failed')
        self.assertIn('thay đổi', self.facebook()['message'])

    def test_rerendering_source_does_not_change_scheduled_video(self):
        self.media.write_bytes(b'new unrelated render')
        def publisher(task, checkpoint):
            self.assertEqual(Path(task['media_path']).read_bytes(), b'video')
            checkpoint()
            return Receipt('https://www.facebook.com/reel/12345', 'OK')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'published')

    def test_foreign_receipt_does_not_report_success(self):
        def publisher(task, checkpoint):
            checkpoint()
            return Receipt('https://www.facebook.com.evil.test/reel/12345', 'OK')
        Worker(self.store, publisher).run_once(now=1000)
        self.assertEqual(self.facebook()['state'], 'needs_review')

    def test_profile_home_is_not_a_post_receipt(self):
        for platform, url in [('facebook', 'https://www.facebook.com/'), ('instagram', 'https://www.instagram.com/me/'),
                              ('threads', 'https://www.threads.com/@someone'), ('tiktok', 'https://www.tiktok.com/@someone'),
                              ('youtube', 'https://studio.youtube.com/channel/123')]:
            self.assertFalse(valid_permalink(platform, url))

    def test_reel_and_video_receipts_are_allowed_only_on_correct_platform(self):
        self.assertTrue(valid_permalink('instagram', 'https://www.instagram.com/reel/ABC_123/'))
        self.assertTrue(valid_permalink('threads', 'https://www.threads.com/@someone/post/ABC123'))
        self.assertTrue(valid_permalink('tiktok', 'https://www.tiktok.com/@someone/video/12345'))
        self.assertTrue(valid_permalink('youtube', 'https://youtu.be/abcdefghijk'))
        self.assertFalse(valid_permalink('youtube', 'javascript:alert(1)'))
        self.assertFalse(valid_permalink('youtube', 'https://youtu.be/abcdefghijk/extra'))

    def test_cookie_from_unrelated_domain_is_not_a_login(self):
        self.assertIsNone(session_identity('facebook', [{'name': 'c_user', 'value': '42', 'domain': '.evil.test'}]))
        self.assertEqual(session_identity('facebook', [{'name': 'c_user', 'value': '42', 'domain': '.facebook.com'},
                                                     {'name': 'xs', 'value': 'secret', 'domain': '.facebook.com'}]), '42')

    def test_youtube_channel_is_bound_separately_from_google_login(self):
        class Page:
            url = 'https://studio.youtube.com/channel/UCabcdefghijklmnopqrstuv'
        cookies = [{'name': 'SAPISID', 'value': 'secret', 'domain': '.youtube.com'}]
        self.assertEqual(account_identity('youtube', cookies, Page()), 'UCabcdefghijklmnopqrstuv')
        Page.url = 'https://studio.youtube.com/'
        self.assertIsNone(account_identity('youtube', cookies, Page()))


if __name__ == '__main__':
    unittest.main()
