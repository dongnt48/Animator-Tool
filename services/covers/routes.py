from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.exceptions import HTTPException
import database
from services.captions.transcripts import safe_media
from . import images

covers = Blueprint('covers', __name__)
ROOT = Path(__file__).resolve().parents[2]


@covers.before_request
def bound_upload():
    if request.method == 'POST':
        request.max_content_length = images.MAX_BYTES + 65536


def cover_root():
    from services.social.routes import get_store
    return Path(current_app.config.get('COVERS_DIR', get_store().path.parent/'covers'))


def current_video(video_id):
    video = database.get_video(video_id)
    if video is None:
        raise LookupError('Video không còn trong thư viện.')
    return video


def public_cover(video):
    cover = video.get('cover') or {}
    ready = all(images.cover_path(cover, shape, cover_root()) for shape in images.SIZES)
    return {'ready': ready, 'title': cover.get('title', images.auto_title(video)),
            'aspect_ratio': video.get('aspect_ratio') or cover.get('aspect_ratio') or '9:16',
            'timestamp': cover.get('timestamp'), 'focus': cover.get('focus', [.5, .5]),
            'mode': cover.get('mode', 'frame'), 'revision': cover.get('revision', ''),
            'images': {shape: f'/api/covers/videos/{video["id"]}/image/{shape}?v={cover.get("revision", "")}'
                       for shape in images.SIZES} if ready else {}}


@covers.get('/api/covers/videos/<video_id>')
def get(video_id):
    return jsonify(status='success', cover=public_cover(current_video(video_id)))


@covers.post('/api/covers/videos/<video_id>')
def save(video_id):
    video = current_video(video_id)
    if request.mimetype == 'multipart/form-data':
        upload = request.files.get('image')
        if upload is None:
            raise ValueError('Chọn ảnh JPEG, PNG hoặc WebP.')
        try:
            focus = [float(request.form.get('focus_x', .5)), float(request.form.get('focus_y', .5))]
        except ValueError:
            raise ValueError('Vị trí cắt ảnh không hợp lệ.') from None
        images.save_cover(video_id, upload.stream.read(images.MAX_BYTES+1), request.form.get('title', ''), cover_root(), mode='upload', focus=focus)
    else:
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError('Cần gửi cấu hình ảnh bìa hợp lệ.')
        if body.get('mode') not in (None, 'frame', 'title'):
            raise ValueError('Chọn tạo từ video hoặc chỉnh chữ của ảnh đã có.')
        title = body.get('title', images.auto_title(video))
        focus = body.get('focus', (video.get('cover') or {}).get('focus', [.5, .5]))
        if body.get('mode') == 'title':
            existing = video.get('cover') or {}
            source = images.cover_path(existing, 'source', cover_root())
            if source is None:
                raise ValueError('Chưa có ảnh gốc để sửa chữ. Chọn lại khung hoặc tải ảnh lên.')
            images.save_cover(video_id, source.read_bytes(), title, cover_root(), mode=existing['mode'],
                              timestamp=existing.get('timestamp'), duration=existing.get('duration'), focus=focus)
        else:
            path = safe_media(current_app.config.get('SOCIAL_OUTPUTS_DIR', ROOT/'outputs'), video.get('output_filename'))
            path = path or safe_media(current_app.config.get('SOCIAL_DOWNLOADS_DIR', ROOT/'downloads'), video.get('video_filename'))
            if path is None:
                raise ValueError('Không tìm thấy video để lấy ảnh bìa.')
            images.frame_cover(video_id, path, title, cover_root(), body.get('timestamp'), focus=focus)
    return jsonify(status='success', cover=public_cover(current_video(video_id)), message='Đã lưu ảnh bìa. Lịch đã tạo trước đó giữ ảnh bìa đã chốt.')


@covers.get('/api/covers/videos/<video_id>/image/<shape>')
def image(video_id, shape):
    if shape not in images.SIZES:
        raise LookupError('Không tìm thấy ảnh bìa.')
    path = images.cover_path(current_video(video_id).get('cover'), shape, cover_root())
    if path is None:
        raise LookupError('Chưa có ảnh bìa.')
    return send_file(path, mimetype='image/jpeg', conditional=True, max_age=0)


@covers.errorhandler(ValueError)
def invalid(error):
    return jsonify(status='error', message=str(error)), 400


@covers.errorhandler(LookupError)
def missing(error):
    return jsonify(status='error', message=str(error)), 404


@covers.errorhandler(HTTPException)
def http_error(error):
    return jsonify(status='error', message=error.description), error.code
