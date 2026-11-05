"""Loopback-only social dashboard and JSON endpoints; no browser launches on GET."""
import importlib.util
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, quote

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.exceptions import HTTPException
import database
from .store import Store, PLATFORMS, Conflict
from .worker import data_dir
from .daily import validated_output, caption_of, ready_content, daily_status

social = Blueprint('social', __name__)
PROJECT_DIR = Path(__file__).resolve().parents[2]


def local_request_guard():
    hostname = urlsplit('http://' + request.host).hostname
    if hostname not in ('localhost', '127.0.0.1', '::1'):
        return jsonify(status='error', message='Studio chỉ cho phép truy cập từ localhost.'), 403
    if request.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(status='error', message='Yêu cầu phải đến từ cùng trang Studio.'), 403
        if request.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            return jsonify(status='error', message='Không nhận yêu cầu từ trang bên ngoài.'), 403
    if request.path.startswith('/api/social/') and request.method == 'POST':
        if not request.is_json:
            return jsonify(status='error', message='Cần gửi JSON.'), 415
        if not isinstance(request.get_json(silent=True), dict):
            return jsonify(status='error', message='Nội dung JSON phải là một object.'), 400


def get_store():
    override = current_app.config.get('SOCIAL_STORE')
    if override is not None:
        return override
    if 'social_store' not in current_app.extensions:
        current_app.extensions['social_store'] = Store(data_dir() / 'social.sqlite3')
    return current_app.extensions['social_store']


def output_path(video):
    return validated_output(video, current_app.config.get('SOCIAL_OUTPUTS_DIR', PROJECT_DIR / 'outputs'))


def existing_caption(video):
    return caption_of(video)


def public_batch(batch):
    result = {key: batch[key] for key in ('id', 'video_id', 'caption', 'scheduled_at', 'made_for_kids', 'created_at')}
    result['tasks'] = [{key: task[key] for key in ('id', 'platform', 'state', 'message', 'url', 'attempts', 'updated_at')}
                       for task in batch['tasks']]
    return result


@social.errorhandler(ValueError)
def invalid(error):
    return jsonify(status='error', message=str(error)), 409 if isinstance(error, Conflict) else 400


@social.errorhandler(KeyError)
def missing(error):
    return jsonify(status='error', message='Không tìm thấy lịch hoặc tác vụ.'), 404


@social.errorhandler(HTTPException)
def http_error(error):
    return jsonify(status='error', message=error.description), error.code


from .pages import register_pages
register_pages(social)


@social.get('/api/social/status')
def status():
    store = get_store()
    items = ready_content(database.get_all_videos(), current_app.config.get('SOCIAL_OUTPUTS_DIR', PROJECT_DIR / 'outputs'))
    videos = [{key:value for key,value in item.items() if key != 'media_path'} for item in items]
    seen = store.worker_seen()
    return jsonify(status='success', platforms=PLATFORMS, videos=videos, accounts=store.accounts(),
                   batches=[public_batch(batch) for batch in store.list_batches()], worker_seen=seen,
                   worker_online=(time.time() - seen < 20), playwright_installed=importlib.util.find_spec('playwright') is not None,
                   adapters_verified=False, daily=daily_status(store, items))


@social.get('/api/social/videos/<video_id>')
def video_detail(video_id):
    video=database.get_video(video_id)
    if video is None:
        return jsonify(status='error',message='Video không còn trong thư viện.'),404
    from services.captions.transcripts import safe_media
    original=safe_media(PROJECT_DIR/'downloads',video.get('video_filename'))
    output=safe_media(current_app.config.get('SOCIAL_OUTPUTS_DIR',PROJECT_DIR/'outputs'),video.get('output_filename'))
    fields=('id','stt','title','caption','status','log','created_at','duration_sec','aspect_ratio',
            'style','character','tiktok_url','transcript','caption_ai_result','caption_ai_saved_at')
    return jsonify(status='success',video={key:video.get(key) for key in fields},
                   publication=get_store().publication_summary([video_id]).get(video_id,{}),
                   media={'original':'/video/download/'+quote(original.name,safe='') if original else None,
                          'output':'/video/output/'+quote(output.name,safe='') if output else None})


@social.get('/api/social/videos/<video_id>/thumbnail/<kind>')
def thumbnail(video_id,kind):
    from .thumbnails import video_thumbnail
    video=database.get_video(video_id)
    if video is None:
        return '',404
    try:
        path=video_thumbnail(video,kind,current_app.config.get('SOCIAL_DOWNLOADS_DIR',PROJECT_DIR/'downloads'),
                             current_app.config.get('SOCIAL_OUTPUTS_DIR',PROJECT_DIR/'outputs'),
                             get_store().path.parent/'thumbnails')
        return send_file(path,mimetype='image/jpeg',conditional=True,max_age=0)
    except (OSError,subprocess.SubprocessError):
        return '',404


@social.post('/api/social/daily')
def save_daily():
    body = request.get_json()
    if body.get('enabled') is True and body.get('confirm_all_platforms') is not True:
        raise ValueError('Xác nhận cho phép tự lấy bài và đăng lên cả 5 nền tảng theo lịch hằng ngày.')
    config = get_store().save_daily(body)
    return jsonify(status='success', config=config, message='Đã lưu lịch hằng ngày. Cấu hình áp dụng từ bây giờ.')


