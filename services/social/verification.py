"""Read-only publication confirmation on the authenticated platform profile."""
from collections import Counter
import logging
import math
import re
import time
import uuid
from urllib.parse import urljoin, urlsplit

LOG = logging.getLogger(__name__)
CONTENT = 'https://www.tiktok.com/tiktokstudio/content'
POSTS_API = '/tiktok/creator/manage/item_list/v1/'


def find_tiktok_receipt(payload, links, caption, earliest, latest):
    from .browser import valid_permalink
    if not isinstance(payload, dict) or payload.get('status_code') != 0 or not isinstance(payload.get('item_list'), list):
        return None
    normalize = lambda text: ' '.join(text.split()) if isinstance(text, str) else ''
    wanted = normalize(caption)
    if not wanted:
        return None
    matches = set()
    for item in payload['item_list']:
        if not isinstance(item, dict) or item.get('status') != 102 or normalize(item.get('desc')) != wanted:
            continue
        item_id = item.get('item_id')
        if not isinstance(item_id, str) or not re.fullmatch(r'\d+', item_id):
            continue
        try:
            posted = float(item['post_time'])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(posted) and earliest <= posted <= latest:
            matches.add(item_id)
    # Identical captions on multiple posts are ambiguous even if only one link is visible.
    if len(matches) != 1:
        return None
    item_id = next(iter(matches))
    urls = {url for url in links if valid_permalink('tiktok', url) and urlsplit(url).path.rstrip('/').endswith('/video/' + item_id)}
    return next(iter(urls)) if len(urls) == 1 else None


class TikTokPostIndex:
    def __init__(self, page):
        self.page = page
        self.items = {}
        self.listener = self._response
        page.on('response', self.listener)

    def _response(self, response):
        url = urlsplit(response.url)
        if url.scheme != 'https' or url.hostname != 'www.tiktok.com' or url.path != POSTS_API:
            return
        try:
            payload = response.json()
            if payload.get('status_code') == 0 and isinstance(payload.get('item_list'), list):
                for item in payload['item_list']:
                    if isinstance(item, dict) and isinstance(item.get('item_id'), str):
                        self.items[item['item_id']] = item
        except Exception:
            # A navigation may cancel a response; lack of evidence never confirms a post.
            return

    def find(self, caption, earliest, latest):
        url = urlsplit(self.page.url)
        if url.scheme != 'https' or url.hostname != 'www.tiktok.com' or url.path.rstrip('/') != '/tiktokstudio/content' or not self.items:
            return None
        from playwright.sync_api import Error
        try:
            links = [urljoin(self.page.url, href) for href in self.page.locator('a[href]').evaluate_all("els => els.map(a => a.getAttribute('href'))") if href]
        except Error:
            return None
        return find_tiktok_receipt({'status_code':0, 'item_list':list(self.items.values())}, links, caption, earliest, latest)

    def close(self):
        self.page.remove_listener('response', self.listener)


def collect_tiktok_receipts(root, identity, tasks):
    from playwright.sync_api import sync_playwright
    from .browser import account_identity
    from .profiles import launch_profile
    found = {}
    with sync_playwright() as playwright:
        context = launch_profile(playwright, root, 'tiktok')
        try:
            page = context.pages[0] if context.pages else context.new_page()
            index = TikTokPostIndex(page)
            try:
                page.goto(CONTENT, wait_until='domcontentloaded', timeout=45000)
                if account_identity('tiktok', context.cookies(), page) != identity:
                    return {}
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    for task in tasks:
                        if task['id'] in found:
                            continue
                        # Bound old attempts to their execution interval, not all historical posts.
                        earliest = max(task['ready_at'] - 60, task['updated_at'] - 1200)
                        link = index.find(task['caption'], earliest, task['updated_at'] + 120)
                        if link:
                            found[task['id']] = link
                    if len(found) == len(tasks):
                        break
                    page.wait_for_timeout(500)
            finally:
                index.close()
        finally:
            context.close()
    return found


def reconcile_pending(store, root, *, collector=None, now=None, platform='tiktok'):
    """Confirm uncertain tasks without uploading or clicking Publish again."""
    if platform not in ('tiktok', 'facebook'):
        raise ValueError('Không hỗ trợ đối chiếu nền tảng này.')
    now = time.time() if now is None else now
    owner = 'verify:' + uuid.uuid4().hex
    with store.transaction() as db:
        account = db.execute("SELECT * FROM accounts WHERE platform=?", (platform,)).fetchone()
        if account is None or account['state'] != 'connected' or (account['lease_owner'] and account['lease_until'] > now):
            return 0
        key = platform + '_verify_after'
        due = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        if due and float(due[0]) > now:
            return 0
        tasks = [dict(row) for row in db.execute("""SELECT t.*,b.caption FROM tasks t JOIN batches b ON b.id=t.batch_id
            WHERE t.platform=? AND t.state='needs_review' AND t.attempts>0 AND t.account_identity=?
            ORDER BY t.updated_at DESC""", (platform, account['identity']))]
        if not tasks:
            return 0
        identity = account['identity']
        db.execute("UPDATE accounts SET lease_owner=?,lease_until=? WHERE platform=?", (owner, now+180, platform))
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, str(now+600)))
    confirmed = 0
    try:
        if collector is None and platform == 'facebook':
            from .facebook_verification import collect_facebook_receipts
            collector = collect_facebook_receipts
        found = (collector or collect_tiktok_receipts)(root, identity, tasks)
        uses = Counter(found.values())
        from .browser import valid_permalink
        for task in tasks:
            url = found.get(task['id'])
            if platform == 'facebook' and not task.get('actor_identity'):
                continue
            if not url or uses[url] != 1 or not valid_permalink(platform, url):
                continue
            with store.transaction() as db:
                current = db.execute("SELECT identity,lease_owner FROM accounts WHERE platform=?", (platform,)).fetchone()
                if current['identity'] != identity or current['lease_owner'] != owner:
                    break
                post_id = urlsplit(url).path.rstrip('/').rsplit('/', 1)[-1]
                previous_urls = db.execute("SELECT url FROM tasks WHERE platform=? AND state='published' AND id!=?", (platform, task['id']))
                if any(urlsplit(row['url']).path.rstrip('/').rsplit('/', 1)[-1] == post_id for row in previous_urls):
                    continue
                result = db.execute("""UPDATE tasks SET state='published',url=?,message=?,updated_at=?,actor_identity=?
                    WHERE id=? AND state='needs_review' AND account_identity=?""",
                    (url, 'Hệ thống đã đối chiếu caption, thời điểm và link bài trên đúng tài khoản '+platform+'.', time.time(), task.get('actor_identity',''), task['id'], identity))
                confirmed += result.rowcount
    except Exception:
        LOG.warning('Automatic %s verification unavailable; preserving unconfirmed state.', platform, exc_info=True)
    finally:
        with store.transaction() as db:
            db.execute("UPDATE accounts SET lease_owner=NULL,lease_until=0 WHERE platform=? AND lease_owner=?", (platform,owner))
    return confirmed
