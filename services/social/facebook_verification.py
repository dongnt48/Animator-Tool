"""Read-only Facebook Story evidence scoped to the active profile/Page actor."""
import json
import math
import sqlite3
import time
from urllib.parse import urlsplit


def facebook_actor(cookies):
    values = {c['name']:c.get('value') for c in cookies
              if (c.get('domain','').lstrip('.') == 'facebook.com' or c.get('domain','').lstrip('.').endswith('.facebook.com'))}
    return values.get('i_user') or values.get('c_user')


def facebook_actor_history(root,cookies):
    """Legacy attempts may use only an actor cookie unchanged since before them."""
    from .profiles import profile_path
    active = facebook_actor(cookies)
    cookie = next((c for c in cookies if c.get('name')=='i_user' and c.get('value')==active
                   and c.get('domain','').lstrip('.') in ('facebook.com','www.facebook.com')),None)
    if not cookie:
        return None
    profile = profile_path(root,'facebook')/'Default'
    path = profile/'Cookies'
    if not path.is_file():
        path = profile/'Network'/'Cookies'
    try:
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            row = db.execute("SELECT creation_utc,last_update_utc,value FROM cookies WHERE host_key=? AND name='i_user' AND path=?",
                             (cookie['domain'],cookie.get('path','/'))).fetchone()
        # Encrypted or stale disk values cannot prove a legacy actor. New
        # attempts use the actor persisted at the publication checkpoint.
        if row and row[2] and row[2] == active:
            created,updated = (float(v)/1000000-11644473600 for v in row[:2])
            if 0 < created <= updated <= time.time()+5:
                return active,updated
    except (sqlite3.Error,OSError,ValueError,TypeError):
        pass
    return None


def facebook_story_receipts(payload, actor_id):
    from .browser import valid_permalink
    if not actor_id:
        return []
    records = []
    pending = [payload]
    while pending:
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        pending.extend(v for v in node.values() if isinstance(v, (dict,list)))
        if node.get('__typename') != 'Story' or not node.get('post_id'):
            continue
        sections = node.get('comet_sections') or {}
        content = sections.get('content') if isinstance(sections,dict) else None
        story = content.get('story') if isinstance(content,dict) else None
        story = story if isinstance(story,dict) else {}
        actors = node.get('actors') or story.get('actors')
        message = node.get('message') or story.get('message')
        text = message.get('text') if isinstance(message,dict) else None
        if not isinstance(actors,list) or not actors or not isinstance(actors[0],dict) or actors[0].get('id') != actor_id or not isinstance(text,str):
            continue
        try:
            posted = float(node['creation_time'])
        except (KeyError,TypeError,ValueError):
            continue
        url = node.get('permalink_url')
        if isinstance(node['creation_time'],bool) or not math.isfinite(posted) or not valid_permalink('facebook',url):
            continue
        video_id = urlsplit(url).path.rstrip('/').rsplit('/',1)[-1]
        attachments = node.get('attachments')
        if not isinstance(attachments,list) or not attachments or not isinstance(attachments[0],dict):
            continue
        styles = attachments[0].get('styles') or {}
        attachment = styles.get('attachment') if isinstance(styles,dict) else None
        media = attachment.get('media') if isinstance(attachment,dict) else None
        if (not isinstance(media,dict) or media.get('__typename')!='Video' or media.get('id')!=video_id
                or not isinstance(media.get('owner'),dict) or media['owner'].get('id')!=actor_id):
            continue
        records.append({'caption':text,'posted_at':posted,'url':'https://www.facebook.com/reel/'+video_id})
    return records


def find_facebook_receipt(records, caption, earliest, latest):
    if not isinstance(caption,str) or not caption.strip():
        return None
    normalize = lambda text:' '.join(text.split())
    urls = {r['url'] for r in records if normalize(r['caption']) == normalize(caption) and earliest <= r['posted_at'] <= latest}
    return next(iter(urls)) if len(urls)==1 else None


