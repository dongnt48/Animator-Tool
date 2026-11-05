import os
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory

from database import get_all_videos, get_video, add_video, update_video_status, delete_video, update_video_aspect_ratio, update_video_style, update_video_character
from services import downloader
from services import renderer

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.jinja_env.auto_reload = True

from services.social.routes import social, local_request_guard
app.before_request(local_request_guard)
app.register_blueprint(social)
from services.captions.routes import captions
app.register_blueprint(captions)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Thread worker for rendering queue
render_queue_lock = threading.Lock()
is_batch_rendering = False

def process_single_render_task(video_id, aspect_ratio=None, style=None, character=None):
    renderer.render_video_pipeline(video_id, aspect_ratio=aspect_ratio, style=style, character=character)

def process_batch_render_task(aspect_ratio=None, style=None, character=None, force_all=False):
    global is_batch_rendering
    with render_queue_lock:
        if is_batch_rendering:
            return
        is_batch_rendering = True

    try:
        videos = get_all_videos()
        for v in videos:
            if force_all or v["status"] in ["new", "error", "processing"]:
                target_ratio = aspect_ratio or v.get("aspect_ratio", "9:16")
                target_style = style or v.get("style", "cozy")
                target_char = character or v.get("character", "stickman")
                renderer.render_video_pipeline(v["id"], aspect_ratio=target_ratio, style=target_style, character=target_char)
    finally:
        with render_queue_lock:
            is_batch_rendering = False

def process_download_and_render_task(url, limit=5, aspect_ratio="9:16", style="cozy", character="stickman"):
    placeholder_id = None
    try:
        # Normalize input
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            if url.startswith("@"):
                url = f"https://www.tiktok.com/{url}"
            elif "/video/" in url:
                url = f"https://www.tiktok.com/{url}"

        is_channel = ("/video/" not in url) and ("vt.tiktok.com" not in url) and ("vm.tiktok.com" not in url)

        if not is_channel:
            # Single video
            placeholder = add_video(
                title=f"Đang tải: {url[:45]}...",
                tiktok_url=url,
                video_filename="",
                thumbnail="",
                duration_sec=0,
                aspect_ratio=aspect_ratio,
                style=style,
                character=character
            )
            placeholder_id = placeholder["id"]
            update_video_status(placeholder_id, "processing", aspect_ratio=aspect_ratio, style=style, character=character, log_msg="Đang tải video từ TikTok...")

            res = downloader.download_single_video(url)

            # Update database record with downloaded info
            with render_queue_lock:
                from database import LOCK, _load_data, _save_data
                with LOCK:
                    d = _load_data()
                    for v in d:
                        if v["id"] == placeholder_id:
                            v["title"] = res["title"]
                            v["video_filename"] = res["video_filename"]
                            v["thumbnail"] = res["thumbnail"]
                            v["duration_sec"] = res["duration_sec"]
                            break
                    _save_data(d)

            # Now render immediately
            renderer.render_video_pipeline(placeholder_id, aspect_ratio=aspect_ratio, style=style, character=character)

        else:
            # Channel videos
            placeholder = add_video(
                title=f"Đang quét kênh: {url[:40]}...",
                tiktok_url=url,
                video_filename="",
                thumbnail="",
                duration_sec=0,
                aspect_ratio=aspect_ratio,
                style=style,
                character=character
            )
            placeholder_id = placeholder["id"]
            update_video_status(placeholder_id, "processing", aspect_ratio=aspect_ratio, style=style, character=character, log_msg="Đang quét video từ kênh...")

            results = downloader.download_channel_videos(url, limit=limit)
            if not results:
                raise RuntimeError("TikTok chặn quét tự động kênh. Vui lòng dán link video cụ thể (dạng /video/...)")

            delete_video(placeholder_id)
            placeholder_id = None

            added_ids = []
            for vid_url, res in results:
                v = add_video(
                    title=res["title"],
                    tiktok_url=vid_url,
                    video_filename=res["video_filename"],
                    thumbnail=res["thumbnail"],
                    duration_sec=res["duration_sec"],
                    aspect_ratio=aspect_ratio,
                    style=style,
                    character=character
                )
                added_ids.append(v["id"])

            for vid_id in added_ids:
                renderer.render_video_pipeline(vid_id, aspect_ratio=aspect_ratio, style=style, character=character)

    except Exception as e:
        print("[Download and Render Error]", e)
        if placeholder_id:
            err_msg = str(e)
            if "Unable to extract" in err_msg or "private" in err_msg or "403" in err_msg or "TikTok chặn" in err_msg:
                err_msg = "TikTok chặn quét kênh. Vui lòng dán link video cụ thể (/video/...)"
            update_video_status(placeholder_id, "error", log_msg=f"Lỗi: {err_msg[:90]}")

