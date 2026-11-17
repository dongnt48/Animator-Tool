"""Shared browser/profile selection for manual login and scheduled publication."""
import os
import shutil
from pathlib import Path

from .store import PLATFORMS


def profile_path(root, platform):
    if platform not in PLATFORMS:
        raise ValueError('Nền tảng không hợp lệ.')
    # Never reuse Chromium data with Chrome or touch the user's everyday profile.
    name = 'tiktok-chrome' if platform == 'tiktok' else platform
    return Path(root)/'profiles'/name


def chrome_executable():
    """Find an installed Google Chrome executable without falling back to Chromium."""
    if os.name == 'nt':
        for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            base = os.environ.get(variable)
            if base:
                candidate = Path(base) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
                if candidate.is_file():
                    return str(candidate)
        return shutil.which('chrome.exe') or shutil.which('chrome')
    if os.name == 'darwin':
        candidates = (
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path.home() / 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return shutil.which('google-chrome') or shutil.which('chrome')
    return shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chrome')


def playwright_chromium_executable():
    """Return the same bundled Chromium binary used by Playwright login and uploads."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            executable = playwright.chromium.executable_path
        return executable if Path(executable).is_file() else None
    except Exception:
        return None


def browser_executable(platform):
    if platform not in PLATFORMS:
        raise ValueError('Nền tảng không hợp lệ.')
    if platform == 'tiktok':
        return chrome_executable()
    return playwright_chromium_executable()


def launch_profile(playwright, root, platform, *, headless=False, slow_mo=0):
    profile = profile_path(root, platform)
    profile.mkdir(parents=True, exist_ok=True)
    options = {'headless': headless, 'locale': 'en-US', 'viewport': {'width':1360, 'height':900}}
    if slow_mo:
        options['slow_mo'] = slow_mo
    if platform == 'tiktok':
        options['channel'] = 'chrome'
    if platform in ('tiktok', 'facebook'):
        # Match the standalone browser's OS key store so its saved login cookies
        # remain readable when this profile is reopened through Playwright.
        options['ignore_default_args'] = ['--password-store=basic', '--use-mock-keychain']
    try:
        return playwright.chromium.launch_persistent_context(str(profile), **options)
    except Exception as error:
        if platform == 'tiktok' and any(message in str(error) for message in (
                "Executable doesn't exist", "distribution 'chrome' is not found")):
            raise RuntimeError('Chưa tìm thấy Google Chrome chính thức. Cài Chrome rồi kết nối TikTok lại.') from error
        raise
