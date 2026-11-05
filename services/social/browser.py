"""Headed Playwright adapters. Platform UI changes must fail visibly, not guess."""
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

LOG = logging.getLogger(__name__)
HOME = {
    'facebook': 'https://www.facebook.com/',
    'instagram': 'https://www.instagram.com/',
    'threads': 'https://www.threads.com/',
    'tiktok': 'https://www.tiktok.com/tiktokstudio/upload',
    'youtube': 'https://studio.youtube.com/',
}
UPLOAD = {**HOME, 'facebook': 'https://www.facebook.com/reels/create/'}


class LoginRequired(RuntimeError):
    pass


class BrowserStepError(RuntimeError):
    pass


@dataclass
class Receipt:
    url: str
    message: str


def valid_permalink(platform, url):
    try:
        part = urlsplit(url)
        if part.scheme != 'https' or part.username or part.password or part.port not in (None, 443):
            return False
        host, path = part.hostname, part.path
        if platform == 'facebook' and host in ('facebook.com', 'www.facebook.com', 'm.facebook.com'):
            return bool(re.fullmatch(r'/reels?/\d+/?', path))
        if platform == 'instagram' and host in ('instagram.com', 'www.instagram.com'):
            return bool(re.fullmatch(r'/(?:reel|p)/[\w-]+/?', path))
        if platform == 'threads' and host in ('threads.com', 'www.threads.com', 'threads.net', 'www.threads.net'):
            return bool(re.fullmatch(r'/@[\w.]+/post/[\w-]+/?', path))
        if platform == 'tiktok' and host in ('tiktok.com', 'www.tiktok.com'):
            return bool(re.fullmatch(r'/@[\w.]+/video/\d+/?', path))
        if platform == 'youtube':
            if host == 'youtu.be':
                return bool(re.fullmatch(r'/[\w-]{11}/?', path))
            if host in ('youtube.com', 'www.youtube.com'):
                return (path == '/watch' and bool(re.fullmatch(r'[\w-]{11}', parse_qs(part.query).get('v', [''])[0]))) or bool(re.fullmatch(r'/shorts/[\w-]{11}/?', path))
    except (ValueError, TypeError):
        pass
    return False


def session_identity(platform, cookies):
    domains = {
        'facebook': ('facebook.com',), 'instagram': ('instagram.com',),
        'threads': ('threads.com', 'threads.net'), 'tiktok': ('tiktok.com',),
        'youtube': ('youtube.com', 'google.com'),
    }
    filtered = {}
    for cookie in cookies:
        domain = cookie.get('domain', '').lstrip('.')
        if any(domain == allowed or domain.endswith('.' + allowed) for allowed in domains[platform]):
            if cookie.get('value'):
                filtered[cookie['name']] = cookie['value']
    if platform == 'facebook' and filtered.get('xs'):
        return filtered.get('c_user')
    if platform == 'instagram' and filtered.get('sessionid'):
        return filtered.get('ds_user_id') or 'session-present'
    if platform == 'tiktok' and (filtered.get('sessionid') or filtered.get('sessionid_ss')):
        return filtered.get('uid_tt') or 'session-present'
    if platform == 'threads' and filtered.get('sessionid'):
        return filtered.get('ds_user_id') or 'session-present'
    if platform == 'youtube' and any(filtered.get(k) for k in ('SAPISID', '__Secure-3PAPISID', '__Secure-1PAPISID')):
        return 'session-present'
    return None


def account_identity(platform, cookies, page):
    identity = session_identity(platform, cookies)
    if not identity:
        return None
    if platform == 'youtube':
        url = urlsplit(page.url)
        channel = re.match(r'^/channel/(UC[\w-]{22})(?:/|$)', url.path)
        return channel.group(1) if url.hostname == 'studio.youtube.com' and channel else None
    if identity != 'session-present':
        return identity
    # Without a stable account cookie, require a link explicitly labelled as OUR profile.
    links = page.get_by_role('link', name=re.compile(r'^(Profile|Your profile|Trang cá nhân|Hồ sơ)$', re.I))
    for link in links.all():
        href = link.get_attribute('href') or ''
        url = urlsplit(urljoin(HOME[platform], href))
        expected_hosts = {'instagram': ('instagram.com', 'www.instagram.com'),
                          'threads': ('threads.com', 'www.threads.com', 'threads.net', 'www.threads.net'),
                          'tiktok': ('tiktok.com', 'www.tiktok.com')}
        pattern = r'^/([\w.]+)/?$' if platform == 'instagram' else r'^/(@[\w.]+)/?$'
        match = re.match(pattern, url.path)
        if url.hostname in expected_hosts.get(platform, ()) and match:
            return 'profile:' + match.group(1)
    return None


