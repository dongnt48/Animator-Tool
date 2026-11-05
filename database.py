import json
import os
import threading
import shutil
from pathlib import Path
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "videos.json")
LOCK = threading.Lock()

def _load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_data(data):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_all_videos():
    with LOCK:
        data = _load_data()
        for v in data:
            if "style" not in v:
                v["style"] = "cozy"
            if "character" not in v:
                v["character"] = "stickman"
        # Sort by STT ascending
        return sorted(data, key=lambda x: x.get("stt", 0))

def get_video(video_id):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id:
                if "style" not in v:
                    v["style"] = "cozy"
                if "character" not in v:
                    v["character"] = "stickman"
                return v
        return None

def add_video(title, tiktok_url, video_filename, thumbnail="", duration_sec=0, aspect_ratio="9:16", style="cozy", character="stickman"):
    with LOCK:
        data = _load_data()
        next_stt = len(data) + 1
        video_id = f"vid_{int(datetime.now().timestamp() * 1000)}"
        new_item = {
            "id": video_id,
            "stt": next_stt,
            "title": title or f"Video #{next_stt}",
            "tiktok_url": tiktok_url,
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
            if v["id"] == video_id:
                v["aspect_ratio"] = aspect_ratio
                break
        _save_data(data)

def update_video_style(video_id, style):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id:
                v["style"] = style
                break
        _save_data(data)

def update_video_character(video_id, character):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id:
                v["character"] = character
                break
        _save_data(data)

def update_video_status(video_id, status, output_filename=None, log_msg=None, aspect_ratio=None, style=None, character=None):
    with LOCK:
        data = _load_data()
        for v in data:
            if v["id"] == video_id:
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
                break
        _save_data(data)

def delete_video(video_id):
    with LOCK:
        data = _load_data()
        data = [v for v in data if v["id"] != video_id]
        # Re-number STT
        for i, v in enumerate(data):
            v["stt"] = i + 1
        _save_data(data)


def update_video_caption(video_id, caption, expected):
    with LOCK:
        data = _load_data()
        for video in data:
            if video['id'] == video_id:
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
        by_id={video['id']:video for video in data}
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
        pending=[video for video in data if 'caption_ai' in video]
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
            if video['id']==video_id:
                video['transcript']=text.strip()
                video['transcript_fingerprint']=fingerprint
                video['transcript_source']='google_speech_recognition'
                _save_data(data)
                return True
        return False
