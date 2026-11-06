"""Dedicated manual-login process; the dashboard requests Save or Cancel via SQLite."""
import argparse
import time
from .store import Store, PLATFORMS
from .worker import data_dir
from .browser import HOME, account_identity
from .profiles import launch_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', choices=PLATFORMS)
    parser.add_argument('owner')
    args = parser.parse_args()
    root = data_dir()
    store = Store(root / 'social.sqlite3')
    platform, owner = args.platform, args.owner
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            context = launch_profile(playwright, root, platform)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(HOME[platform], wait_until='domcontentloaded', timeout=60000)
                while True:
                    account = next(a for a in store.accounts() if a['platform'] == platform)
                    if account['lease_owner'] != owner or account['lease_until'] <= time.time():
                        raise RuntimeError('Đã hết 20 phút kết nối. Hãy mở đăng nhập lại.')
                    if not context.pages:
                        raise RuntimeError('Cửa sổ đã đóng trước khi lưu phiên.')
                    if account['state'] == 'cancel_requested':
                        raise RuntimeError('Đã hủy kết nối. Phiên này chưa được kích hoạt.')
                    if account['state'] == 'save_requested':
                        page = context.pages[0]
                        identity = account_identity(platform, context.cookies(), page)
                        if not identity:
                            raise RuntimeError('Chưa xác nhận được phiên và tài khoản. Đăng nhập xong, mở hồ sơ/kênh của bạn rồi lưu lại.')
                        # Flush the persistent profile BEFORE releasing its lease.
                        context.close()
                        context = None
                        store.complete_login(platform, owner, identity)
                        return
                    page = context.pages[0]
                    page.wait_for_timeout(500)
            finally:
                if context is not None:
                    context.close()
    except Exception as exc:
        store.login_failed(platform, owner, str(exc))


if __name__ == '__main__':
    main()
