"""Shared browser/profile selection for manual login and scheduled publication."""
from pathlib import Path

from .store import PLATFORMS


def profile_path(root, platform):
    if platform not in PLATFORMS:
        raise ValueError('Nền tảng không hợp lệ.')
    # Never reuse Chromium data with Chrome or touch the user's everyday profile.
    name = 'tiktok-chrome' if platform == 'tiktok' else platform
    return Path(root)/'profiles'/name


def launch_profile(playwright, root, platform, *, headless=False):
    profile = profile_path(root, platform)
    profile.mkdir(parents=True, exist_ok=True)
    options = {'headless': headless, 'locale': 'en-US', 'viewport': {'width':1360, 'height':900}}
    if platform == 'tiktok':
        options['channel'] = 'chrome'
    try:
        return playwright.chromium.launch_persistent_context(str(profile), **options)
    except Exception as error:
        if platform == 'tiktok' and any(message in str(error) for message in (
                "Executable doesn't exist", "distribution 'chrome' is not found")):
            raise RuntimeError('Chưa tìm thấy Google Chrome chính thức. Cài Chrome rồi kết nối TikTok lại.') from error
        raise
