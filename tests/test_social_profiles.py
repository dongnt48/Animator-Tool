import tempfile
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import Mock

from services.social.profiles import (chrome_executable, launch_profile,
                                     playwright_chromium_executable, profile_path)


class SocialProfileTests(unittest.TestCase):
    def test_publishing_pace_spaces_real_browser_clicks(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
            context = launch_profile(playwright, directory, 'facebook', headless=True,
                                     slow_mo=5000)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_content('''<button onclick="(window.clicks ||= []).push(performance.now())">Next</button>''')
                button = page.get_by_role('button', name='Next')
                button.click()
                button.click()
                times = page.evaluate('window.clicks')
                self.assertGreaterEqual(times[1] - times[0], 4900)
            finally:
                context.close()

    @unittest.skipUnless(sys.platform.startswith('linux') and chrome_executable(),
                         'Requires installed Google Chrome on Linux')
    def test_tiktok_reuses_cookie_saved_by_manually_launched_chrome(self):
        self.assert_manual_cookie_reused('tiktok', chrome_executable())

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Requires Linux cookie store')
    def test_facebook_reuses_cookie_saved_by_manually_launched_chromium(self):
        executable = playwright_chromium_executable()
        if not executable:
            self.skipTest('Requires installed Playwright Chromium')
        self.assert_manual_cookie_reused('facebook', executable)

    def assert_manual_cookie_reused(self, platform, executable):
        from playwright.sync_api import sync_playwright

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Set-Cookie', 'studio_probe=present; Max-Age=3600; Path=/; HttpOnly')
                self.end_headers()
                self.wfile.write(b'Local cookie persistence test')

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                profile = profile_path(directory, platform)
                url = f'http://127.0.0.1:{server.server_port}'
                cmd = [executable, '--headless=new', '--no-first-run',
                       f'--user-data-dir={profile}', '--dump-dom', url]
                if sys.platform.startswith('linux'):
                    cmd.insert(1, '--no-sandbox')
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                with sync_playwright() as playwright:
                    context = launch_profile(playwright, directory, platform, headless=True)
                    try:
                        cookies = {cookie['name']: cookie['value'] for cookie in context.cookies(url)}
                        self.assertEqual(cookies.get('studio_probe'), 'present')
                    finally:
                        context.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_tiktok_uses_official_chrome_and_a_separate_persistent_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/'profiles/tiktok'; old.mkdir(parents=True)
            (old/'keep.txt').write_text('existing session')
            playwright = Mock()
            result = launch_profile(playwright, root, 'tiktok')
            call = playwright.chromium.launch_persistent_context.call_args
            self.assertEqual(call.args, (str(root/'profiles/tiktok-chrome'),))
            self.assertEqual(call.kwargs['channel'], 'chrome')
            self.assertFalse(call.kwargs['headless'])
            self.assertIs(result, playwright.chromium.launch_persistent_context.return_value)
            self.assertTrue((old/'keep.txt').is_file())
            self.assertEqual(profile_path(root, 'tiktok'), root/'profiles/tiktok-chrome')

    def test_other_platforms_keep_their_existing_browser_and_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            for platform in ('facebook','instagram','threads','youtube'):
                with self.subTest(platform=platform):
                    playwright = Mock()
                    launch_profile(playwright, Path(directory), platform)
                    call = playwright.chromium.launch_persistent_context.call_args
                    self.assertEqual(call.args, (str(Path(directory)/'profiles'/platform),))
                    self.assertNotIn('channel', call.kwargs)

    def test_unknown_platform_is_rejected(self):
        with self.assertRaises(ValueError):
            profile_path(Path('.'), '../unrelated')

    def test_missing_chrome_reports_actionable_error_without_falling_back(self):
        with tempfile.TemporaryDirectory() as directory:
            playwright = Mock()
            playwright.chromium.launch_persistent_context.side_effect = RuntimeError("Chromium distribution 'chrome' is not found")
            with self.assertRaisesRegex(RuntimeError, 'Google Chrome chính thức'):
                launch_profile(playwright, directory, 'tiktok')
            self.assertEqual(playwright.chromium.launch_persistent_context.call_count, 1)
