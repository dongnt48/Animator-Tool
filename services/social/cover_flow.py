"""Optional cover UI. Never use the video upload input or infer success from a filename."""
import re
import time


ROOTS = ('ytcp-video-thumbnail-editor', '#thumbnail-editor', '[data-testid="cover-editor"]',
         '[data-e2e="cover_container"]', '[aria-label="Cover photo"]', '[aria-label="Ảnh bìa"]',
         '[role="dialog"][aria-label*="cover" i]', '[role="dialog"][aria-label*="thumbnail" i]',
         '[role="dialog"][aria-label*="ảnh bìa" i]')
OPEN = re.compile(r'^(Edit cover|Select cover|Change cover|Upload thumbnail|Edit thumbnail|Chỉnh sửa ảnh bìa|Chọn ảnh bìa|Đổi ảnh bìa|Tải hình thu nhỏ lên)$', re.I)


class CoverFlow:
    def __init__(self, page, cover=None):
        self.page, self.cover = page, cover or {}
        self.state = 'pending' if cover else 'automatic'
        self.message = '' if cover else 'Lịch này không có ảnh bìa riêng; nền tảng chọn ảnh tự động.'
        self.attempted = False

    def root(self):
        for selector in ROOTS:
            for item in self.page.locator(selector).all():
                if item.is_visible():
                    return item
        return None

    def previews(self, *, loaded_only=True):
        sources = set()
        for selector in ROOTS:
            for item in self.page.locator(selector+' img').all():
                if item.is_visible() and (not loaded_only or item.evaluate('(image) => image.complete && image.naturalWidth > 0')):
                    sources.add(item.get_attribute('src'))
        return sources

    def close_editor(self):
        # Only close a specifically named cover editor; never click a composer Submit button.
        for selector in ROOTS:
            if not selector.startswith('[role="dialog"]'):
                continue
            for dialog in self.page.locator(selector).all():
                if dialog.is_visible():
                    for button in dialog.get_by_role('button', name=re.compile(r'^(Save|Done|Lưu|Xong)$', re.I)).all():
                        if button.is_visible() and button.is_enabled():
                            button.click(); return

    def apply(self, platform):
        if not self.cover or self.attempted:
            return
        if platform == 'threads':
            self.state, self.message = 'automatic', 'Luồng Threads hiện dùng ảnh xem trước tự động; không tải ảnh bìa riêng.'
            self.attempted = True
            return
        scope = self.root()
        buttons = [b for b in self.page.get_by_role('button', name=OPEN).all() if b.is_visible() and b.is_enabled()]
        if scope is None and not buttons:
            return
        self.attempted = True
        before = self.previews(loaded_only=False)
        ratio = str(self.cover.get('aspect_ratio') or '9:16').split(':')
        horizontal = len(ratio) == 2 and all(p.isdigit() for p in ratio) and int(ratio[0]) > int(ratio[1])
        shape = 'landscape' if platform == 'youtube' and horizontal else 'portrait'
        path = self.cover.get(shape+'_path')
        if not path:
            self.state, self.message = 'needs_review', 'Thiếu bản ảnh bìa phù hợp.'
            return
        try:
            uploaded = False
            if buttons:
                from playwright.sync_api import TimeoutError as PlaywrightTimeout
                try:
                    with self.page.expect_file_chooser(timeout=900) as chooser:
                        buttons[0].click()
                    before = self.previews(loaded_only=False)
                    chooser.value.set_files(path)
                    uploaded = True
                except PlaywrightTimeout:
                    pass  # The button may open a cover editor rather than a native chooser.
            scope = self.root()
            if not uploaded and scope is not None:
                inputs = scope.locator('input[type="file"][accept*="image" i]')
                if inputs.count():
                    before = self.previews(loaded_only=False)
                    inputs.first.set_input_files(path)
                    uploaded = True
            if uploaded:
                self.close_editor()
                deadline = time.monotonic()+4
                while time.monotonic() < deadline:
                    if self.previews()-before:
                        self.state, self.message = 'applied', 'Đã thấy ảnh bìa mới trong giao diện xem trước trước khi đăng.'
                        return
                    self.page.wait_for_timeout(150)
                self.state, self.message = 'needs_review', 'Đã gửi ảnh nhưng chưa xác minh được ảnh bìa mới trong xem trước.'
            elif scope is not None and self.cover.get('mode') == 'frame' and self.cover.get('duration'):
                sliders = scope.locator('input[type="range"], [role="slider"]')
                if sliders.count() == 1 and sliders.first.is_visible():
                    slider = sliders.first
                    old = slider.evaluate('(e) => e.value ?? e.getAttribute("aria-valuenow")')
                    box = slider.bounding_box()
                    fraction = max(0, min(.999, float(self.cover.get('timestamp') or 0)/float(self.cover['duration'])))
                    self.page.mouse.click(box['x']+box['width']*fraction, box['y']+box['height']/2)
                    new = slider.evaluate('(e) => e.value ?? e.getAttribute("aria-valuenow")')
                    self.close_editor()
                    if old != new and new is not None:
                        self.state, self.message = 'frame', 'Đã chọn khung từ video. Chữ trên ảnh bìa riêng không được tải lên.'
                        return
                self.state, self.message = 'automatic', 'Không xác minh được bộ chọn khung; dùng ảnh xem trước của nền tảng.'
            else:
                self.state, self.message = 'automatic', 'Giao diện hiện tại không cho tải ảnh bìa riêng; dùng ảnh nền tảng chọn.'
            self.close_editor()
        except Exception:
            self.state, self.message = 'needs_review', 'Không hoàn tất được bước đặt ảnh bìa. Cần kiểm tra ảnh sau khi đăng.'
            self.close_editor()

    def finalize(self):
        if self.state == 'pending':
            self.state, self.message = 'automatic', 'Không tìm thấy bước ảnh bìa được hỗ trợ; nền tảng dùng ảnh tự động.'