def spawn_module(module, args, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['SOCIAL_DATA_DIR'] = str(root)
    with open(root / 'process.log', 'a', encoding='utf-8') as log:
        return subprocess.Popen([sys.executable, '-m', module, *args], cwd=str(PROJECT_DIR), env=env,
                                stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def start_worker(root=None):
    return spawn_module('services.social.worker', [], root or data_dir())


@social.post('/api/social/worker/start')
def worker_start():
    store = get_store()
    if time.time() - store.worker_seen() >= 20:
        start_worker(store.path.parent)
    return jsonify(status='success', message='Đã yêu cầu khởi động bộ đăng. Đợi trạng thái cập nhật.'), 202


@social.post('/api/social/accounts/<platform>/connect')
def connect(platform):
    if importlib.util.find_spec('playwright') is None:
        raise ValueError('Chưa cài Playwright. Chạy setup.bat trước.')
    store = get_store()
    owner = store.begin_login(platform)
    try:
        spawn_module('services.social.login', [platform, owner], store.path.parent)
    except OSError:
        store.login_failed(platform, owner, 'Không mở được tiến trình trình duyệt. Kiểm tra cài đặt.')
        raise ValueError('Không mở được trình duyệt đăng nhập.') from None
    return jsonify(status='success', message='Đăng nhập thủ công trong cửa sổ vừa mở, kiểm tra đúng tài khoản rồi bấm Lưu phiên.'), 202


@social.post('/api/social/accounts/<platform>/save')
def save(platform):
    get_store().login_command(platform, 'save_requested')
    return jsonify(status='success', message='Đang kiểm tra và lưu phiên.'), 202


@social.post('/api/social/accounts/<platform>/cancel')
def cancel_login(platform):
    get_store().login_command(platform, 'cancel_requested')
    return jsonify(status='success', message='Đã yêu cầu đóng cửa sổ đăng nhập.'), 202


@social.post('/api/social/batches')
def schedule():
    body = request.get_json()
    video_id = body.get('video_id')
    if not isinstance(video_id, str) or not video_id:
        raise ValueError('Hãy chọn video đã dựng.')
    if body.get('confirm_all_platforms') is not True:
        raise ValueError('Cần xác nhận đăng lên cả 5 nền tảng.')
    made_for_kids = body.get('made_for_kids')
    if type(made_for_kids) is not bool:
        raise ValueError('Hãy chọn video có dành cho trẻ em trên YouTube hay không.')
    raw_date = body.get('scheduled_at')
    if not isinstance(raw_date, str):
        raise ValueError('Thời gian lên lịch không hợp lệ.')
    try:
        date = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        if date.utcoffset() is None:
            raise ValueError()
        scheduled_at = date.timestamp()
    except (ValueError, OverflowError):
        raise ValueError('Thời gian cần kèm múi giờ hợp lệ.') from None
    request_key = body.get('request_key')
    if not isinstance(request_key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}', request_key):
        raise ValueError('Mã yêu cầu không hợp lệ. Tải lại trang rồi thử lại.')
    # Lost responses must be recoverable after the due time or a source rerender/deletion.
    existing = get_store().find_request(request_key)
    if existing is not None:
        if (existing['video_id'] != video_id or existing['scheduled_at'] != scheduled_at
                or existing['made_for_kids'] != made_for_kids):
            raise Conflict('Mã yêu cầu đã được dùng cho một lịch khác.')
        return jsonify(status='success', batch=public_batch(existing)), 201
    now = time.time()
    if not now - 5 <= scheduled_at <= now + 366 * 86400:
        raise ValueError('Chọn thời gian từ hiện tại đến tối đa một năm tới.')
    video = database.get_video(video_id)
    if not video:
        raise ValueError('Video không còn tồn tại.')
    if video.get('status') != 'completed':
        raise ValueError('Chỉ lên lịch cho video đã dựng xong.')
    path = output_path(video)
    try:
        batch = get_store().create_batch(video_id, str(path), existing_caption(video), scheduled_at, made_for_kids, request_key)
    except OSError:
        raise ValueError('Không đọc được video đầu ra. Hãy kiểm tra file rồi thử lại.') from None
    return jsonify(status='success', batch=public_batch(batch)), 201


@social.post('/api/social/tasks/<task_id>/retry')
def retry(task_id):
    confirmed = request.get_json().get('confirmed_not_posted') is True
    get_store().retry(task_id, confirmed_not_posted=confirmed)
    return jsonify(status='success', message='Đã đưa riêng nền tảng này vào hàng đợi.')


@social.post('/api/social/batches/<batch_id>/cancel')
def cancel_batch(batch_id):
    get_store().cancel_batch(batch_id)
    return jsonify(status='success', message='Đã hủy các nền tảng chưa chạy. Tác vụ đang xuất bản sẽ tiếp tục.')


@social.post('/api/social/tasks/<task_id>/resolve')
def resolve(task_id):
    body = request.get_json()
    if body.get('confirmed_published') is not True or not isinstance(body.get('url'), str):
        raise ValueError('Cần kiểm tra bài đã đăng và cung cấp link bài.')
    get_store().resolve(task_id, body['url'].strip())
    return jsonify(status='success', message='Đã lưu xác nhận và link bài của bạn.')
