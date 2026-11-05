"""Daily local-time slots select one unused library item, never one item per platform."""
import json
import logging
import random
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .store import Conflict, MISFIRE_SECONDS

DEFAULT_CONFIG = {'enabled':False, 'times':[], 'timezone':'Asia/Bangkok',
                  'selection':'random', 'made_for_kids':None, 'active_from':0, 'revision':''}
TIMEZONES = ('Asia/Bangkok', 'Asia/Ho_Chi_Minh', 'UTC')


def validate_config(value):
    if not isinstance(value, dict) or type(value.get('enabled')) is not bool:
        raise ValueError('Trạng thái tự động phải là bật hoặc tắt.')
    times = value.get('times')
    if not isinstance(times, list) or len(times) > 24 or any(not isinstance(t, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in times):
        raise ValueError('Chọn tối đa 24 khung giờ hợp lệ theo định dạng HH:MM.')
    if value['enabled'] and not times:
        raise ValueError('Thêm ít nhất một khung giờ trước khi bật tự động.')
    zone = value.get('timezone', 'Asia/Bangkok')
    if zone not in TIMEZONES:
        raise ValueError('Múi giờ không được hỗ trợ.')
    try:
        ZoneInfo(zone)
    except ZoneInfoNotFoundError:
        raise ValueError('Chưa có dữ liệu múi giờ. Chạy setup.bat để cài tzdata.') from None
    selection = value.get('selection', 'random')
    if selection not in ('fifo', 'random'):
        raise ValueError('Cách lấy bài không hợp lệ.')
    audience = value.get('made_for_kids')
    if (audience is not None and type(audience) is not bool) or (value['enabled'] and type(audience) is not bool):
        raise ValueError('Chọn đối tượng khán giả YouTube trước khi bật tự động.')
    return {'enabled':value['enabled'], 'times':sorted(set(times)), 'timezone':zone,
            'selection':selection, 'made_for_kids':audience}


def validated_output(video, outputs_dir):
    name = video.get('output_filename', '')
    if not isinstance(name, str) or not name or '/' in name or '\\' in name or Path(name).suffix.lower() != '.mp4':
        raise ValueError('Video chưa có file MP4 đầu ra hợp lệ.')
    root = Path(outputs_dir).resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise ValueError('File video đầu ra không tồn tại hoặc nằm ngoài thư mục outputs.')
    return path


def caption_of(video):
    caption = video.get('caption', video.get('title', ''))
    if not isinstance(caption, str) or not caption.strip() or len(caption) > 10000:
        raise ValueError('Video chưa có caption hợp lệ. Hãy kiểm tra nội dung nguồn.')
    return caption


def ready_content(videos, outputs_dir):
    result = []
    for video in videos:
        if video.get('status') != 'completed' or not isinstance(video.get('id'), str):
            continue
        try:
            path, caption = validated_output(video, outputs_dir), caption_of(video)
        except ValueError:
            continue
        result.append({'id':video['id'], 'caption':caption, 'media_path':str(path),
                       'output_filename':path.name, 'aspect_ratio':video.get('aspect_ratio',''),
                       'duration_sec':video.get('duration_sec',0)})
    return result


def library_content():
    import database
    return ready_content(database.get_all_videos(), Path(__file__).resolve().parents[2] / 'outputs')


def local_slots(config, now):
    zone = ZoneInfo(config['timezone'])
    today = datetime.fromtimestamp(now, zone).date()
    result = []
    for day in (today - timedelta(days=1), today, today + timedelta(days=1)):
        for value in config['times']:
            hour, minute = map(int, value.split(':'))
            result.append(datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone).timestamp())
    return sorted(set(result))


def daily_status(store, items, now=None):
    now = time.time() if now is None else now
    config = store.get_daily()
    used = store.used_video_ids()
    available = [item for item in items if item['id'] not in used]
    future = [slot for slot in local_slots(config, now) if slot > now] if config['enabled'] else []
    return {'config':config, 'available_count':len(available), 'preview':[item['caption'] for item in available[:3]],
            'next_at':min(future) if future else None, 'runs':store.daily_runs()}


