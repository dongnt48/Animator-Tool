import os
import json
import subprocess
import shutil
import sys
import threading
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from services import transcriber
from services import analyzer

DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
REMOTION_DIR = os.path.join(BASE_DIR, "remotion")
LEGACY_REMOTION_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'remotion-project'))
REMOTION_PUBLIC = os.path.join(REMOTION_DIR, "public")

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(REMOTION_PUBLIC, exist_ok=True)

ASPECT_RATIOS = {
    "16:9": {"width": 1920, "height": 1080, "label": "16:9 (Ngang)"},
    "9:16": {"width": 1080, "height": 1920, "label": "9:16 (Dọc TikTok/Reels)"},
    "1:1": {"width": 1080, "height": 1080, "label": "1:1 (Vuông)"},
    "4:3": {"width": 1440, "height": 1080, "label": "4:3 (Ngang cổ điển)"},
    "4:5": {"width": 1080, "height": 1350, "label": "4:5 (Dọc Feed)"},
    "16:10": {"width": 1920, "height": 1200, "label": "16:10 (Ngang Tablet)"},
    "10:16": {"width": 1200, "height": 1920, "label": "10:16 (Dọc Tablet)"},
}

STYLE_LABELS = {
    "cozy": "2D Cozy Storytelling",
    "midnight": "Midnight Deep Philosophy",
    "scrapbook": "Scrapbook Paper Collage",
    "pixel": "Pixel Art Retro Lo-Fi",
    "brutalism": "Neo-Brutalism Productivity",
    "whiteboard": "Whiteboard Hand-Drawn Sketch",
}

CHARACTER_LABELS = {
    "stickman": "Người Que",
    "cat": "Mèo Béo Chill",
    "hoodie": "Cậu Bé Hoodie",
    "bear": "Gấu Teddy",
    "bot": "Robot AI",
    "ghost": "Bé Ma Bồng Bềnh",
}

_VIDEO_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def render_video_pipeline(video_id, aspect_ratio=None, style=None, character=None, *, animation_settings=None):
    with _LOCKS_GUARD:
        lock = _VIDEO_LOCKS.setdefault(video_id, threading.Lock())
    if not lock.acquire(blocking=False):
        return False
    try:
        return _render_video_pipeline(video_id, aspect_ratio, style, character, animation_settings=animation_settings)
    finally:
        lock.release()