def process_download_task(url, limit=5, aspect_ratio="9:16", style="cozy", character="stickman"):
    placeholder_id = None
    try:
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            if url.startswith("@"):
                url = f"https://www.tiktok.com/{url}"
            elif "/video/" in url:
                url = f"https://www.tiktok.com/{url}"

        is_channel = ("/video/" not in url) and ("vt.tiktok.com" not in url) and ("vm.tiktok.com" not in url)

        if not is_channel:
            placeholder = add_video(
                title=f"Đang tải: {url[:45]}...",
                tiktok_url=url,
                video_filename="",
                thumbnail="",
                duration_sec=0,
                aspect_ratio=aspect_ratio,
                style=style,
                character=character
            )
            placeholder_id = placeholder["id"]
            update_video_status(placeholder_id, "processing", aspect_ratio=aspect_ratio, style=style, character=character, log_msg="Đang kết nối tải video TikTok...")

            res = downloader.download_single_video(url)
            with render_queue_lock:
                from database import LOCK, _load_data, _save_data
                with LOCK:
                    d = _load_data()
                    for v in d:
                        if v["id"] == placeholder_id:
                            v["title"] = res["title"]
                            v["video_filename"] = res["video_filename"]
                            v["thumbnail"] = res["thumbnail"]
                            v["duration_sec"] = res["duration_sec"]
                            v["status"] = "new"
                            v["log"] = "Tải về thành công, sẵn sàng dựng hoạt hình."
                            break
                    _save_data(d)
        else:
            placeholder = add_video(
                title=f"Đang quét kênh: {url[:40]}...",
                tiktok_url=url,
                video_filename="",
                thumbnail="",
                duration_sec=0,
                aspect_ratio=aspect_ratio,
                style=style,
                character=character
            )
            placeholder_id = placeholder["id"]
            update_video_status(placeholder_id, "processing", aspect_ratio=aspect_ratio, style=style, character=character, log_msg="Đang quét video từ kênh TikTok...")

            results = downloader.download_channel_videos(url, limit=limit)
            if not results:
                raise RuntimeError("TikTok chặn quét tự động kênh. Vui lòng dán link video cụ thể (dạng /video/...)")

            delete_video(placeholder_id)
            placeholder_id = None

            for vid_url, res in results:
                add_video(
                    title=res["title"],
                    tiktok_url=vid_url,
                    video_filename=res["video_filename"],
                    thumbnail=res["thumbnail"],
                    duration_sec=res["duration_sec"],
                    aspect_ratio=aspect_ratio,
                    style=style,
                    character=character
                )
    except Exception as e:
        print("[App Download Error]", e)
        if placeholder_id:
            err_msg = str(e)
            if "Unable to extract" in err_msg or "private" in err_msg or "403" in err_msg or "TikTok chặn" in err_msg:
                err_msg = "TikTok chặn quét kênh. Vui lòng dán link video cụ thể (/video/...)"
            update_video_status(placeholder_id, "error", log_msg=f"Lỗi: {err_msg[:90]}")


# ----------------- ROUTES -----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/videos", methods=["GET"])
def api_videos():
    videos = get_all_videos()
    from services.social.routes import get_store
    publication = get_store().publication_summary([v['id'] for v in videos])
    for video in videos:
        video['publication'] = publication.get(video['id'], {})
    return jsonify({
        "status": "success",
        "videos": videos,
        "is_batch_rendering": is_batch_rendering
    })

@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.json or {}
    url = data.get("url", "").strip()
    raw_limit = data.get("limit", 5)
    limit = 0 if str(raw_limit).lower() in ["all", "0", "-1"] else int(raw_limit)
    aspect_ratio = data.get("aspect_ratio", "9:16")
    style = data.get("style", "cozy")
    character = data.get("character", "stickman")

    if not url:
        return jsonify({"status": "error", "message": "Vui lòng nhập đường link TikTok hoặc kênh."}), 400

    # Start download in background thread
    t = threading.Thread(target=process_download_task, args=(url, limit, aspect_ratio, style, character), daemon=True)
    t.start()

    return jsonify({"status": "success", "message": "Đang bắt đầu tải video trong chế độ nền..."})

@app.route("/api/render/<video_id>", methods=["POST"])
def api_render(video_id):
    video = get_video(video_id)
    if not video:
        return jsonify({"status": "error", "message": "Không tìm thấy video."}), 404

    data = request.json or {}
    aspect_ratio = data.get("aspect_ratio") or video.get("aspect_ratio", "9:16")
    style = data.get("style") or video.get("style", "cozy")
    character = data.get("character") or video.get("character", "stickman")

    # Immediately mark as processing so UI updates on next poll instantly
    update_video_status(video_id, "processing", aspect_ratio=aspect_ratio, style=style, character=character, log_msg=f"1/4: Đang chuẩn bị dựng video ({aspect_ratio} - {style} - {character})...")

    t = threading.Thread(target=process_single_render_task, args=(video_id, aspect_ratio, style, character), daemon=True)
    t.start()

    return jsonify({"status": "success", "message": f"Bắt đầu dựng hoạt hình {aspect_ratio} ({style} - {character}) cho video #{video['stt']}"})

