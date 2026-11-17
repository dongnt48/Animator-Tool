"""Optional cover UI. Never use the video upload input or infer success from a filename."""
import re
import time
import hashlib


ROOTS = ('ytcp-video-thumbnail-editor', '#thumbnail-editor', '[data-testid="cover-editor"]', '.cover-container',
         '[data-e2e="cover_container"]', '[aria-label="Cover photo"]', '[aria-label="Ảnh bìa"]',
         '[role="dialog"][aria-label*="cover" i]', '[role="dialog"][aria-label*="thumbnail" i]',
         '[role="dialog"][aria-label*="ảnh bìa" i]', '[role="dialog"][aria-label*="hình thu nhỏ" i]')
OPEN = re.compile(r'^(Edit cover|Select cover|Change cover|Upload thumbnail|Edit thumbnail|Chỉnh sửa ảnh bìa|Chọn ảnh bìa|Đổi ảnh bìa|Tải hình thu nhỏ lên)$', re.I)
EDITOR_TITLE = re.compile(r'^(Chọn hình thu nhỏ|Choose thumbnail|Select thumbnail|Edit thumbnail|Edit cover|Chọn ảnh bìa)$', re.I)
IMAGE_INPUT = ('input[type="file"][accept*="image" i], input[type="file"][accept*=".jpg" i], '
               'input[type="file"][accept*=".jpeg" i], input[type="file"][accept*=".png" i], input[type="file"][accept*=".webp" i]')
SAVE = re.compile(r'^(Save|Done|Lưu|Xong)$', re.I)


