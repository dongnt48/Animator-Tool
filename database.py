import json
import os
import threading
import shutil
import uuid
import tempfile
from pathlib import Path
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "videos.json")
LOCK = threading.Lock()


class DuplicateVideo(ValueError):
    def __init__(self, video):
        self.video = video
        state = 'đã xóa' if video.get('deleted_at') else 'đã có trong thư viện'
        super().__init__(f"Video này {state} (record {video['id']}). Không tải lại để tránh trùng.")


class VideoBusy(ValueError):
    pass


def _find_duplicate(data, tiktok_url='', video_filename='', source_video_id='', source_hash='', exclude_id=None):
    from services.video_identity import identity_keys
    wanted = identity_keys(tiktok_url, video_filename, source_video_id, source_hash)
    for video in data:
        if video['id'] == exclude_id:
            continue
        if not (video.get('deleted_at') or video.get('video_filename') or video.get('status') in ('new', 'processing')):
            continue
        if wanted & identity_keys(video.get('tiktok_url', ''), video.get('video_filename', ''),
                                  video.get('source_video_id', ''), video.get('source_hash', '')):
            return video
    return None


def find_duplicate_video(tiktok_url='', video_filename='', source_video_id='', source_hash='', exclude_id=None):
    with LOCK:
        return _find_duplicate(_load_data(), tiktok_url, video_filename, source_video_id, source_hash, exclude_id)


def attach_download(video_id, result, *, render_next=False):
    """Attach a unique downloaded source while holding the same lock as inserts."""
    with LOCK:
        data = _load_data()
        video = next((v for v in data if v['id'] == video_id and not v.get('deleted_at')), None)
        if video is None:
            raise ValueError('Record tải video đã bị xóa.')
        duplicate = _find_duplicate(data, video.get('tiktok_url', ''), result['video_filename'],
                                    result.get('source_video_id', ''), result.get('source_hash', ''), video_id)
        if duplicate:
            raise DuplicateVideo(duplicate)
        for field in ('title', 'video_filename', 'thumbnail', 'duration_sec', 'source_video_id', 'source_hash'):
            if field in result:
                video[field] = result[field]
        video['status'] = 'processing' if render_next else 'new'
        video['log'] = 'Tải về thành công, sẵn sàng dựng hoạt hình.'
        _save_data(data)

def _load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or any(not isinstance(v, dict) or 'id' not in v for v in data):
            raise ValueError('Invalid video history')
        return data
    except (OSError, ValueError):
        raise RuntimeError('Không đọc được lịch sử video. Dừng thao tác để tránh mất record kiểm tra trùng.') from None

def _save_data(data):
    directory = os.path.dirname(os.path.abspath(DB_FILE))
    os.makedirs(directory, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.videos-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, DB_FILE)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)

def get_all_videos(*, include_deleted=False):
    with LOCK:
        data = _load_data()
        if not include_deleted:
            data = [v for v in data if not v.get('deleted_at')]
        for v in data:
            if "style" not in v:
                v["style"] = "cozy"
            if "character" not in v:
                v["character"] = "stickman"
        # Sort by STT ascending
        return sorted(data, key=lambda x: x.get("stt", 0))

def get_video(video_id, *, include_deleted=False):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id and (include_deleted or not v.get('deleted_at')):
                if "style" not in v:
                    v["style"] = "cozy"
                if "character" not in v:
                    v["character"] = "stickman"
                return v
        return None

def add_video(title, tiktok_url, video_filename, thumbnail="", duration_sec=0, aspect_ratio="9:16", style="cozy", character="stickman", source_video_id='', source_hash=''):
    with LOCK:
        data = _load_data()
        duplicate = _find_duplicate(data, tiktok_url, video_filename, source_video_id, source_hash)
        if duplicate:
            raise DuplicateVideo(duplicate)
        next_stt = max((v.get('stt', 0) for v in data), default=0) + 1
        video_id = f"vid_{uuid.uuid4().hex}"
        from services.video_identity import source_id
        new_item = {
            "id": video_id,
            "stt": next_stt,
            "title": title or f"Video #{next_stt}",
            "tiktok_url": tiktok_url,
            "source_video_id": source_id(tiktok_url, video_filename, source_video_id),
            "source_hash": source_hash,
            "video_filename": video_filename,
            "thumbnail": thumbnail,
            "duration_sec": round(duration_sec, 1),
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "aspect_ratio": aspect_ratio or "9:16",
            "style": style or "cozy",
            "character": character or "stickman",
            "status": "new", # new, processing, completed, error
            "output_filename": None,
            "log": "Video mới tải về, sẵn sàng dựng hoạt hình."
        }
        data.append(new_item)
        _save_data(data)
        return new_item

