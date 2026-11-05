"""Durable schedules. Transactions also serialize profile leases and job claims."""
import hashlib
import json
import sqlite3
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

PLATFORMS = ('facebook', 'instagram', 'threads', 'tiktok', 'youtube')
LEASE_SECONDS = 1800
MISFIRE_SECONDS = 900


class Conflict(ValueError):
    pass


def media_hash(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS accounts (
                    platform TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'disconnected',
                    identity TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '',
                    lease_owner TEXT, lease_until REAL NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
                    request_digest TEXT NOT NULL, video_id TEXT NOT NULL,
                    media_path TEXT NOT NULL, media_hash TEXT NOT NULL,
                    caption TEXT NOT NULL, scheduled_at REAL NOT NULL,
                    made_for_kids INTEGER NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
                    platform TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                    ready_at REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                    owner TEXT, message TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
                    account_identity TEXT NOT NULL DEFAULT '',
                    updated_at REAL NOT NULL, UNIQUE(batch_id, platform)
                );
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS daily_runs (
                    slot_at REAL PRIMARY KEY, revision TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE,
                    video_id TEXT, state TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', batch_id TEXT,
                    created_at REAL NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS daily_video ON daily_runs(video_id) WHERE video_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS due_tasks ON tasks(state, ready_at);
                CREATE INDEX IF NOT EXISTS batch_video ON batches(video_id);
            ''')
            # Additive migration for schedules created by an earlier local build.
            if 'account_identity' not in {row['name'] for row in db.execute('PRAGMA table_info(tasks)')}:
                db.execute("ALTER TABLE tasks ADD COLUMN account_identity TEXT NOT NULL DEFAULT ''")
            db.executemany('INSERT OR IGNORE INTO accounts(platform) VALUES (?)', [(p,) for p in PLATFORMS])

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_batch(self, video_id, media_path, caption, scheduled_at, made_for_kids, request_key):
        path = Path(media_path).resolve(strict=True)
        snapshots = self.path.parent / 'media'
        snapshots.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=snapshots, suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                with path.open('rb') as source:
                    shutil.copyfileobj(source, stream)
            digest = media_hash(temporary)
            snapshot = snapshots / f'{digest}.mp4'
            if snapshot.exists():
                if media_hash(snapshot) != digest:
                    raise ValueError('Bản video đã lưu bị thay đổi. Kiểm tra thư mục data/social/media.')
            else:
                temporary.replace(snapshot)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        payload = json.dumps([video_id, str(path), digest, caption, scheduled_at, made_for_kids], ensure_ascii=False)
        request_digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.transaction() as db:
            existing = db.execute('SELECT id, request_digest FROM batches WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['request_digest'] != request_digest:
                    raise Conflict('Mã yêu cầu đã được dùng cho một lịch khác.')
                batch_id = existing['id']
            else:
                reservation = db.execute('SELECT * FROM daily_runs WHERE video_id=?', (video_id,)).fetchone()
                if reservation is not None:
                    if reservation['request_key'] != request_key:
                        raise Conflict('Video đã được giữ cho một khung giờ tự động. Hãy xử lý lịch gốc.')
                    config_row = db.execute("SELECT value FROM metadata WHERE key='daily_config'").fetchone()
                    config = json.loads(config_row['value']) if config_row else {}
                    if not config.get('enabled') or config.get('revision') != reservation['revision']:
                        raise Conflict('Lịch tự động đã tắt hoặc thay đổi. Không tạo bài từ cấu hình cũ.')
                batch_id = uuid.uuid4().hex
                now = time.time()
                db.execute('INSERT INTO batches VALUES (?,?,?,?,?,?,?,?,?,?)',
                           (batch_id, request_key, request_digest, video_id, str(snapshot), digest,
                            caption, scheduled_at, int(made_for_kids), now))
                identities = {row['platform']: row['identity'] for row in db.execute("SELECT platform,identity FROM accounts WHERE state='connected'")}
                db.executemany('INSERT INTO tasks(id,batch_id,platform,ready_at,updated_at,account_identity) VALUES (?,?,?,?,?,?)',
                               [(uuid.uuid4().hex, batch_id, p, scheduled_at, now, identities.get(p, '')) for p in PLATFORMS])
        return self.get_batch(batch_id)

    def get_batch(self, batch_id):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM batches WHERE id=?', (batch_id,)).fetchone()
            if row is None:
                raise KeyError(batch_id)
            result = dict(row)
            result['made_for_kids'] = bool(result['made_for_kids'])
            result['tasks'] = [dict(t) for t in db.execute('SELECT * FROM tasks WHERE batch_id=? ORDER BY rowid', (batch_id,))]
            return result

    def list_batches(self):
        with self.transaction() as db:
            ids = [row['id'] for row in db.execute('SELECT id FROM batches ORDER BY created_at DESC LIMIT 100')]
        return [self.get_batch(batch_id) for batch_id in ids]

    def find_request(self, request_key):
        with self.transaction() as db:
            row = db.execute('SELECT id FROM batches WHERE request_key=?', (request_key,)).fetchone()
        return self.get_batch(row['id']) if row else None

    def get_daily(self):
        from .daily import DEFAULT_CONFIG
        with self.transaction() as db:
            row = db.execute("SELECT value FROM metadata WHERE key='daily_config'").fetchone()
        return json.loads(row['value']) if row else {**DEFAULT_CONFIG, 'times': []}

    def get_caption_hashtags(self):
        with self.transaction() as db:
            row=db.execute("SELECT value FROM metadata WHERE key='caption_hashtags'").fetchone()
        return row['value'] if row else ''

    def get_caption_provider(self):
        with self.transaction() as db:
            row=db.execute("SELECT value FROM metadata WHERE key='caption_provider'").fetchone()
        return json.loads(row['value']) if row else {}

    def save_caption_provider(self,body):
        from services.captions.provider import validate_provider_update
        updates=validate_provider_update(body)
        with self.transaction() as db:
            row=db.execute("SELECT value FROM metadata WHERE key='caption_provider'").fetchone()
            value=json.loads(row['value']) if row else {}
            value.update(updates)
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('caption_provider', ?)",(json.dumps(value),))

    def save_caption_hashtags(self,value):
        from services.captions.hashtags import normalize_hashtags
        value=normalize_hashtags(value)
        with self.transaction() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('caption_hashtags', ?)",(value,))
        return value

    def save_daily(self, config, now=None):
        from .daily import validate_config
        value = validate_config(config)
        value.update(active_from=time.time() if now is None else now, revision=uuid.uuid4().hex)
        with self.transaction() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('daily_config', ?)", (json.dumps(value),))
        return value

    def daily_runs(self):
        with self.transaction() as db:
            return [dict(row) for row in db.execute('SELECT * FROM daily_runs ORDER BY slot_at DESC LIMIT 50')]

    def used_video_ids(self):
        with self.transaction() as db:
            return {row[0] for row in db.execute('SELECT video_id FROM batches UNION SELECT video_id FROM daily_runs WHERE video_id IS NOT NULL')}

    def accounts(self):
        with self.transaction() as db:
            return [dict(row) for row in db.execute('SELECT * FROM accounts ORDER BY rowid')]

    def publication_summary(self, video_ids):
        result={video_id:{} for video_id in video_ids}
        if not result:
            return result
        ids=list(result)
        rows=[]
        with self.transaction() as db:
            for offset in range(0,len(ids),500):
                chunk=ids[offset:offset+500]
                placeholders=','.join('?' for _ in chunk)
                rows.extend(db.execute(f'''SELECT b.video_id,t.platform,t.state,t.url,t.updated_at,b.created_at
                               FROM tasks t JOIN batches b ON b.id=t.batch_id
                               WHERE b.video_id IN ({placeholders})
                               ORDER BY b.created_at DESC,t.updated_at DESC''',chunk).fetchall())
        for row in rows:
            if row['video_id'] not in result:
                continue
            platforms=result[row['video_id']]
            current=platforms.get(row['platform'])
            if current is None or (row['state']=='published' and current['state']!='published'):
                platforms[row['platform']]={'state':row['state'],'url':row['url'] if row['state']=='published' else '',
                                            'updated_at':row['updated_at']}
        return result

    def begin_login(self, platform, now=None):
        if platform not in PLATFORMS:
            raise ValueError('Nền tảng không hợp lệ.')
        now = time.time() if now is None else now
        owner = 'login:' + uuid.uuid4().hex
        with self.transaction() as db:
            result = db.execute('''UPDATE accounts SET state='connecting', lease_owner=?, lease_until=?, message=''
                                   WHERE platform=? AND lease_until<=?''', (owner, now + 1200, platform, now))
            if not result.rowcount:
                raise Conflict('Trình duyệt tài khoản này đang được sử dụng.')
        return owner

    def login_command(self, platform, command):
        if command not in ('save_requested', 'cancel_requested'):
            raise ValueError('Lệnh đăng nhập không hợp lệ.')
        with self.transaction() as db:
            result = db.execute("UPDATE accounts SET state=? WHERE platform=? AND state IN ('connecting','save_requested') AND lease_until>?",
                                (command, platform, time.time()))
            if not result.rowcount:
                raise Conflict('Không có cửa sổ đăng nhập đang hoạt động.')

    def complete_login(self, platform, owner, identity, now=None):
        now = time.time() if now is None else now
        if not identity:
            raise ValueError('Chưa tìm thấy phiên đăng nhập.')
        with self.transaction() as db:
            result = db.execute("""UPDATE accounts SET state='connected', identity=?, message='Phiên đã lưu; kiểm tra đúng tài khoản trong trình duyệt.',
                                   lease_owner=NULL, lease_until=0 WHERE platform=? AND lease_owner=? AND lease_until>?""",
                                (identity, platform, owner, now))
            if not result.rowcount:
                raise Conflict('Phiên đăng nhập đã hết thời gian hoặc đổi chủ.')

    def login_failed(self, platform, owner, message):
        with self.transaction() as db:
            db.execute("UPDATE accounts SET state='needs_login',message=?,lease_owner=NULL,lease_until=0 WHERE platform=? AND lease_owner=?",
                       (message[:500], platform, owner))

    def heartbeat(self, task_id=None):
        with self.transaction() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('worker_seen', ?)", (str(time.time()),))
            if task_id is not None:
                db.execute('UPDATE accounts SET lease_until=? WHERE lease_owner=?', (time.time() + LEASE_SECONDS, 'task:' + task_id))

    def worker_seen(self):
        with self.transaction() as db:
            row = db.execute("SELECT value FROM metadata WHERE key='worker_seen'").fetchone()
            return float(row['value']) if row else 0

    def claim_next(self, owner, now=None):
        now = time.time() if now is None else now
        with self.transaction() as db:
            db.execute("""UPDATE tasks SET state='needs_review',message='Đã lỡ lịch hơn 15 phút. Kiểm tra và chọn thử lại nếu muốn đăng bây giờ.',updated_at=?
                          WHERE state='queued' AND ready_at<?""", (now, now - MISFIRE_SECONDS))
            rows = db.execute('''SELECT t.*,b.media_path,b.media_hash,b.caption,b.made_for_kids,a.state AS account_state,
                                 a.lease_until,a.identity FROM tasks t JOIN batches b ON b.id=t.batch_id
                                 JOIN accounts a ON a.platform=t.platform
                                 WHERE t.state='queued' AND t.ready_at<=? ORDER BY t.ready_at,t.rowid''', (now,)).fetchall()
            for row in rows:
                if row['lease_until'] > now:
                    continue
                if row['account_state'] != 'connected':
                    db.execute("UPDATE tasks SET state='needs_login',message='Cần đăng nhập và lưu phiên trước khi thử lại.',updated_at=? WHERE id=?", (now, row['id']))
                    continue
                if row['account_identity'] and row['account_identity'] != row['identity']:
                    db.execute("UPDATE tasks SET state='needs_login',message='Tài khoản đã đổi sau khi lên lịch. Kết nối lại tài khoản cũ hoặc tạo lịch mới.',updated_at=? WHERE id=?", (now, row['id']))
                    continue
                db.execute("UPDATE tasks SET state='running',owner=?,attempts=attempts+1,updated_at=? WHERE id=?", (owner, now, row['id']))
                db.execute('UPDATE accounts SET lease_owner=?,lease_until=? WHERE platform=?',
                           ('task:' + row['id'], now + LEASE_SECONDS, row['platform']))
                result = dict(row)
                result.update(owner=owner, state='running', attempts=row['attempts'] + 1)
                return result
        return None

    def mark_submitting(self, task_id, owner):
        with self.transaction() as db:
            result = db.execute("UPDATE tasks SET state='submitting',updated_at=? WHERE id=? AND owner=? AND state='running'", (time.time(), task_id, owner))
            if not result.rowcount:
                raise Conflict('Tác vụ không còn thuộc worker này.')

    def task_state(self, task_id):
        with self.transaction() as db:
            row = db.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            return row['state']

    def finish(self, task_id, owner, state, message='', url=''):
        if state not in ('published', 'failed', 'needs_login', 'needs_review'):
            raise ValueError('Trạng thái kết thúc không hợp lệ.')
        with self.transaction() as db:
            task = db.execute('SELECT * FROM tasks WHERE id=? AND owner=?', (task_id, owner)).fetchone()
            if task is None or task['state'] not in ('running', 'submitting'):
                raise Conflict('Tác vụ không còn thuộc worker này.')
            if state == 'published' and (task['state'] != 'submitting' or not url):
                raise Conflict('Chưa xác nhận thao tác xuất bản và link bài.')
            if task['state'] == 'submitting' and state in ('failed', 'needs_login'):
                state = 'needs_review'
            db.execute('UPDATE tasks SET state=?,message=?,url=?,owner=NULL,updated_at=? WHERE id=?',
                       (state, message[:1000], url, time.time(), task_id))
            db.execute('UPDATE accounts SET lease_owner=NULL,lease_until=0 WHERE lease_owner=?', ('task:' + task_id,))
            if state == 'needs_login':
                db.execute("UPDATE accounts SET state='needs_login',message=? WHERE platform=?", (message[:500], task['platform']))

    def recover_interrupted(self):
        """Only call after acquiring the exclusive worker process lock."""
        with self.transaction() as db:
            db.execute("UPDATE tasks SET state='needs_review',owner=NULL,message='Worker dừng sau khi bắt đầu xuất bản. Kiểm tra bài trước khi thử lại.' WHERE state='submitting'")
            db.execute("UPDATE tasks SET state='failed',owner=NULL,message='Worker dừng trước khi xuất bản. Có thể thử lại.' WHERE state='running'")
            db.execute("UPDATE accounts SET lease_owner=NULL,lease_until=0 WHERE lease_owner LIKE 'task:%'")

    def retry(self, task_id, confirmed_not_posted=False, now=None):
        now = time.time() if now is None else now
        with self.transaction() as db:
            row = db.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            if row['state'] not in ('failed', 'needs_login', 'needs_review'):
                raise Conflict('Chỉ thử lại nền tảng bị lỗi hoặc cần kiểm tra.')
            if row['state'] == 'needs_review' and not confirmed_not_posted:
                raise Conflict('Hãy kiểm tra tài khoản và xác nhận chưa có bài trước khi thử lại.')
            db.execute("UPDATE tasks SET state='queued',ready_at=?,message='',url='',owner=NULL,updated_at=? WHERE id=?", (now, now, task_id))

    def cancel_batch(self, batch_id):
        with self.transaction() as db:
            if not db.execute('SELECT id FROM batches WHERE id=?', (batch_id,)).fetchone():
                raise KeyError(batch_id)
            db.execute("UPDATE tasks SET state='cancelled',message='Đã hủy.',updated_at=? WHERE batch_id=? AND state IN ('queued','failed','needs_login','needs_review')", (time.time(), batch_id))

    def resolve(self, task_id, url):
        from .browser import valid_permalink
        with self.transaction() as db:
            task = db.execute('SELECT platform,state FROM tasks WHERE id=?', (task_id,)).fetchone()
            if task is None:
                raise KeyError(task_id)
            if task['state'] != 'needs_review':
                raise Conflict('Chỉ xác nhận thủ công cho tác vụ cần kiểm tra.')
            if not valid_permalink(task['platform'], url):
                raise ValueError('Link bài không đúng nền tảng hoặc không phải link bài đăng.')
            db.execute("UPDATE tasks SET state='published',url=?,message='Bạn đã kiểm tra và xác nhận bài đã đăng.',updated_at=? WHERE id=?",
                       (url, time.time(), task_id))