class DailyScheduler:
    def __init__(self, store, provider=None):
        self.store = store
        self.provider = provider or library_content
        self.lock = threading.Lock()

    def reserve(self, slot, config, items, now, reason=''):
        with self.store.transaction() as db:
            current = db.execute("SELECT value FROM metadata WHERE key='daily_config'").fetchone()
            current = json.loads(current['value']) if current else {}
            if not current.get('enabled') or current.get('revision') != config['revision']:
                return None
            existing = db.execute('SELECT * FROM daily_runs WHERE slot_at=?', (slot,)).fetchone()
            if existing:
                return dict(existing) if existing['state'] == 'preparing' else None
            used = {row[0] for row in db.execute('SELECT video_id FROM batches UNION SELECT video_id FROM daily_runs WHERE video_id IS NOT NULL')}
            available = [item for item in items if item['id'] not in used]
            connected = db.execute("SELECT 1 FROM accounts WHERE state='connected' LIMIT 1").fetchone()
            state, message, item = 'preparing', '', None
            if reason:
                state, message = 'skipped', reason
            elif not connected:
                state, message = 'blocked', 'Chưa có nền tảng nào lưu phiên; không lấy bài.'
            elif not available:
                state, message = 'empty', 'Hết video chưa dùng; bỏ qua khung giờ này.'
            else:
                item = random.choice(available) if config['selection'] == 'random' else available[0]
            key = f'daily-{int(slot)}'
            db.execute('INSERT INTO daily_runs(slot_at,revision,request_key,video_id,state,message,batch_id,created_at) VALUES (?,?,?,?,?,?,?,?)',
                       (slot, config['revision'], key, item['id'] if item else None, state, message, None, now))
            row = db.execute('SELECT * FROM daily_runs WHERE slot_at=?', (slot,)).fetchone()
            return dict(row) if state == 'preparing' else None

    def record(self, run, state, message, batch_id=None):
        with self.store.transaction() as db:
            db.execute('UPDATE daily_runs SET state=?,message=?,batch_id=? WHERE slot_at=?',
                       (state, message[:500], batch_id, run['slot_at']))

    def complete(self, run, config, items):
        existing = self.store.find_request(run['request_key'])
        if existing is not None:
            self.record(run, 'scheduled', 'Đã lấy một video cho cả 5 nền tảng.', existing['id'])
            return existing
        if not config['enabled'] or run['revision'] != config['revision']:
            self.record(run, 'cancelled', 'Cấu hình đã tắt hoặc thay đổi; không lấy thêm bài.')
            return None
        item = next((item for item in items if item['id'] == run['video_id']), None)
        if item is None:
            self.record(run, 'error', 'Video đã giữ không còn sẵn sàng. Không tự chọn bài thay thế.')
            return None
        try:
            batch = self.store.create_batch(item['id'], item['media_path'], item['caption'], run['slot_at'],
                                            config['made_for_kids'], run['request_key'])
        except Exception as exc:
            # A concurrent tick may have completed the same idempotent request already.
            existing = self.store.find_request(run['request_key'])
            if existing is not None:
                self.record(run, 'scheduled', 'Đã lấy một video cho cả 5 nền tảng.', existing['id'])
                return existing
            self.record(run, 'cancelled' if isinstance(exc, Conflict) else 'error', str(exc))
            return None
        self.record(run, 'scheduled', 'Đã lấy một video cho cả 5 nền tảng.', batch['id'])
        return batch

    def tick(self, now=None):
        if not self.lock.acquire(blocking=False):
            return None
        try:
            return self._tick(time.time() if now is None else now)
        finally:
            self.lock.release()

    def _tick(self, now):
        config = self.store.get_daily()
        with self.store.transaction() as db:
            pending = [dict(row) for row in db.execute("SELECT * FROM daily_runs WHERE state='preparing' ORDER BY slot_at")]
        if not config['enabled'] and not pending:
            return None
        items = self.provider()
        for run in pending:
            existing = self.store.find_request(run['request_key'])
            if existing is None and now - run['slot_at'] > MISFIRE_SECONDS:
                self.record(run, 'skipped', 'Đã quá 15 phút sau khung giờ; không đăng bù.')
                continue
            recovered = self.complete(run, config, items)
            if recovered:
                return recovered
        if not config['enabled']:
            return None
        due = [slot for slot in local_slots(config, now) if config['active_from'] <= slot <= now]
        for slot in due:
            reason = 'Khung giờ đã qua; không đăng dồn.' if slot != due[-1] or now - slot > MISFIRE_SECONDS else ''
            run = self.reserve(slot, config, items, now, reason)
            if run:
                return self.complete(run, config, items)
        return None

    def run(self, stop):
        while not stop.is_set():
            try:
                self.tick()
            except Exception:
                logging.exception('Daily scheduler tick failed')
            stop.wait(2)
