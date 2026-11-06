"""Export all semantic scenes with deterministic cues; no AI or recognition calls."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.animation.planner import build_scenes, validate_storyboard

EXAMPLES = [
    ('parting', 'turn_away', 'sad', 'Buông tay để bước tiếp'),
    ('support', 'reach', 'loyal', 'Có người cùng ta đứng dậy'),
    ('burden', 'release', 'peace', 'Thả xuống những gánh nặng'),
    ('crossroads', 'choose', 'reflecting', 'Chọn con đường của mình'),
    ('growth', 'water', 'proud', 'Kiên trì vun đắp từng ngày'),
    ('journey', 'walk', 'proud', 'Hãy vững vàng bước tiếp'),
    ('conversation', 'reach', 'loyal', 'Lắng nghe để hiểu nhau'),
    ('reflection', 'think', 'reflecting', 'Nhìn lại và hiểu chính mình'),
    ('celebration', 'rise', 'proud', 'Đứng lên sau những khó khăn'),
    ('peace', 'breathe', 'peace', 'Tìm lại bình yên trong tâm'),
]


def main():
    engine = ROOT/'remotion'
    target = ROOT/'data/animation/story-scenes.mp4'
    target.parent.mkdir(parents=True, exist_ok=True)
    props = engine/'props_story_check.json'
    segments, shots = [], []
    for i, (visual, action, mood, text) in enumerate(EXAMPLES):
        words = text.split()
        segments.append({'id': i, 'start': i*3, 'end': i*3+3, 'text': text,
                         'words': [{'text': word, 'start': i*3+.1+j*.35, 'end': i*3+.4+j*.35} for j, word in enumerate(words)]})
        shots.append({'segment_id': i, 'visual': visual, 'action': action, 'mood': mood, 'cue_word': 1,
                      'badge': text, 'key_phrase': text, 'note': text, 'icon': '🌿'})
    data = build_scenes(validate_storyboard({'scenes': shots}, segments), segments, 30)
    data.update(totalDurationInFrames=data['durationInFrames'], width=1080, height=1920,
                audioSrc='', character='stickman', style='cozy', channelTag='KIỂM TRA CẢNH MINH HỌA')
    try:
        props.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        subprocess.run(['npx.cmd' if os.name == 'nt' else 'npx', 'remotion', 'render', 'src/index.ts',
                        'CozyStorytellingVideo', str(target), '--props='+props.name, '--scale=0.5',
                        '--concurrency=2', '--overwrite'], cwd=engine, check=True, timeout=360)
        print(f'Semantic motion fixture: {target}')
    finally:
        props.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