class CoverFlow:
    def __init__(self, page, cover=None):
        self.page, self.cover = page, cover or {}
        self.state = 'pending' if cover else 'automatic'
        self.message = '' if cover else 'Lịch này không có ảnh bìa riêng; nền tảng chọn ảnh tự động.'
        self.attempted = False

    def editors(self):
        scopes = []
        for dialog in self.page.locator('[role="dialog"], [aria-modal="true"]').all():
            label = dialog.get_attribute('aria-label') or ''
            # TikTok's title is plain text, without a heading role or aria-label.
            text_title = (any(t.is_visible() for t in dialog.get_by_text(EDITOR_TITLE).all())
                          and dialog.get_by_role('button', name=SAVE).count()
                          and (dialog.locator(IMAGE_INPUT).count() or
                               (dialog.get_attribute('data-dialog-content') == 'true'
                                and dialog.get_by_role('button', name=re.compile(r'^(Cancel|Hủy)$', re.I)).count())))
            if dialog.is_visible() and (text_title or EDITOR_TITLE.fullmatch(label) or any(h.is_visible() for h in dialog.get_by_role('heading', name=EDITOR_TITLE).all())
                                       or re.search(r'cover|thumbnail|ảnh bìa|hình thu nhỏ', label, re.I)):
                scope = dialog
                # Facebook labels only the header as dialog. Its picker and
                # footer are siblings in the immediate modal wrapper.
                if not dialog.get_by_role('button', name=SAVE).count():
                    parent = dialog.locator('..')
                    if parent.locator(IMAGE_INPUT).count() and parent.get_by_role('button', name=SAVE).count():
                        scope = parent
                scopes.append(scope)
        return scopes

    def root(self):
        editors = self.editors()
        if editors:
            return editors[0]
        for selector in ROOTS:
            for item in self.page.locator(selector).all():
                if item.is_visible():
                    return item
        return None

    def previews(self, *, loaded_only=True):
        sources = set()
        for editor in self.editors():
            for item in editor.locator('img').all():
                if item.is_visible() and (not loaded_only or item.evaluate('(image) => image.complete && image.naturalWidth > 0')):
                    sources.add(item.get_attribute('src'))
            # TikTok renders the uploaded cover on a canvas and removes the
            # upload input. Read pixels rather than treating its filename as proof.
            from playwright.sync_api import Error
            for canvas in editor.locator('canvas').all():
                if not canvas.is_visible() or 'upper' in (canvas.get_attribute('class') or '').lower():
                    continue
                try:
                    pixels = canvas.evaluate('''canvas => {
                        if (!canvas.width || !canvas.height) return null;
                        const sample = document.createElement('canvas');
                        sample.width = Math.min(64, canvas.width); sample.height = Math.min(64, canvas.height);
                        const context = sample.getContext('2d'); context.drawImage(canvas, 0, 0, sample.width, sample.height);
                        const data = context.getImageData(0, 0, sample.width, sample.height).data;
                        let first = null, rendered = false;
                        for (let i = 0; i < data.length; i += 4) {
                            if (!data[i+3]) continue;
                            const color = (data[i] << 24) | (data[i+1] << 16) | (data[i+2] << 8) | data[i+3];
                            if (first === null) first = color;
                            else if (first !== color) { rendered = true; break; }
                        }
                        return rendered ? canvas.toDataURL() : null;
                    }''')
                    if pixels:
                        sources.add('canvas:' + hashlib.sha256(pixels.encode()).hexdigest())
                except Error:
                    continue
        for selector in ROOTS:
            for item in self.page.locator(selector+' img').all():
                if item.is_visible() and (not loaded_only or item.evaluate('(image) => image.complete && image.naturalWidth > 0')):
                    sources.add(item.get_attribute('src'))
        return sources

    def close_editor(self, *, save=True, wait_for_save=False):
        # Only close a specifically named cover editor; never click a composer Submit button.
        for dialog in self.editors():
            handle = dialog.element_handle()
            if save:
                if wait_for_save:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        if any(button.is_visible() and button.is_enabled() for button in dialog.get_by_role('button', name=SAVE).all()):
                            break
                        self.page.wait_for_timeout(100)
                for button in dialog.get_by_role('button', name=SAVE).all():
                    if button.is_visible() and button.is_enabled():
                        button.click()
                        handle.wait_for_element_state('hidden', timeout=10000)
                        return True
            for button in dialog.get_by_role('button', name=re.compile(r'^(Close|Cancel|Đóng|Hủy|Đóng hộp thoại của công cụ tạo)$', re.I)).all():
                if button.is_visible() and button.is_enabled():
                    button.click()
                    handle.wait_for_element_state('hidden', timeout=10000)
                    return False
        return not self.editors()

    def apply(self, platform):
        self.platform = platform
        if not self.cover or self.attempted:
            return
        if platform == 'threads':
            self.state, self.message = 'automatic', 'Luồng Threads hiện dùng ảnh xem trước tự động; không tải ảnh bìa riêng.'
            self.attempted = True
            return
        scope = self.root()
        buttons = [b for b in self.page.get_by_role('button', name=OPEN).all() if b.is_visible() and b.is_enabled()]
        if platform == 'tiktok' and scope is not None and not buttons:
            buttons = [b for b in scope.get_by_text(OPEN).all() if b.is_visible() and b.is_enabled()]
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
                inputs = scope.locator(IMAGE_INPUT)
                if inputs.count():
                    before = self.previews(loaded_only=False)
                    inputs.first.set_input_files(path)
                    uploaded = True
                elif platform == 'facebook' and self.editors():
                    upload = scope.get_by_role('button', name=re.compile(r'^(Upload|Upload image|Upload photo|Tải lên|Tải ảnh lên)$', re.I))
                    if upload.count() and upload.first.is_visible() and upload.first.is_enabled():
                        with self.page.expect_file_chooser(timeout=10000) as chooser:
                            upload.first.click()
                        before = self.previews(loaded_only=False)
                        chooser.value.set_files(path)
                        uploaded = True
            if uploaded:
                deadline = time.monotonic()+4
                while time.monotonic() < deadline:
                    if self.previews()-before:
                        if self.close_editor(wait_for_save=True):
                            self.state, self.message = 'applied', 'Đã thấy ảnh bìa mới trong giao diện xem trước trước khi đăng.'
                        else:
                            self.state, self.message = 'needs_review', 'Ảnh đã gửi nhưng chưa lưu được trong trình chọn ảnh bìa.'
                        return
                    self.page.wait_for_timeout(150)
                self.state, self.message = 'needs_review', 'Đã gửi ảnh nhưng chưa xác minh được ảnh bìa mới trong xem trước.'
            elif platform != 'tiktok' and scope is not None and self.cover.get('mode') == 'frame' and self.cover.get('duration'):
                sliders = scope.locator('input[type="range"], [role="slider"]')
                if sliders.count() == 1 and sliders.first.is_visible():
                    slider = sliders.first
                    old = slider.evaluate('(e) => e.value ?? e.getAttribute("aria-valuenow")')
                    box = slider.bounding_box()
                    fraction = max(0, min(.999, float(self.cover.get('timestamp') or 0)/float(self.cover['duration'])))
                    self.page.mouse.click(box['x']+box['width']*fraction, box['y']+box['height']/2)
                    new = slider.evaluate('(e) => e.value ?? e.getAttribute("aria-valuenow")')
                    saved = self.close_editor(wait_for_save=True)
                    if old != new and new is not None and saved:
                        self.state, self.message = 'frame', 'Đã chọn khung từ video. Chữ trên ảnh bìa riêng không được tải lên.'
                        return
                self.state, self.message = 'automatic', 'Không xác minh được bộ chọn khung; dùng ảnh xem trước của nền tảng.'
            else:
                self.state, self.message = 'automatic', 'Giao diện hiện tại không cho tải ảnh bìa riêng; dùng ảnh nền tảng chọn.'
            self.close_editor()
        except Exception:
            self.state, self.message = 'needs_review', 'Không hoàn tất được bước đặt ảnh bìa. Cần kiểm tra ảnh sau khi đăng.'
            self.close_editor(save=False)

    def finalize(self):
        if self.state == 'pending':
            self.state, self.message = 'automatic', 'Không tìm thấy bước ảnh bìa được hỗ trợ; nền tảng dùng ảnh tự động.'
        if getattr(self, 'platform', None) == 'tiktok' and self.cover and self.state != 'applied':
            self.state = 'needs_review'
            self.message = 'Chưa xác minh được ảnh bìa của app trên TikTok. Đã dừng trước khi đăng; không dùng ảnh tự động thay thế.'
            raise ValueError(self.message)
