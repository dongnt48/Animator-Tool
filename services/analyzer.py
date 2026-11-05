import random

PASTEL_COLORS = [
  "#FFF3B0", # soft butter yellow
  "#FFE5D9", # soft peach
  "#D8E2DC", # soft sage
  "#E2ECE9", # soft mint
  "#FDE2E4", # pastel blush
  "#FFCAD4", # soft pink
  "#E8D7F1", # soft lavender
]

PILL_COLORS = [
  "#E07A5F", # terracotta
  "#3D405B", # deep slate
  "#2A9D8F", # emerald teal
  "#F4A261", # warm amber
  "#E76F51", # burnt orange
  "#E63946", # deep crimson
  "#6B705C", # olive slate
]

def analyze_and_build_scenes(segments, total_duration_sec, fps=30):
    total_frames = int(total_duration_sec * fps)
    scenes = []

    # Filter out empty segments or join them
    valid_segs = [s for s in segments if s.get("text")]
    if not valid_segs:
        # Fallback if audio was mostly instrumental
        valid_segs = [{
            "start": 0.0,
            "end": total_duration_sec,
            "text": "Lắng nghe giai điệu cuộc sống và cảm nhận sự bình yên"
        }]

    for idx, seg in enumerate(valid_segs):
        start_frame = int(seg["start"] * fps)
        end_frame = int(seg["end"] * fps)
        if idx == len(valid_segs) - 1:
            end_frame = max(end_frame, total_frames)

        text = seg["text"].strip()
        words = text.split()
        if not words:
            words = ["Lắng", "nghe"]

        # Word timing interpolation
        seg_dur_frames = max(1, end_frame - start_frame)
        word_dur = seg_dur_frames / len(words)
        lead_words = []
        for w_i, w in enumerate(words):
            w_start = start_frame + int(w_i * word_dur)
            w_end = start_frame + int((w_i + 1) * word_dur)
            lead_words.append({
                "text": w,
                "start": w_start,
                "end": w_end
            })

        # Detect Mood & Key concepts
        lower_txt = text.lower()
        mood = "reflecting"
        badge = "🌿 LỜI NHẮN NHỦ"
        key_icon = "✨"
        tag = "Ý nghĩa cuộc sống"

        if any(k in lower_txt for k in ["tin nhắn", "rep", "chờ", "im lặng"]):
            mood = "sad"
            badge = "📱 CHUYỆN TIN NHẮN"
            key_icon = "💬"
            tag = "Lắng đọng"
        elif any(k in lower_txt for k in ["dằn vặt", "nội tâm", "không yên", "tò mò"]):
            mood = "sad"
            badge = "💭 TÂM SỰ NỘI TÂM"
            key_icon = "💭"
            tag = "Suy tư"
        elif any(k in lower_txt for k in ["nhân quả", "quy luật", "gieo", "gặt"]):
            mood = "reflecting"
            badge = "⚖️ QUY LUẬT CUỘC SỐNG"
            key_icon = "⚖️"
            tag = "Gieo gì gặt nấy"
        elif any(k in lower_txt for k in ["chung thủy", "tình duyên", "yêu", "thương", "kết hôn", "hôn"]):
            mood = "loyal"
            badge = "❤️ TÌNH YÊU CHÂN THÀNH"
            key_icon = "❤️"
            tag = "Trọn vẹn một lòng"
        elif any(k in lower_txt for k in ["buồn", "từ bỏ", "chán", "mất", "khóc", "xa", "kết thúc"]):
            mood = "sad"
            badge = "💔 LẮNG ĐỌNG CẢM XÚC"
            key_icon = "💧"
            tag = "Đừng nản lòng"
        elif any(k in lower_txt for k in ["lương tâm", "sạch sẽ", "bình yên", "thanh thản"]):
            mood = "peace"
            badge = "✨ TÂM HỒN TRONG SẠCH"
            key_icon = "✨"
            tag = "Bình an trong tâm"
        elif any(k in lower_txt for k in ["bội bạc", "hối hận", "sai lầm", "phản bội"]):
            mood = "regret"
            badge = "⚡ BÀI HỌC CUỘC ĐỜI"
            key_icon = "⚡"
            tag = "Nhân quả báo ứng"
        elif any(k in lower_txt for k in ["tử tế", "cố gắng", "tự hào", "vươn lên", "trải nghiệm"]):
            mood = "proud"
            badge = "🌟 SỐNG TỬ TẾ"
            key_icon = "🌟"
            tag = "Trọn vẹn một đời"

        # Select punchy Key Phrase (prefer meaningful content words)
        stop_words = {"và", "là", "của", "cho", "với", "trong", "ở", "từ", "rằng", "thì", "mà", "nhưng", "đã", "đang", "sẽ", "được", "bị", "họ", "mình", "bạn", "này", "đó", "thế", "nào", "gì", "chỉ", "lại", "cũng"}
        content_words = [w for w in words if w.lower() not in stop_words]
        if len(content_words) >= 2:
            key_txt = " ".join(content_words[-2:]).upper()
        elif len(content_words) == 1:
            key_txt = content_words[0].upper()
        elif len(words) >= 2:
            key_txt = " ".join(words[-2:]).upper()
        else:
            key_txt = words[0].upper()

        pill_color = PILL_COLORS[idx % len(PILL_COLORS)]
        note_color = PASTEL_COLORS[idx % len(PASTEL_COLORS)]

        # Keyphrase start ~65% into the segment
        key_start = start_frame + int(seg_dur_frames * 0.65)

        note_title = f"{key_icon} {key_txt}"

        # Sticky note body: compact 2 short lines (max 6-8 words total)
        if len(words) <= 4:
            note_body = text
        else:
            mid = min(4, len(words) // 2)
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:min(len(words), mid + 4)])
            note_body = f"{line1}\n{line2}"

        scenes.append({
            "startFrame": start_frame,
            "endFrame": end_frame,
            "badge": badge,
            "leadWords": lead_words,
            "keyPhrase": {
                "text": key_txt,
                "start": key_start,
                "end": end_frame,
                "pillBg": pill_color,
                "textColor": "#FFFFFF",
                "icon": key_icon
            },
            "note": {
                "title": note_title,
                "body": note_body,
                "color": note_color,
                "tag": tag,
                "rotation": round(random.uniform(-3.5, 3.5), 1)
            },
            "characterState": mood
        })

    return {
        "durationInFrames": total_frames,
        "fps": fps,
        "scenes": scenes
    }
