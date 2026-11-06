import io
import math
import re
import threading
import uuid
import warnings
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

import database

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
SIZES = {'portrait': (1080, 1920), 'landscape': (1280, 720)}
_lock = threading.RLock()


def auto_title(video):
    text = re.sub(r'#\w+', '', video.get('caption') or video.get('title') or 'Câu chuyện của bạn')
    return ' '.join(text.split()[:8])[:100]


def cover_path(cover, shape, root):
    if shape not in (*SIZES, 'source') or not isinstance(cover, dict):
        return None
    name = cover.get(shape+'_filename')
    if not isinstance(name, str) or not name or '/' in name or '\\' in name or Path(name).suffix.lower() != '.jpg':
        return None
    root = Path(root).resolve()
    path = root/name
    if path.is_symlink():
        return None
    return path if path.parent == root and path.is_file() else None


def _decode(data):
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES:
        raise ValueError('Ảnh tối đa 5 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width*image.height > MAX_PIXELS:
                    raise ValueError('Chọn ảnh JPEG, PNG hoặc WebP tối đa 20 triệu điểm ảnh.')
                image = ImageOps.exif_transpose(image)
                rgba = image.convert('RGBA')
                base = Image.new('RGBA', rgba.size, '#FAF6EE'); base.alpha_composite(rgba)
                return base.convert('RGB')
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Không đọc được ảnh. Chọn JPEG, PNG hoặc WebP hợp lệ.') from None


def _font(size):
    for path in ('C:/Windows/Fonts/segoeuib.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def compose(source, title, size, focus=(.5, .5)):
    image = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS, centering=focus)
    if not title:
        return image
    width, height = size
    overlay = Image.new('RGBA', size)
    draw = ImageDraw.Draw(overlay)
    for size_px in range(int(width*.075), 24, -2):
        font = _font(size_px)
        lines, current = [], ''
        words = []
        for word in title.split():
            chunk = ''
            for letter in word:
                if chunk and draw.textlength(chunk+letter, font=font) > width*.76:
                    words.append(chunk); chunk = ''
                chunk += letter
            if chunk:
                words.append(chunk)
        for word in words:
            candidate = (current+' '+word).strip()
            if current and draw.textlength(candidate, font=font) > width*.76:
                lines.append(current); current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) <= 3 and all(draw.textlength(line, font=font) <= width*.76 for line in lines):
            break
    text = '\n'.join(lines)
    bounds = draw.multiline_textbbox((0, 0), text, font=font, align='center', spacing=12)
    text_height = bounds[3]-bounds[1]
    top = int(height*.53-text_height/2)
    draw.rounded_rectangle((int(width*.07), top-35, int(width*.93), top+text_height+40), radius=26, fill=(40, 42, 58, 225))
    draw.rounded_rectangle((int(width*.11), top-35, int(width*.89), top-25), radius=5, fill='#E07A5F')
    draw.multiline_text((width/2, top-bounds[1]), text, font=font, fill='white', anchor='ma', align='center', spacing=12)
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')


def save_cover(video_id, data, title, root, *, mode, timestamp=None, duration=None, focus=(.5, .5), persist=True):
    with _lock:
        return _save_cover(video_id, data, title, root, mode=mode, timestamp=timestamp, duration=duration, focus=focus, persist=persist)