def _render_video_pipeline(video_id, aspect_ratio=None, style=None, character=None, *, animation_settings=None):
    video = database.get_video(video_id)
    if not video:
        print(f"[Renderer] Video {video_id} not found.")
        return False

    if not aspect_ratio:
        aspect_ratio = video.get("aspect_ratio", "9:16")

    if not style:
        style = video.get("style", "cozy")

    if not character:
        character = video.get("character", "stickman")

    if (aspect_ratio not in ASPECT_RATIOS or style not in STYLE_LABELS or character not in CHARACTER_LABELS):
        database.update_video_status(video_id, "error", log_msg="Tỉ lệ, phong cách hoặc nhân vật không hợp lệ.")
        return False

    dim = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["9:16"])
    target_w, target_h = dim["width"], dim["height"]
    is_ai = bool(animation_settings and animation_settings.get('mode') == 'antigravity')
    # AI compatibility aliases are runtime options, not edits to the legacy library settings.
    saved_options = {} if is_ai else {'aspect_ratio': aspect_ratio, 'style': style, 'character': character}

    video_path = os.path.join(DOWNLOADS_DIR, video["video_filename"])
    if not os.path.exists(video_path):
        database.update_video_status(video_id, "error", log_msg="File video gốc không tồn tại.")
        return False

    props_path = None
    temp_dir = None
    temporary_output = None
    try:
        # Only the dedicated AI endpoint opts into Antigravity.
        config = animation_settings or {'mode': 'legacy'}
        engine_dir = REMOTION_DIR
        if config['mode'] == 'legacy' and os.path.isfile(os.path.join(LEGACY_REMOTION_DIR, 'src', 'index.ts')):
            engine_dir = LEGACY_REMOTION_DIR
        engine_public = os.path.join(engine_dir, 'public')
        os.makedirs(engine_public, exist_ok=True)
        if config['mode'] == 'antigravity':
            from services.animation.settings import find_cli
            if not find_cli():
                raise RuntimeError('Chưa có Antigravity CLI. Chạy tools/setup-animation.ps1 và đăng nhập agy.')
        # Step 1: Update status to processing
        style_title = STYLE_LABELS.get(style, style)
        char_title = CHARACTER_LABELS.get(character, character)
        claimed = database.update_video_status(
            video_id,
            "processing",
            **saved_options,
            log_msg=f"1/4: Đang trích xuất âm thanh gốc ({aspect_ratio} - {style_title} - {char_title})..."
        )
        if claimed is False:
            return False  # Soft-deleted after the renderer first loaded the record.

        audio_rel_name = f"audio_{video_id}.mp3"
        audio_public_path = os.path.join(engine_public, audio_rel_name)
        transcriber.extract_audio(video_path, audio_public_path)

        # Step 2: Transcribe segments
        database.update_video_status(video_id, "processing", **saved_options, log_msg=f"2/4: Đang nhận diện giọng nói & tách câu ({aspect_ratio})...")
        temp_dir = os.path.join(BASE_DIR, "data", f"temp_{video_id}")
        from services.captions.transcripts import save_recognized_transcript
        if config['mode'] == 'antigravity':
            from services.animation.planner import prepare_animation
            analysis = prepare_animation(video_path, config, on_progress=lambda message:
                database.update_video_status(video_id, 'processing', log_msg='2/4: '+message))
            save_recognized_transcript(video_id, analysis['transcript'], video_path)
        else:
            segments, duration_sec = transcriber.transcribe_audio_segments(
                video_path, temp_dir,
                on_transcript=lambda text: save_recognized_transcript(video_id,text,video_path)
            )
            analysis = analyzer.analyze_and_build_scenes(segments, duration_sec, fps=30)
        database.update_video_status(video_id, "processing", **saved_options, log_msg=f"3/4: Đang thiết kế đồ họa {style_title} ({char_title})...")

        # Write props json for Remotion
        props_filename = f"props_{video_id}.json"
        props_path = os.path.join(engine_dir, props_filename)

        # Channel tag from title or default
        channel_tag = "☕ 60 Ngày Kỷ Luật • Thay Đổi Bản Thân"
        if "60daykyluat" in video.get("tiktok_url", ""):
            channel_tag = "☕ 60 Ngày Kỷ Luật • Thay Đổi Bản Thân"

        props_data = {
            "scenes": analysis["scenes"],
            "timedDialogue": analysis.get('timedDialogue', False),
            "audioSrc": audio_rel_name,
            "totalDurationInFrames": analysis["durationInFrames"],
            "channelTag": channel_tag,
            "aspectRatio": aspect_ratio,
            "style": style,
            "character": character,
            "width": target_w,
            "height": target_h
        }

        with open(props_path, "w", encoding="utf-8") as pf:
            json.dump(props_data, pf, ensure_ascii=False, indent=2)

        # Step 4: Render video with Remotion Engine
        database.update_video_status(
            video_id,
            "processing",
            **saved_options,
            log_msg=f"4/4: Đang xuất video {style_title} ({char_title}) {aspect_ratio} ({target_w}x{target_h})..."
        )
        ratio_clean = aspect_ratio.replace(":", "_")
        prefix = 'antigravity_' if config['mode'] == 'antigravity' else ''
        out_filename = f"{prefix}{style}_{character}_{video_id}_{ratio_clean}.mp4"
        out_path = os.path.join(OUTPUTS_DIR, out_filename)
        temporary_output = os.path.join(OUTPUTS_DIR, f'.render-{uuid.uuid4().hex}.mp4')

        cmd = [
            "npx.cmd" if os.name == 'nt' else 'npx', "remotion", "render",
            "src/index.ts",
            "CozyStorytellingVideo",
            temporary_output,
            f"--props={props_filename}",
            f"--width={target_w}",
            f"--height={target_h}",
            "--overwrite"
        ]

        # Validated settings and an argument list preserve paths containing spaces.
        res = subprocess.run(
            cmd,
            cwd=engine_dir,
            shell=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if res.returncode != 0:
            print("[Renderer Error]", res.stderr or res.stdout)
            raise RuntimeError(f"Remotion render error: {res.stderr or res.stdout}")
        if not os.path.isfile(temporary_output):
            raise RuntimeError('Remotion không tạo được file video.')
        os.replace(temporary_output, out_path)

        # Cleanup temp props file
        if os.path.exists(props_path):
            try:
                os.remove(props_path)
            except Exception:
                pass

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        database.update_video_status(video_id, 'processing', log_msg='Đang tạo ảnh bìa tự động…', **saved_options)
        cover_ready = False
        try:
            from services.covers.images import ensure_cover
            from services.social.worker import data_dir
            cover_ready = bool(ensure_cover(video_id, out_path, data_dir()/'covers'))
        except Exception as cover_error:
            print('[Cover] Chưa tạo được ảnh bìa mặc định:', type(cover_error).__name__)
        database.update_video_status(
            video_id,
            "completed",
            output_filename=out_filename,
            **saved_options,
            log_msg=f"Đã hoàn thành dựng {'hoạt hình AI' if is_ai else 'video'} {style_title} ({char_title} - {aspect_ratio})! "
                    + ('Đã tạo ảnh bìa.' if cover_ready else 'Chưa tạo được ảnh bìa; có thể tạo lại trong chi tiết video.')
        )
        print(f"[Renderer] Successfully rendered {video_id} -> {out_filename} ({aspect_ratio})")
        return True

    except Exception as e:
        print(f"[Renderer Exception] {e}")
        database.update_video_status(video_id, "error", log_msg=f"Lỗi: {str(e)[:120]}")
        return False
    finally:
        for filename in (props_path, temporary_output):
            if filename and os.path.isfile(filename):
                try:
                    os.remove(filename)
                except OSError:
                    pass
        if temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
