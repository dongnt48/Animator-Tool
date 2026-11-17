import importlib.util
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from services.social.store import Store, Conflict


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Requires Playwright')
class ChannelBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)

    def test_waits_for_manual_verification_then_collects_only_requested_channel(self):
        from services.channel_browser import collect_channel_urls
        self.page.set_content('''<div id="captcha">Drag the slider to fit the puzzle</div>
            <a href="https://www.tiktok.com/@other/video/99">Other</a>
            <a href="https://www.tiktok.com.evil.test/@example/video/98">Wrong host</a>
            <a href="https://www.tiktok.com/@example/video/12">Hidden behind verification</a>''')
        messages = []
        def progress(message):
            messages.append(message)
            if 'xác minh' in message:
                # Simulate the user's completed verification; the scanner never solves it.
                self.page.evaluate("document.getElementById('captcha').remove();document.body.insertAdjacentHTML('beforeend','<a href=\"https://www.tiktok.com/@example/video/12?share=1\">Duplicate</a><a href=\"https://www.tiktok.com/@example/video/13\">Next</a>')")
        urls = collect_channel_urls(self.page, 'example', 2, timeout=2, poll_ms=20, progress=progress)
        self.assertEqual(urls, ['https://www.tiktok.com/@example/video/12', 'https://www.tiktok.com/@example/video/13'])
        self.assertTrue(any('xác minh' in message for message in messages))

    def test_uncompleted_captcha_times_out_without_clicking_or_returning_links(self):
        from services.channel_browser import collect_channel_urls, ChannelScanError
        self.page.set_content('''<div id="captcha" onclick="window.captchaClicked=true">Drag the slider to fit the puzzle</div>
            <a href="https://www.tiktok.com/@example/video/12">Video</a>''')
        with self.assertRaises(ChannelScanError):
            collect_channel_urls(self.page, 'example', 1, timeout=.15, poll_ms=20)
        self.assertIsNone(self.page.evaluate('window.captchaClicked'))

    def test_image_only_verification_inside_iframe_blocks_collection(self):
        from services.channel_browser import collect_channel_urls, ChannelScanError
        self.page.set_content('''<iframe srcdoc="<div id='captcha' style='height:100px'>Select matching shapes</div>"></iframe>
            <a href="https://www.tiktok.com/@example/video/12">Video</a>''')
        with self.assertRaises(ChannelScanError):
            collect_channel_urls(self.page, 'example', 1, timeout=.15, poll_ms=20)

    def test_hidden_verification_iframe_does_not_block_collection(self):
        from services.channel_browser import collect_channel_urls
        self.page.set_content('''<iframe hidden srcdoc="<div id='captcha' style='height:100px'>Select matching shapes</div>"></iframe>
            <a href="https://www.tiktok.com/@example/video/12">Video</a>''')
        self.assertEqual(len(collect_channel_urls(self.page, 'example', 1, timeout=1)), 1)

    def test_closed_window_is_reported(self):
        from services.channel_browser import collect_channel_urls, ChannelScanError
        self.page.close()
        with self.assertRaisesRegex(ChannelScanError, 'đóng'):
            collect_channel_urls(self.page, 'example', 1, timeout=.1)

    def test_scrolling_collects_lazy_loaded_videos_and_stops_at_limit(self):
        from services.channel_browser import collect_channel_urls
        self.page.set_content('''<div style="height:2000px"></div><a href="https://www.tiktok.com/@example/video/12">First</a>
            <script>window.addEventListener('scroll',()=>{if(!window.added){window.added=true;document.body.insertAdjacentHTML('beforeend','<a href="https://www.tiktok.com/@example/video/13">Second</a>')}})</script>''')
        self.assertEqual(len(collect_channel_urls(self.page, 'example', 2, timeout=2, poll_ms=30)), 2)

    def test_all_mode_stops_after_list_settles(self):
        from services.channel_browser import collect_channel_urls
        self.page.set_content('<a href="https://www.tiktok.com/@example/video/12">Only video</a>')
        self.assertEqual(collect_channel_urls(self.page, 'example', 0, timeout=2, poll_ms=20, settle_rounds=2),
                         ['https://www.tiktok.com/@example/video/12'])

    def test_busy_profile_is_not_opened_or_released_by_another_scan(self):
        from services.channel_browser import scan_channel_urls
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root/'social.sqlite3')
            store.begin_login('tiktok')
            before = store.accounts()
            with self.assertRaises(Conflict):
                scan_channel_urls('example', root=root)
            self.assertEqual(store.accounts(), before)

    def test_full_scanner_reads_local_channel_and_releases_profile_on_success(self):
        from services.channel_browser import scan_channel_urls
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root/'social.sqlite3')
            before = store.accounts()
            def launch(playwright, *args, **kwargs):
                context = playwright.chromium.launch_persistent_context(str(root/'test-browser'), headless=True)
                context.pages[0].route('https://www.tiktok.com/@example', lambda route: route.fulfill(
                    content_type='text/html', body='<a href="https://www.tiktok.com/@example/video/12">Video</a>'))
                return context
            with patch('services.channel_browser.launch_profile', side_effect=launch), ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(scan_channel_urls, 'example', 1, root=root, timeout=2).result()
            self.assertEqual(result, ['https://www.tiktok.com/@example/video/12'])
            self.assertEqual(store.accounts(), before)

    def test_private_channel_error_is_not_mislabeled_as_closed_window(self):
        from services.channel_browser import scan_channel_urls, ChannelScanError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root/'social.sqlite3')
            def launch(playwright, *args, **kwargs):
                context = playwright.chromium.launch_persistent_context(str(root/'test-browser'), headless=True)
                context.pages[0].route('https://www.tiktok.com/@example', lambda route: route.fulfill(
                    content_type='text/html', body='<h2>This account is private</h2>'))
                return context
            with patch('services.channel_browser.launch_profile', side_effect=launch), ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(ChannelScanError, 'riêng tư'):
                    pool.submit(scan_channel_urls, 'example', root=root, timeout=2).result()
            self.assertEqual(next(a for a in store.accounts() if a['platform'] == 'tiktok')['lease_until'], 0)

    def test_profile_is_reserved_and_released_without_changing_saved_account(self):
        from services.channel_browser import scan_channel_urls
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root/'social.sqlite3')
            owner = store.begin_login('tiktok')
            store.complete_login('tiktok', owner, 'saved-account')
            before = next(a for a in store.accounts() if a['platform'] == 'tiktok')
            def fail_launch(*args, **kwargs):
                with self.assertRaises(Conflict):
                    store.begin_login('tiktok')
                raise RuntimeError('Browser failed to launch')
            with patch('services.channel_browser.launch_profile', side_effect=fail_launch):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with self.assertRaisesRegex(RuntimeError, 'failed to launch'):
                        pool.submit(scan_channel_urls, 'example', root=root).result()
            after = next(a for a in store.accounts() if a['platform'] == 'tiktok')
            self.assertEqual(after, before)
