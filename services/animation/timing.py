"""Preserve recognizer timestamps; never distribute words over the clip duration."""
import json
import math
import subprocess
from pathlib import Path

from .settings import speech_python


def group_words(words, duration):
    if not isinstance(words, list) or not words or type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Không tìm thấy lời thoại có mốc thời gian trong video.')
    groups, current = [], []
    previous_end = 0.0
    for raw in words:
        if not isinstance(raw, dict) or not isinstance(raw.get('text'), str):
            raise ValueError('Từ nhận diện không hợp lệ.')
        text = raw['text'].strip()
        start, end = raw.get('start'), raw.get('end')
        if (not text or type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end)
                or start < previous_end - 0.02 or start < 0 or end <= start or end > duration + 0.02):
            raise ValueError('Mốc thời gian lời thoại không hợp lệ. Hãy nhận diện lại.')
        if current and (len(current) >= 9 or start-current[-1]['end'] >= 0.55 or current[-1]['text'].endswith(('.', '!', '?', '…'))):
            groups.append(current); current = []
        current.append({'text': text, 'start': start, 'end': min(end, duration)})
        previous_end = end
    if current:
        groups.append(current)
    return [{'id': i, 'start': group[0]['start'], 'end': group[-1]['end'],
             'text': ' '.join(w['text'] for w in group), 'words': group} for i, group in enumerate(groups)]


def recognize(path, model):
    worker = Path(__file__).with_name('speech_worker.py')
    try:
        result = subprocess.run([speech_python(), str(worker), str(path), model], capture_output=True,
                                text=True, encoding='utf-8', timeout=3600, shell=False)
        if result.returncode:
            raise RuntimeError('Nhận diện lời thoại thất bại. Kiểm tra môi trường .venv-speech và model đã tải.')
        value = json.loads(result.stdout)
        group_words(value['words'], value['duration'])
        return value['words'], value['duration']
    except subprocess.TimeoutExpired:
        raise RuntimeError('Nhận diện lời thoại quá 60 phút. Chọn model nhỏ hơn hoặc video ngắn hơn.') from None
    except (OSError, KeyError, json.JSONDecodeError):
        raise RuntimeError('Chưa sẵn sàng nhận diện lời thoại. Chạy tools/setup-animation.ps1 trước.') from None
