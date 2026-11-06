import os
import json
import urllib.request
import urllib.parse
import subprocess
import cv2
import re
import shutil
import hashlib
from pathlib import Path
import threading
import uuid

import database
from services.video_identity import source_id

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
THUMB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "thumbnails")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
DOWNLOAD_LOCK = threading.Lock()


class DownloadResults(list):
    skipped_duplicates = 0


def discard_download(result):
    for root, name in [(DOWNLOAD_DIR, result.get('video_filename')),
                       (THUMB_DIR, (result.get('thumbnail') or '').removeprefix('/static/thumbnails/'))]:
        if not isinstance(name, str) or not name or '/' in name or '\\' in name:
            continue
        root = Path(root).resolve()
        path = (root/name).resolve()
        if path.parent == root:
            path.unlink(missing_ok=True)

def _generate_thumbnail(video_path, thumb_path):
    try:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 15)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(thumb_path, frame)
        cap.release()
    except Exception as e:
        print("Thumbnail generation error:", e)

def download_single_video(url, *, exclude_video_id=None):
    with DOWNLOAD_LOCK:
        duplicate = database.find_duplicate_video(url, exclude_id=exclude_video_id)
        if duplicate:
            raise database.DuplicateVideo(duplicate)
        result = _download_single_video(url)
        path = Path(DOWNLOAD_DIR)/result['video_filename']
        try:
            with path.open('rb') as stream:
                result['source_hash'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            result['source_video_id'] = result.get('source_video_id') or source_id(url, result['video_filename'])
            duplicate = database.find_duplicate_video(url, result['video_filename'], result['source_video_id'],
                                                       result['source_hash'], exclude_id=exclude_video_id)
            if duplicate:
                raise database.DuplicateVideo(duplicate)
            return result
        except Exception:
            discard_download(result)
            raise


def _download_single_video(url):
    print(f"[Downloader] Downloading: {url}")
    vid_num = source_id(url) or 'local_' + uuid.uuid4().hex
    token = uuid.uuid4().hex

    out_filename = f"tiktok_{vid_num}_{token}.mp4"
    out_path = os.path.join(DOWNLOAD_DIR, out_filename)
    thumb_filename = f"thumb_{vid_num}_{token}.jpg"
    thumb_path = os.path.join(THUMB_DIR, thumb_filename)

    title = f"TikTok Video {vid_num}"
    duration_sec = 0

    # 1. Try TikWM API (Fast, no watermark)
    try:
        api_url = "https://www.tikwm.com/api/?url=" + urllib.parse.quote(url)
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                d = data["data"]
                play_url = d["play"]
                title = d.get("title", title)
                duration_sec = d.get("duration", 0)

                # Download video file with User-Agent stream
                v_req = urllib.request.Request(play_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(v_req, timeout=30) as v_resp, open(out_path, "wb") as f_out:
                    shutil.copyfileobj(v_resp, f_out)

                # Thumbnail
                cover_url = d.get("cover")
                if cover_url:
                    try:
                        c_req = urllib.request.Request(cover_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(c_req, timeout=10) as c_resp, open(thumb_path, "wb") as f_c:
                            shutil.copyfileobj(c_resp, f_c)
                    except Exception:
                        _generate_thumbnail(out_path, thumb_path)
                else:
                    _generate_thumbnail(out_path, thumb_path)

                return {
                    "title": title,
                    "video_filename": out_filename,
                    "thumbnail": f"/static/thumbnails/{thumb_filename}",
                    "duration_sec": duration_sec,
                    "source_video_id": source_id(url, explicit=str(d.get('id', '')))
                }
    except Exception as e:
        print("[Downloader] TikWM attempt failed:", e)

    # 2. Fallback to yt-dlp
    try:
        cmd = [
            "python", "-m", "yt_dlp",
            "-o", out_path,
            "--no-playlist",
            url
        ]
        subprocess.run(cmd, check=True)

        # Get video info via cv2
        cap = cv2.VideoCapture(out_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration_sec = count / fps if fps > 0 else 0
        cap.release()

        _generate_thumbnail(out_path, thumb_path)

        return {
            "title": title,
            "video_filename": out_filename,
            "thumbnail": f"/static/thumbnails/{thumb_filename}",
            "duration_sec": duration_sec
        }
    except Exception as e:
        print("[Downloader] yt-dlp error:", e)
        discard_download({'video_filename': out_filename, 'thumbnail': '/static/thumbnails/'+thumb_filename})
        raise e

def download_channel_videos(channel_url, limit=5):
    is_all = not limit or limit <= 0
    print(f"[Downloader] Scanning channel: {channel_url} (limit: {'all' if is_all else limit})")
    # Clean channel username
    match = re.search(r'@([a-zA-Z0-9_\.]+)', channel_url)
    if not match:
        raise ValueError("Không tìm thấy tên kênh TikTok (@username)")
    username = match.group(1)

    results = DownloadResults()

    # 1. Primary: Use yt-dlp with curl_cffi to get clean video IDs
    try:
        cmd = [
            "python", "-m", "yt_dlp",
            "--flat-playlist",
            "--print", "%(id)s"
        ]
        if not is_all:
            cmd.extend(["--playlist-end", str(limit)])
        cmd.append(f"https://www.tiktok.com/@{username}")

        out = subprocess.check_output(cmd, text=True)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        video_ids = list(dict.fromkeys(lines if is_all else lines[:limit]))
        print(f"[Downloader] Found {len(video_ids)} video IDs for @{username}:", video_ids)
        for vid_id in video_ids:
            vid_url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
            try:
                res = download_single_video(vid_url)
                results.append((vid_url, res))
            except database.DuplicateVideo:
                results.skipped_duplicates += 1
            except Exception as err:
                print(f"[Downloader] Error downloading {vid_url}:", err)
        if results or results.skipped_duplicates:
            return results
    except Exception as err:
        print("[Downloader] yt-dlp channel error:", err)

    # 2. Fallback: TikWM user posts API
    try:
        count_param = 50 if is_all else limit
        user_api = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count={count_param}"
        req = urllib.request.Request(user_api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0 and "data" in data and "videos" in data["data"]:
                videos = data["data"]["videos"] if is_all else data["data"]["videos"][:limit]
                seen = set()
                for v in videos:
                    if v['video_id'] in seen:
                        continue
                    seen.add(v['video_id'])
                    vid_url = f"https://www.tiktok.com/@{username}/video/{v['video_id']}"
                    try:
                        res = download_single_video(vid_url)
                        results.append((vid_url, res))
                    except database.DuplicateVideo:
                        results.skipped_duplicates += 1
                    except Exception as err:
                        print(f"Failed to download {vid_url}:", err)
                if results:
                    return results
    except Exception as e:
        print("[Downloader] TikWM channel API failed:", e)

    return results