def _save_cover(video_id, data, title, root, *, mode, timestamp=None, duration=None, focus=(.5, .5), persist=True):
    if not isinstance(title, str) or len(title) > 100 or any(ord(c) < 32 for c in title):
        raise ValueError('Tiêu đề bìa tối đa 100 ký tự, một dòng.')
    if mode not in ('frame', 'upload'):
        raise ValueError('Nguồn ảnh bìa không hợp lệ.')
    if not isinstance(focus, (list, tuple)) or len(focus) != 2 or any(
            type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 for value in focus):
        raise ValueError('Vị trí cắt ảnh cần nằm trong khoảng 0–100%.')
    source = _decode(data)
    video = database.get_video(video_id)
    if video is None:
        raise ValueError('Video đã bị xóa.')
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    revision = uuid.uuid4().hex
    cover = {'title': title.strip(), 'mode': mode, 'timestamp': timestamp, 'duration': duration, 'focus': list(focus),
             'aspect_ratio': video.get('aspect_ratio') or '9:16',
             'revision': revision, 'created_at': datetime.now().isoformat(timespec='seconds')}
    created = []
    try:
        base_name = f'cover_{video_id}_{revision}_source.jpg'
        if '/' in base_name or '\\' in base_name:
            raise ValueError('ID video không hợp lệ.')
        base = source.copy(); base.thumbnail((2560, 2560))
        base.save(root/base_name, 'JPEG', quality=90, optimize=True)
        created.append(root/base_name); cover['source_filename'] = base_name
        for shape, size in SIZES.items():
            name = f'cover_{video_id}_{revision}_{shape}.jpg'
            # IDs originate in the database; never permit path components.
            if '/' in name or '\\' in name:
                raise ValueError('ID video không hợp lệ.')
            path = root/name
            compose(source, cover['title'], size, focus).save(path, 'JPEG', quality=90, optimize=True)
            created.append(path); cover[shape+'_filename'] = name
        if not persist:
            return cover
        if not database.save_video_cover(video_id, cover):
            raise ValueError('Video đã bị xóa trong khi tạo ảnh bìa.')
        for shape in (*SIZES, 'source'):
            previous = cover_path(video.get('cover'), shape, root)
            if previous:
                try:
                    previous.unlink(missing_ok=True)
                except OSError:
                    pass
        return cover
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def frame_cover(video_id, path, title, root, timestamp=None, focus=(.5, .5), *, persist=True):
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not fps or not math.isfinite(fps) or count <= 0:
            raise ValueError('Không đọc được video để chọn ảnh bìa.')
        duration = count/fps
        if timestamp is not None and (type(timestamp) not in (int, float) or not math.isfinite(timestamp) or timestamp < 0 or timestamp >= duration):
            raise ValueError(f'Mốc ảnh bìa cần từ 0 đến dưới {duration:.2f} giây.')
        candidates = [timestamp] if timestamp is not None else [duration*.15, duration*.4, duration*.65]
        best = None
        for second in candidates:
            capture.set(cv2.CAP_PROP_POS_MSEC, second*1000)
            ok, frame = capture.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score = cv2.Laplacian(gray, cv2.CV_64F).var() - abs(float(gray.mean())-128)*.05
            if best is None or score > best[0]:
                best = (score, second, frame)
        if best is None:
            raise ValueError('Không lấy được khung hình ở mốc này.')
        ok, encoded = cv2.imencode('.jpg', best[2])
        if not ok:
            raise ValueError('Không tạo được ảnh khung hình.')
        return save_cover(video_id, encoded.tobytes(), title, root, mode='frame', timestamp=round(best[1], 3), duration=duration, focus=focus, persist=persist)
    finally:
        capture.release()


def cover_payload(cover, root, *, aspect_ratio=None):
    from services.social.store import media_hash
    payload = {key: cover.get(key) for key in ('mode', 'title', 'timestamp', 'duration', 'aspect_ratio')}
    if aspect_ratio is not None:
        payload['aspect_ratio'] = aspect_ratio
    for shape in SIZES:
        path = cover_path(cover, shape, root)
        if path is None:
            raise ValueError('Ảnh bìa đã mất. Tạo lại trước khi lên lịch.')
        payload[shape+'_path'] = str(path)
        payload[shape+'_hash'] = media_hash(path)
    return payload


def ensure_cover(video_id, path, root):
    """Best effort for old videos; explicit saved covers must remain readable."""
    with _lock:
        video = database.get_video(video_id)
        if video is None:
            return None
        if video.get('cover'):
            return cover_payload(video['cover'], root, aspect_ratio=video.get('aspect_ratio') or '9:16')
        try:
            cover = frame_cover(video_id, path, auto_title(video), root)
        except (ValueError, OSError):
            return None
        return cover_payload(cover, root)


@contextmanager
def scheduled_cover(video_id, path, root):
    """The worker reads JSON only; generate legacy covers temporarily for the snapshot."""
    video = database.get_video(video_id)
    if video is None:
        yield None
    elif video.get('cover'):
        yield cover_payload(video['cover'], root, aspect_ratio=video.get('aspect_ratio') or '9:16')
    else:
        with tempfile.TemporaryDirectory(prefix='animator-cover-') as temporary:
            try:
                cover = frame_cover(video_id, path, auto_title(video), temporary, persist=False)
                payload = cover_payload(cover, temporary)
            except (ValueError, OSError):
                payload = None
            yield payload
