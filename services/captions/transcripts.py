"""Cache actual dialogue; original media and output media stay inside project folders."""
import tempfile
import threading
from pathlib import Path

import database
from services.transcriber import transcribe_audio_text, TranscriptionError
from .client import CaptionError

ROOT=Path(__file__).resolve().parents[2]
DOWNLOADS_DIR=ROOT/'downloads'
OUTPUTS_DIR=ROOT/'outputs'
_locks={}
_guard=threading.Lock()


def fingerprint(path):
    path=Path(path)
    stat=path.stat()
    return {'name':path.name,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}


def safe_media(root,name):
    if not isinstance(name,str) or not name or '/' in name or '\\' in name or Path(name).suffix.lower()!='.mp4':
        return None
    root=Path(root).resolve()
    path=(root/name).resolve()
    return path if path.parent==root and path.is_file() else None


def save_recognized_transcript(video_id,text,path):
    return database.update_video_transcript(video_id,text,fingerprint(path))


def dialogue_for_video(video_id):
    with _guard:
        lock=_locks.setdefault(video_id,threading.Lock())
    with lock:
        video=database.get_video(video_id)
        if not video:
            raise CaptionError('Video đã bị xóa.')
        path=safe_media(DOWNLOADS_DIR,video.get('video_filename')) or safe_media(OUTPUTS_DIR,video.get('output_filename'))
        cached=video.get('transcript','')
        cached=cached.strip() if isinstance(cached,str) else ''
        if path is None:
            if cached:
                return cached
            raise CaptionError('Chưa có lời thoại và không tìm thấy file video để nhận diện.')
        try:
            before=fingerprint(path)
            if cached and video.get('transcript_fingerprint')==before:
                return cached
            with tempfile.TemporaryDirectory(prefix='animator-dialogue-') as directory:
                text,_=transcribe_audio_text(str(path),directory,strict=True)
            if before!=fingerprint(path):
                raise CaptionError('Video thay đổi trong lúc nhận diện. Hãy thử lại.')
            if not text.strip():
                raise CaptionError('Không có lời thoại rõ để viết caption.')
            database.update_video_transcript(video_id,text,before)
            return text.strip()
        except (TranscriptionError,OSError):
            raise CaptionError('Không nhận diện được lời thoại. Kiểm tra video, âm thanh và mạng rồi thử lại.') from None
