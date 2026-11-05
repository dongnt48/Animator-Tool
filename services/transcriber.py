import os
import wave
import imageio_ffmpeg
import subprocess
import speech_recognition as sr

def extract_audio(video_path, out_audio_path):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        out_audio_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def split_text_into_storytelling_phrases(text, min_words=5, max_words=9):
    words = text.split()
    if not words:
        return []

    markers = {
        'nhưng', 'mặt khác', 'một mặt', 'chỉ vì', 'bạn bắt đầu', 'muốn biết',
        'và luôn', 'thậm chí', 'nhưng hãy nhớ', 'hãy nhớ', 'trong nhịp sống',
        'chúng ta', 'giữa thói quen', 'tình cảm', 'rồi cũng sẽ', 'kết thúc vì',
        'bởi vì', 'cho nên', 'tuy nhiên', 'thực ra', 'đôi khi', 'nếu như',
        'đặc biệt', 'vậy nên', 'đừng bao giờ', 'hãy sống', 'để rồi'
    }

    split_indices = [0]
    i = 0
    while i < len(words):
        match = False
        for window in [3, 2, 1]:
            gram = ' '.join(words[i:i+window]).lower()
            if gram in markers or (words[i][0].isupper() and i > 0):
                if i - split_indices[-1] >= min_words:
                    split_indices.append(i)
                    match = True
                    break
        if not match and (i - split_indices[-1] >= max_words):
            split_indices.append(i)
        i += 1

    split_indices.append(len(words))
    split_indices = sorted(list(set(split_indices)))

    phrases = []
    for idx in range(len(split_indices) - 1):
        chunk = words[split_indices[idx]:split_indices[idx+1]]
        if chunk:
            phrases.append(' '.join(chunk))

    # Merge any trailing tiny chunks (< 4 words) into the preceding phrase
    merged = []
    for p in phrases:
        if merged and len(p.split()) < 4:
            merged[-1] += ' ' + p
        else:
            merged.append(p)

    return merged

class TranscriptionError(RuntimeError):
    pass


def transcribe_audio_text(video_path, temp_dir, *, strict=False):
    """Return real recognized dialogue, never the animation fallback sentence."""
    os.makedirs(temp_dir, exist_ok=True)
    temp_wav = os.path.join(temp_dir, "temp_voice.wav")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        subprocess.run([ffmpeg_exe,"-y","-i",video_path,"-ar","16000","-ac","1",temp_wav],
                       check=True,capture_output=True,timeout=120)
        with wave.open(temp_wav,"rb") as wf:
            duration=wf.getnframes()/wf.getframerate()
        recognizer=sr.Recognizer()
        recognizer.operation_timeout=30
        text=''
        try:
            with sr.AudioFile(temp_wav) as source:
                audio=recognizer.record(source)
                text=recognizer.recognize_google(audio,language='vi-VN')
        except Exception:
            if strict:
                raise TranscriptionError('Không nhận diện được lời thoại. Kiểm tra âm thanh và kết nối mạng rồi thử lại.') from None
        text=text.strip() if isinstance(text,str) else ''
        if strict and not text:
            raise TranscriptionError('Video không có lời thoại rõ để nhận diện.')
        return text,duration
    except (OSError,subprocess.SubprocessError,wave.Error):
        raise TranscriptionError('Không trích xuất được âm thanh từ video.') from None
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass


def transcribe_audio_segments(video_path, temp_dir, *, on_transcript=None):
    full_text,duration=transcribe_audio_text(video_path,temp_dir)
    if full_text and on_transcript is not None:
        on_transcript(full_text)

    if not full_text.strip():
        # Fallback if audio was mostly instrumental
        full_text = "Lắng nghe giai điệu cuộc sống và cảm nhận sự bình yên mỗi ngày"

    # 4. Split full text into short, rhythmic storytelling phrases (5 - 8 words per phrase)
    phrases = split_text_into_storytelling_phrases(full_text, min_words=5, max_words=9)
    if not phrases:
        phrases = [full_text]

    # 5. Distribute timestamps naturally across the video duration
    total_words = sum(len(p.split()) for p in phrases)
    segments = []
    curr_t = 0.0

    for idx, p in enumerate(phrases):
        w_count = len(p.split())
        dur = (w_count / total_words) * duration
        end_t = min(round(curr_t + dur, 2), duration)
        if idx == len(phrases) - 1:
            end_t = round(duration, 2)

        segments.append({
            "start": round(curr_t, 2),
            "end": end_t,
            "text": p
        })
        curr_t = end_t

    return segments, duration
