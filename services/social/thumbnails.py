"""Cache real local-video thumbnails without changing the source media."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import imageio_ffmpeg
from services.captions.transcripts import safe_media


def video_thumbnail(video,kind,downloads,outputs,cache):
    if kind not in ('original','output'):
        raise FileNotFoundError()
    path=safe_media(downloads if kind=='original' else outputs,video.get('video_filename' if kind=='original' else 'output_filename'))
    if path is None:
        raise FileNotFoundError()
    stat=path.stat()
    identity=f'{path}:{stat.st_size}:{stat.st_mtime_ns}'
    cache=Path(cache); cache.mkdir(parents=True,exist_ok=True)
    destination=cache/(hashlib.sha256(identity.encode()).hexdigest()+'.jpg')
    if destination.is_file():
        return destination
    handle,temporary=tempfile.mkstemp(suffix='.jpg',dir=cache)
    os.close(handle)
    try:
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-ss','0.1','-i',str(path),
                        '-frames:v','1','-vf','scale=160:-2','-q:v','5',temporary],
                       check=True,capture_output=True,timeout=15)
        if not Path(temporary).stat().st_size:
            raise FileNotFoundError()
        os.replace(temporary,destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return destination
