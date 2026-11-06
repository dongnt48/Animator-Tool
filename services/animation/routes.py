import subprocess
import time
import database

from flask import Blueprint, jsonify, request, render_template

from .settings import find_cli, load_settings, save_settings, speech_python

animation = Blueprint('animation', __name__)
_speech_status = (None, 0, False)


def readiness():
    global _speech_status
    python = speech_python()
    if _speech_status[0] != python or time.monotonic() - _speech_status[1] > 30:
        try:
            check = subprocess.run([python, '-c', "import importlib.util; print(bool(importlib.util.find_spec('faster_whisper')))"],
                                   capture_output=True, text=True, timeout=8, shell=False)
            ready = check.returncode == 0 and check.stdout.strip() == 'True'
        except (OSError, subprocess.SubprocessError):
            ready = False
        _speech_status = (python, time.monotonic(), ready)
    return {'cli_installed': bool(find_cli()), 'speech_installed': _speech_status[2],
            'login_hint': 'Mở terminal chạy agy và đăng nhập tài khoản Google. Trạng thái này chưa kiểm tra đăng nhập/quota.'}


def store():
    from services.social.routes import get_store
    return get_store()


@animation.get('/animation')
def page():
    return render_template('admin/pages/animation.html', active_page='animation',
                           page_title='Hoạt hình AI',
                           page_description='Dựng hoạt hình theo lời thoại bằng Antigravity.')


@animation.post('/api/animation/render/<video_id>')
def render(video_id):
    from services import renderer
    import threading
    video = database.get_video(video_id)
    if not video:
        return jsonify(status='error', message='Không tìm thấy video.'), 404
    if video.get('status') == 'processing':
        return jsonify(status='error', message='Video đang xử lý. Chờ hoàn tất rồi thử lại.'), 409
    ratio = video.get('aspect_ratio') or '9:16'
    style = video.get('style') or 'cozy'
    # Existing library records can use styles from the previous external engine.
    style = {'semantic_dark': 'midnight', 'ai_storyboard': 'cozy'}.get(style, style)
    character = video.get('character') or 'stickman'
    if ratio not in renderer.ASPECT_RATIOS or style not in renderer.STYLE_LABELS or character not in renderer.CHARACTER_LABELS:
        return jsonify(status='error', message='Cấu hình video chưa được AI hỗ trợ. Chọn lại tỉ lệ, phong cách hoặc nhân vật trong thư viện.'), 400
    ready = readiness()
    if not ready['cli_installed'] or not ready['speech_installed']:
        return jsonify(status='error', message='Chưa cài đủ Antigravity/nhận diện. Chạy tools/setup-animation.ps1 và đăng nhập agy.'), 400
    config = {**load_settings(store()), 'mode': 'antigravity'}
    database.update_video_status(video_id, 'processing', log_msg='Đang chuẩn bị dựng hoạt hình Antigravity...')
    threading.Thread(target=renderer.render_video_pipeline,
                     args=(video_id, ratio, style, character), kwargs={'animation_settings': config}, daemon=True).start()
    return jsonify(status='success', message='Đã bắt đầu dựng bằng Antigravity.')


@animation.get('/api/animation/settings')
def settings():
    return jsonify(status='success', settings=load_settings(store()), readiness=readiness())


@animation.post('/api/animation/settings')
def update():
    body = request.get_json(silent=True)
    try:
        value = save_settings(store(), body)
    except ValueError as error:
        return jsonify(status='error', message=str(error)), 400
    return jsonify(status='success', settings=value, readiness=readiness())