class UploadFlow:
    """One upload page. Selectors support English/Vietnamese; no stealth or verification bypass."""
    def __init__(self, page, timeout=120):
        self.page = page
        self.timeout = timeout

    def wait(self, lookup, description, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            item = lookup()
            if item is not None:
                return item
            self.page.wait_for_timeout(250)
        raise BrowserStepError(f'Không tìm thấy {description}. Giao diện có thể đã thay đổi hoặc yêu cầu xác minh.')

    def visible_button(self, pattern):
        name = re.compile(pattern, re.I)
        for role in ('button', 'link'):
            for item in self.page.get_by_role(role, name=name).all():
                if item.is_visible() and item.is_enabled():
                    return item
        return None

    def button(self, pattern, timeout=None):
        return self.wait(lambda: self.visible_button(pattern), f'nút {pattern}', timeout)

    def click(self, pattern, timeout=None):
        self.button(pattern, timeout).click()

    def field(self, selectors):
        def lookup():
            for selector in selectors:
                for item in self.page.locator(selector).all():
                    if item.is_visible():
                        return item
            return None
        return self.wait(lookup, 'ô caption')

    def upload_file(self, media_path):
        self.page.locator('input[type="file"]').first.wait_for(state='attached', timeout=int(self.timeout * 1000))
        self.page.locator('input[type="file"]').first.set_input_files(str(media_path))

    def prepare_facebook(self, media_path, caption):
        self.upload_file(media_path)
        final_pattern = r'^(Share|Share now|Publish|Post|Chia sẻ|Chia sẻ ngay|Đăng)(?: (?:reel|thước phim))?$'
        next_pattern = r'^(Next|Tiếp|Tiếp theo)$'
        deadline = time.monotonic() + self.timeout
        caption_filled = False
        advances = 0
        last_next = None
        last_step_text = None
        while time.monotonic() < deadline:
            for field in self.page.locator('[role="textbox"][contenteditable="true"], textarea').all():
                if field.is_visible() and field.is_editable():
                    if not caption_filled:
                        field.fill(caption)
                        caption_filled = True
                    break
            final = self.visible_button(final_pattern)
            next_button = self.visible_button(next_pattern)
            if final is not None and caption_filled:
                return final_pattern  # Submit, checkpoint and receipt handling remain separate.
            if final is not None and next_button is None and not caption_filled:
                raise BrowserStepError('Đã tới màn hình Đăng nhưng chưa tìm thấy ô caption. Dừng để tránh đăng thiếu nội dung.')
            if next_button is not None:
                handle = next_button.element_handle()
                step_text = self.page.locator('body').inner_text()
                same_step = (last_next is not None and
                             last_next.evaluate('(old, current) => old.isConnected && old === current', handle) and
                             step_text == last_step_text)
                if not same_step:
                    if advances >= 4:
                        raise BrowserStepError('Luồng tạo Facebook Reels có bước chưa nhận diện. Dừng trước khi xuất bản.')
                    last_next, last_step_text = handle, step_text
                    next_button.click()
                    advances += 1
            self.page.wait_for_timeout(100)
        raise BrowserStepError('Chưa nhận diện được bước tiếp theo hoặc nút Đăng Facebook Reels. Hãy kiểm tra ảnh chụp lỗi.')

    def prepare(self, platform, media_path, caption, made_for_kids):
        if platform == 'instagram':
            self.click(r'^(Create|New post|Tạo|Bài viết mới)$')
            self.upload_file(media_path)
            self.click(r'^(Next|Tiếp)$')
            self.click(r'^(Next|Tiếp)$')
            self.field(['textarea[aria-label*="caption" i]', 'textarea[aria-label*="chú thích" i]',
                        '[role="dialog"] [contenteditable="true"]']).fill(caption)
            return r'^(Share|Chia sẻ)$'
        if platform == 'facebook':
            return self.prepare_facebook(media_path, caption)
        if platform == 'threads':
            self.click(r'^(Create|New thread|Tạo|Bài viết mới)$')
            self.field(['[role="dialog"] [role="textbox"]', '[role="textbox"][contenteditable="true"]']).fill(caption)
            self.upload_file(media_path)
            return r'^(Post|Đăng)$'
        if platform == 'tiktok':
            self.upload_file(media_path)
            self.field(['[data-e2e="caption_container"] [contenteditable="true"]',
                        '[contenteditable="true"][role="textbox"]', '[contenteditable="true"]']).fill(caption)
            return r'^(Post|Đăng)$'
        if platform == 'youtube':
            if type(made_for_kids) is not bool:
                raise ValueError('Cần chọn đối tượng khán giả YouTube.')
            if len(caption) > 5000:
                raise ValueError('Caption vượt giới hạn mô tả YouTube; hãy sửa nội dung nguồn trước khi lên lịch.')
            self.click(r'^(Create|Tạo)$')
            self.click(r'^(Upload videos|Tải video lên)$')
            self.upload_file(media_path)
            title = caption.splitlines()[0].strip()[:100]
            self.field(['#title-textarea #textbox', '[aria-label*="Add a title" i]']).fill(title)
            self.field(['#description-textarea #textbox', '[aria-label*="Tell viewers" i]']).fill(caption)
            audience = 'VIDEO_MADE_FOR_KIDS_MFK' if made_for_kids else 'VIDEO_MADE_FOR_KIDS_NOT_MFK'
            self.page.locator(f'[name="{audience}"]').click()
            for _ in range(3):
                self.click(r'^(Next|Tiếp)$')
            self.page.locator('[name="PUBLIC"]').click()
            return r'^(Publish|Xuất bản|Đăng)$'
        raise ValueError('Nền tảng không được hỗ trợ.')

    def permalinks(self, platform, scope):
        urls = set()
        for item in scope.locator('a[href]').all():
            href = item.get_attribute('href')
            if href:
                urls.add(urljoin(self.page.url, href))
        # YouTube's completion dialog can render the share URL as readonly input.
        for item in scope.locator('input[readonly]').all():
            value = item.input_value()
            if value:
                urls.add(value)
        return {url for url in urls if valid_permalink(platform, url)}

    def successful_receipts(self, platform, success):
        selectors = {
            'facebook': '[role="dialog"], [role="status"], [role="alert"]',
            'instagram': '[role="dialog"]',
            'threads': '[role="status"], [role="alert"], [role="dialog"]',
            'tiktok': '[data-e2e="upload-success"], [role="dialog"], [role="status"]',
            'youtube': 'ytcp-video-share-dialog',
        }
        results = set()
        for scope in self.page.locator(selectors[platform]).all():
            if not scope.is_visible():
                continue
            if platform == 'youtube' or scope.get_attribute('role') in ('status', 'alert') or scope.get_attribute('data-e2e') == 'upload-success':
                confirmed = bool(success.search(scope.inner_text()))
            else:
                confirmed = any(item.is_visible() for item in scope.get_by_role('heading', name=success).all())
            if confirmed:
                results.update(self.permalinks(platform, scope))
                if valid_permalink(platform, self.page.url):
                    results.add(self.page.url)
        return results

    def submit(self, platform, button_pattern, before_publish):
        success = re.compile(r'(Your (?:post|reel|video) (?:has been |was )?(?:shared|published|posted)|'
                             r'(?:Post|Reel|Video) (?:published|shared|posted)|'
                             r'Đã (?:chia sẻ|đăng|xuất bản)|(?:đăng|chia sẻ|xuất bản) thành công)', re.I)
        # Only the completion UI can identify THIS upload. Feed/recommendation links are not receipts.
        old_receipts = self.successful_receipts(platform, success)
        final_button = self.button(button_pattern)
        before_publish()  # Durable DB checkpoint BEFORE any click that could publish.
        final_button.click()
        deadline = time.monotonic() + self.timeout
        confirmation_clicked = False
        while time.monotonic() < deadline:
            # Some TikTok accounts show a final confirmation after the Post click.
            if platform == 'tiktok' and not confirmation_clicked:
                for button in self.page.get_by_role('button', name=re.compile(r'^(Post now|Đăng ngay)$', re.I)).all():
                    if button.is_visible() and button.is_enabled():
                        button.click()
                        confirmation_clicked = True
                        break
            links = self.successful_receipts(platform, success) - old_receipts
            if len(links) == 1:
                return Receipt(next(iter(links)), 'Đã thấy xác nhận xuất bản và link bài từ nền tảng.')
            self.page.wait_for_timeout(500)
        raise BrowserStepError('Đã bấm xuất bản nhưng chưa xác nhận được link bài. Kiểm tra tài khoản trước khi thử lại.')


class BrowserPublisher:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    def __call__(self, task, before_publish):
        from playwright.sync_api import sync_playwright
        platform = task['platform']
        profile = self.data_dir / 'profiles' / platform
        if not profile.is_dir():
            raise LoginRequired('Chưa có hồ sơ trình duyệt. Hãy kết nối tài khoản.')
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(str(profile), headless=False, locale='en-US',
                                                                      viewport={'width': 1360, 'height': 900})
            try:
                context.set_default_timeout(20000)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(UPLOAD[platform], wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(1500)
                if platform == 'youtube':
                    page.wait_for_url(re.compile(r'https://studio\.youtube\.com/channel/'), timeout=20000)
                identity = account_identity(platform, context.cookies(), page)
                if not identity or identity != task['identity']:
                    raise LoginRequired('Phiên hết hạn hoặc tài khoản đã đổi. Kết nối và kiểm tra lại tài khoản.')
                if re.search(r'/(login|accounts/login|checkpoint|challenge|signin)', page.url, re.I):
                    raise LoginRequired('Nền tảng đang yêu cầu đăng nhập hoặc xác minh thủ công.')
                flow = UploadFlow(page)
                publish_button = flow.prepare(platform, task['media_path'], task['caption'], bool(task['made_for_kids']))
                return flow.submit(platform, publish_button, before_publish)
            except Exception:
                diagnostics = self.data_dir / 'diagnostics'
                diagnostics.mkdir(parents=True, exist_ok=True)
                try:
                    page.screenshot(path=str(diagnostics / f"{task['id']}.png"), full_page=True)
                except Exception:
                    pass
                LOG.exception('Browser task %s failed on %s', task['id'], platform)
                raise
            finally:
                context.close()