def update_video_aspect_ratio(video_id, aspect_ratio):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id and not v.get('deleted_at'):
                v["aspect_ratio"] = aspect_ratio
                break
        _save_data(data)

def update_video_style(video_id, style):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id and not v.get('deleted_at'):
                v["style"] = style
                break
        _save_data(data)

def update_video_character(video_id, character):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id and not v.get('deleted_at'):
                v["character"] = character
                break
        _save_data(data)

def update_video_status(video_id, status, output_filename=None, log_msg=None, aspect_ratio=None, style=None, character=None):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id and not v.get('deleted_at'):
                v["status"] = status
                if output_filename is not None:
                    v["output_filename"] = output_filename
                if log_msg is not None:
                    v["log"] = log_msg
                if aspect_ratio is not None:
                    v["aspect_ratio"] = aspect_ratio
                if style is not None:
                    v["style"] = style
                if character is not None:
                    v["character"] = character
                _save_data(data)
                return True
        return False

def delete_video(video_id, *, source_hash='', deleted_media=None, reject_processing=False):
    with LOCK:
        data = _load_data()
        for video in data:
            if video['id'] == video_id:
                if reject_processing and not video.get('deleted_at') and video.get('status') == 'processing':
                    raise VideoBusy('Video đang xử lý. Chờ hoàn tất trước khi xóa.')
                video.setdefault('deleted_at', datetime.now().isoformat(timespec='seconds'))
                video.setdefault('status_before_delete', video.get('status'))
                video['status'] = 'deleted'
                if source_hash and not video.get('source_hash'):
                    video['source_hash'] = source_hash
                if deleted_media is not None:
                    video['deleted_media'] = deleted_media
                _save_data(data)
                return True
        return False


def update_video_caption(video_id, caption, expected):
    with LOCK:
        data = _load_data()
        for video in data:
            if video['id'] == video_id and not video.get('deleted_at'):
                if video.get('caption',video.get('title','')) != expected:
                    return 'conflict'
                video['caption'] = caption
                video['caption_ai_saved_at'] = datetime.now().isoformat(timespec='seconds')
                video.pop('caption_ai',None)
                _save_data(data)
                return 'saved'
        return 'missing'


def apply_caption_results(results):
    """Apply successful AI captions only while their source caption still matches."""
    with LOCK:
        data=_load_data()
        by_id={video['id']:video for video in data if not video.get('deleted_at')}
        for result in results:
            if 'error' in result or result.get('skipped'):
                continue
            video=by_id.get(result['video_id'])
            if video is None:
                result['error']='Video đã bị xóa.'
            elif video.get('caption',video.get('title','')) != result['original']:
                result['error']='Caption đã thay đổi trong lúc AI viết. Hãy tải lại và thử lại.'
            else:
                caption=result.get('caption')
                if not isinstance(caption,str) or not caption.strip() or len(caption)>10000:
                    result['error']='Caption AI không hợp lệ.'
                    continue
                video['caption']=caption.strip()
                video['caption_ai_saved_at']=datetime.now().isoformat(timespec='seconds')
                video['caption_ai_result']={**result,'caption':video['caption']}
                video.pop('caption_ai',None)
                result['saved']=True
        _save_data(data)


def migrate_caption_drafts():
    """Apply matching legacy drafts once, retaining a local backup before conversion."""
    with LOCK:
        data=_load_data()
        pending=[video for video in data if 'caption_ai' in video and not video.get('deleted_at')]
        if not pending:
            return
        backup=Path(DB_FILE).parent/'social'/'videos-before-direct-captions.json'
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            shutil.copy2(DB_FILE,backup)
        for video in pending:
            draft=video.pop('caption_ai')
            if not isinstance(draft,dict):
                continue
            caption=draft.get('caption')
            if draft.get('original')!=video.get('caption',video.get('title','')) or not isinstance(caption,str) or not caption.strip() or len(caption)>10000 or draft.get('error'):
                continue
            video['caption']=caption.strip()
            video['caption_ai_saved_at']=datetime.now().isoformat(timespec='seconds')
            video['caption_ai_result']=draft
        _save_data(data)


def update_video_transcript(video_id, text, fingerprint):
    if not isinstance(text,str) or not text.strip():
        return False
    with LOCK:
        data=_load_data()
        for video in data:
            if video['id']==video_id and not video.get('deleted_at'):
                video['transcript']=text.strip()
                video['transcript_fingerprint']=fingerprint
                video['transcript_source']='google_speech_recognition'
                _save_data(data)
                return True
        return False


def save_video_cover(video_id, cover):
    with LOCK:
        data = _load_data()
        for video in data:
            if video['id'] == video_id and not video.get('deleted_at'):
                video['cover'] = cover
                _save_data(data)
                return True
        return False
