import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.social.profiles import launch_profile, profile_path


class SocialProfileTests(unittest.TestCase):
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
