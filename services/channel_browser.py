"""Discover channel links after the user completes verification in visible Chrome."""
import re
import time
import uuid
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .social.profiles import launch_profile
from .social.store import Store, Conflict


class ChannelScanError(RuntimeError):
    pass


def _verification_visible(page):
    from playwright.sync_api import Error as PlaywrightError
    markers = '[id*="captcha" i],[class*="captcha" i],iframe[src*="captcha" i],iframe[src*="verify" i]'
    prompt = re.compile(r'drag the slider|fit the puzzle|complete (?:the )?verification|verify you are human|hoàn thành xác minh', re.I)
    for frame in page.frames:
        try:
            if frame.is_detached():
                continue
            ancestor = frame
            visible = True
            while ancestor.parent_frame is not None:
                if not ancestor.frame_element().is_visible():
                    visible = False
                    break
                ancestor = ancestor.parent_frame
            if not visible:
                continue
            for item in frame.locator(markers).all() + frame.get_by_text(prompt).all():
                if item.is_visible():
                    return True
        except PlaywrightError:
            if frame.is_detached():
                continue  # Verification can remove its iframe after the user completes it.
            raise
    return False


def collect_channel_urls(page, username, limit=5, *, timeout=600, poll_ms=1000,
                         settle_rounds=8, progress=None):
    if not re.fullmatch(r'[A-Za-z0-9_.]+', username):
        raise ValueError('Tên kênh TikTok không hợp lệ.')
    found = {}
    quiet = 0
    last_message = None
    deadline = time.monotonic() + timeout

    def notify(message):
        nonlocal last_message
        if progress and message != last_message:
            progress(message)
        last_message = message

    while time.monotonic() < deadline:
        if page.is_closed():
            raise ChannelScanError('Đã đóng Chrome; lượt quét kênh đã dừng.')
        if _verification_visible(page):
            quiet = 0
            notify('TikTok yêu cầu xác minh. Hoàn thành CAPTCHA thủ công trong Chrome đang mở; app sẽ tự tiếp tục.')
            page.wait_for_timeout(poll_ms)
            continue
        if re.search(r'/(login|signin)(?:/|$)', urlsplit(page.url).path, re.I):
            notify('Đăng nhập TikTok trong Chrome nếu được yêu cầu, rồi mở lại trang kênh; app đang chờ.')
            quiet = 0
            page.wait_for_timeout(poll_ms)
            continue
        before = len(found)
        for href in page.locator('a[href*="/video/"]').evaluate_all('els => els.map(e => e.href)'):
            parsed = urlsplit(urljoin('https://www.tiktok.com/', href))
            match = re.fullmatch(r'/@' + re.escape(username) + r'/video/(\d+)/?', parsed.path, re.I)
            if parsed.scheme == 'https' and parsed.hostname in ('www.tiktok.com', 'tiktok.com', 'm.tiktok.com') and match:
                found.setdefault(match.group(1), f'https://www.tiktok.com/@{username}/video/{match.group(1)}')
        notify(f'Đã tìm thấy {len(found)} link video trên kênh; đang quét trong Chrome.')
        if limit and limit > 0 and len(found) >= limit:
            return list(found.values())[:limit]
        quiet = quiet + 1 if len(found) == before else 0
        if found and quiet >= settle_rounds:
            return list(found.values())
        if not found:
            text = page.locator('body').inner_text()
            if re.search(r'this account is private|no videos yet|chưa có video|tài khoản này.*riêng tư', text, re.I):
                raise ChannelScanError('Kênh riêng tư hoặc chưa có video có thể xem bằng phiên TikTok hiện tại.')
        page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
        page.wait_for_timeout(poll_ms)
    raise ChannelScanError('Hết thời gian chờ quét kênh trong Chrome. Hoàn thành xác minh rồi thử lại hoặc dán link video riêng.')


def scan_channel_urls(username, limit=5, *, progress=None, timeout=600, root=None):
    from playwright.sync_api import sync_playwright
    from .social.worker import data_dir
    if not re.fullmatch(r'[A-Za-z0-9_.]+', username):
        raise ValueError('Tên kênh TikTok không hợp lệ.')
    root = Path(root) if root is not None else data_dir()
    store = Store(root/'social.sqlite3')
    owner = 'channel-scan:' + uuid.uuid4().hex
    now = time.time()
    with store.transaction() as db:
        result = db.execute("UPDATE accounts SET lease_owner=?,lease_until=? WHERE platform='tiktok' AND lease_until<=?",
                            (owner, now + timeout + 120, now))
        if not result.rowcount:
            raise Conflict('Hồ sơ TikTok đang dùng để đăng hoặc đăng nhập. Đóng cửa sổ đó/đợi tác vụ xong rồi quét lại.')
    context = None
    page = None
    try:
        if progress:
            progress('Đang mở Chrome để quét kênh. Nếu TikTok yêu cầu CAPTCHA, hãy xác minh thủ công; chờ tối đa 10 phút.')
        with sync_playwright() as playwright:
            try:
                context = launch_profile(playwright, root, 'tiktok', headless=False)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=45000)
                return collect_channel_urls(page, username, limit, timeout=timeout, progress=progress)
            except Exception as error:
                if page is not None and page.is_closed() and not isinstance(error, ChannelScanError):
                    raise ChannelScanError('Đã đóng Chrome; lượt quét kênh đã dừng.') from error
                raise
            finally:
                if context is not None:
                    with suppress(Exception):
                        context.close()
    finally:
        with store.transaction() as db:
            db.execute("UPDATE accounts SET lease_owner=NULL,lease_until=0 WHERE platform='tiktok' AND lease_owner=?", (owner,))