@app.route("/api/render-all", methods=["POST"])
def api_render_all():
    global is_batch_rendering
    if is_batch_rendering:
        return jsonify({"status": "warning", "message": "Hệ thống đang trong tiến trình dựng hàng loạt."})

    data = request.json or {}
    aspect_ratio = data.get("aspect_ratio")
    style = data.get("style")
    character = data.get("character")
    force_all = data.get("force_all", False)

    videos = get_all_videos()
    if not videos:
        return jsonify({"status": "error", "message": "Chưa có video nào trong danh sách. Vui lòng dán link và bấm 'Tải Video' trước nhé!"}), 400

    new_or_err = [v for v in videos if v["status"] in ["new", "error"]]
    if not new_or_err and not force_all:
        return jsonify({
            "status": "ask_re_render",
            "message": f"Tất cả {len(videos)} video đã hoàn thành. Bạn có muốn dựng lại toàn bộ theo chuẩn {aspect_ratio or 'mới'} không?"
        })

    for v in videos:
        if force_all or v["status"] in ["new", "error"]:
            v_ratio = aspect_ratio or v.get("aspect_ratio", "9:16")
            v_style = style or v.get("style", "cozy")
            v_char = character or v.get("character", "stickman")
            update_video_status(v["id"], "processing", aspect_ratio=v_ratio, style=v_style, character=v_char, log_msg=f"Đang chuẩn bị dựng hàng loạt ({v_ratio} - {v_style} - {v_char})...")

    t = threading.Thread(target=process_batch_render_task, args=(aspect_ratio, style, character, force_all), daemon=True)
    t.start()

    return jsonify({"status": "success", "message": "Đã bắt đầu tiến trình dựng hoạt hình hàng loạt cho tất cả video!"})

@app.route("/api/download-and-render", methods=["POST"])
def api_download_and_render():
    data = request.json or {}
    url = data.get("url", "").strip()
    raw_limit = data.get("limit", 5)
    limit = 0 if str(raw_limit).lower() in ["all", "0", "-1"] else int(raw_limit)
    aspect_ratio = data.get("aspect_ratio", "9:16")
    style = data.get("style", "cozy")
    character = data.get("character", "stickman")

    if not url:
        return jsonify({"status": "error", "message": "Vui lòng nhập đường link TikTok."}), 400

    t = threading.Thread(target=process_download_and_render_task, args=(url, limit, aspect_ratio, style, character), daemon=True)
    t.start()
    return jsonify({"status": "success", "message": "Đang bắt đầu tải và dựng hoạt hình tự động!"})

@app.route("/api/video/<video_id>/aspect-ratio", methods=["POST"])
def api_update_aspect_ratio(video_id):
    data = request.json or {}
    aspect_ratio = data.get("aspect_ratio", "9:16")
    update_video_aspect_ratio(video_id, aspect_ratio)
    return jsonify({"status": "success", "aspect_ratio": aspect_ratio})

@app.route("/api/video/<video_id>/style", methods=["POST"])
def api_update_style(video_id):
    data = request.json or {}
    style = data.get("style", "cozy")
    update_video_style(video_id, style)
    return jsonify({"status": "success", "style": style})

@app.route("/api/video/<video_id>/character", methods=["POST"])
def api_update_character(video_id):
    data = request.json or {}
    character = data.get("character", "stickman")
    update_video_character(video_id, character)
    return jsonify({"status": "success", "character": character})

@app.route("/api/video/<video_id>", methods=["DELETE"])
def api_delete_video(video_id):
    v = get_video(video_id)
    if v:
        # Delete download file
        if v.get("video_filename"):
            orig_path = os.path.join(DOWNLOADS_DIR, v["video_filename"])
            if os.path.exists(orig_path):
                try: os.remove(orig_path)
                except Exception: pass

        # Delete output file
        if v.get("output_filename"):
            out_path = os.path.join(OUTPUTS_DIR, v["output_filename"])
            if os.path.exists(out_path):
                try: os.remove(out_path)
                except Exception: pass

        # Delete thumbnail
        if v.get("thumbnail") and v["thumbnail"].startswith("/static/thumbnails/"):
            thumb_name = os.path.basename(v["thumbnail"])
            thumb_path = os.path.join(STATIC_DIR, "thumbnails", thumb_name)
            if os.path.exists(thumb_path):
                try: os.remove(thumb_path)
                except Exception: pass

        delete_video(video_id)

    return jsonify({"status": "success", "message": "Đã xóa video thành công."})

@app.route("/favicon.ico")
def favicon():
    return ("", 204)

@app.route("/video/download/<filename>")
def stream_download_video(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, conditional=True)

@app.route("/video/output/<filename>")
def stream_output_video(filename):
    return send_from_directory(OUTPUTS_DIR, filename, conditional=True)

if __name__ == "__main__":
    from database import migrate_caption_drafts
    migrate_caption_drafts()
    print("=" * 60)
    print(" 🎬 TIKTOK ANIMATOR STUDIO - LOCAL AI & REMOTION ENGINE")
    print(" 🌐 Server running at: http://localhost:5000")
    print("=" * 60)
    if os.environ.get("SOCIAL_AUTOSTART_WORKER", "1") == "1":
        from services.social.routes import start_worker
        start_worker()
    app.run(host="127.0.0.1", port=5000, debug=False)