class FacebookPostIndex:
    def __init__(self,page,actor_id):
        self.page, self.actor_id = page, actor_id
        self.records = {}
        self.seen_scripts = set()
        self.listener = self._response
        page.on('response',self.listener)

    def ingest(self,payload):
        for record in facebook_story_receipts(payload,self.actor_id):
            self.records[record['url']] = record

    def _response(self,response):
        url = urlsplit(response.url)
        if url.scheme != 'https' or url.hostname not in ('facebook.com','www.facebook.com') or url.path != '/api/graphql/':
            return
        try:
            raw = response.text()
            if raw.startswith('for (;;);'):
                raw = raw[9:]
            for line in raw.splitlines():
                try:
                    self.ingest(json.loads(line))
                except ValueError:
                    continue
        except Exception:
            return  # A cancelled request is not publication evidence.

    def read_embedded(self):
        from playwright.sync_api import Error
        url = urlsplit(self.page.url)
        if url.scheme != 'https' or url.hostname not in ('facebook.com','www.facebook.com'):
            return
        try:
            for raw in self.page.locator('script[type="application/json"]').all_text_contents():
                signature = hash(raw)
                if signature in self.seen_scripts:
                    continue
                self.seen_scripts.add(signature)
                try:
                    self.ingest(json.loads(raw))
                except ValueError:
                    continue
        except Error:
            return

    def find(self,caption,earliest,latest):
        self.read_embedded()
        return find_facebook_receipt(self.records.values(),caption,earliest,latest)

    def close(self):
        self.page.remove_listener('response',self.listener)


def collect_facebook_receipts(root,identity,tasks):
    from playwright.sync_api import sync_playwright
    from .browser import account_identity
    from .profiles import launch_profile
    found = {}
    with sync_playwright() as playwright:
        context = launch_profile(playwright,root,'facebook')
        try:
            active_actor = facebook_actor(context.cookies())
            if not active_actor:
                return {}
            page = context.pages[0] if context.pages else context.new_page()
            groups = {}
            history = facebook_actor_history(root,context.cookies())
            for task in tasks:
                actor = task.get('actor_identity')
                if not actor:
                    if not history or history[1] > task['ready_at']:
                        continue
                    actor = history[0]
                    task['actor_identity'] = actor
                groups.setdefault(actor,[]).append(task)
            # Keep every profile inspection inside the account's 180-second lease.
            overall_deadline = time.monotonic()+100
            for actor_id, group in groups.items():
                remaining = overall_deadline-time.monotonic()
                if remaining <= 1:
                    break
                if not isinstance(actor_id,str) or not actor_id.isdigit():
                    continue
                index = FacebookPostIndex(page,actor_id)
                try:
                    target = 'https://www.facebook.com/me/' if actor_id==active_actor else 'https://www.facebook.com/profile.php?id='+actor_id
                    page.goto(target,wait_until='domcontentloaded',timeout=min(45000,int(remaining*1000)))
                    if account_identity('facebook',context.cookies(),page)!=identity:
                        return {}
                    deadline = min(overall_deadline,time.monotonic()+30)
                    quiet = 0
                    while time.monotonic()<deadline:
                        previous = len(index.records)
                        index.read_embedded()
                        for task in group:
                            earliest = max(task['ready_at']-60,task['updated_at']-1200)
                            link = find_facebook_receipt(index.records.values(),task['caption'],earliest,task['updated_at']+120)
                            if link:
                                found[task['id']] = link
                            else:
                                found.pop(task['id'],None)
                        if all(task['id'] in found for task in group):
                            break
                        quiet = quiet+1 if len(index.records)==previous else 0
                        if index.records and quiet>=5:
                            break
                        page.mouse.wheel(0,1800)
                        page.wait_for_timeout(800)
                finally:
                    index.close()
        finally:
            context.close()
    return found
