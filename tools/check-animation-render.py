"""Render a six-second deterministic fixture; no model or provider requests."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import imageio_ffmpeg
from services.animation.planner import build_scenes, validate_storyboard
from services.animation.timing import group_words


def main():
    engine = ROOT/'remotion'
    public = engine/'public'; public.mkdir(exist_ok=True)
    target = ROOT/'data/animation/check.mp4'; target.parent.mkdir(parents=True, exist_ok=True)
    audio = public/'animation_check.wav'
    props_file = engine/'props_animation_check.json'
    words = [{'text': 'Hãy', 'start': 1.2, 'end': 1.5}, {'text': 'bước', 'start': 1.6, 'end': 1.9},
             {'text': 'tiếp.', 'start': 2, 'end': 2.4}, {'text': 'Bình', 'start': 4, 'end': 4.2},
             {'text': 'yên.', 'start': 4.3, 'end': 4.7}]
    segments = group_words(words, 6)
    plan = {'scenes': [
        {'segment_id': 0, 'mood': 'proud', 'action': 'walk', 'visual': 'journey', 'cue_word': 1, 'badge': 'BƯỚC TIẾP',
         'key_phrase': 'BƯỚC TIẾP', 'note': 'Vững vàng bước tiếp', 'icon': '🌿'},
        {'segment_id': 1, 'mood': 'peace', 'action': 'breathe', 'visual': 'peace', 'cue_word': 0, 'badge': 'BÌNH YÊN',
         'key_phrase': 'BÌNH YÊN', 'note': 'Bình yên trong tâm', 'icon': '✨'}]}
    data = build_scenes(validate_storyboard(plan, segments), segments, 6)
    data.update(audioSrc=audio.name, totalDurationInFrames=data.pop('durationInFrames'),
                width=1080, height=1920, style='cozy', character='stickman')
    try:
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'lavfi', '-i',
                        'anullsrc=r=44100:cl=mono', '-t', '6', str(audio)], check=True, capture_output=True)
        props_file.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        import os
        subprocess.run(['npx.cmd' if os.name == 'nt' else 'npx', 'remotion', 'render', 'src/index.ts',
                        'CozyStorytellingVideo', str(target), '--props='+props_file.name, '--scale=0.5',
                        '--concurrency=2', '--overwrite'], cwd=engine, check=True, timeout=240)
        print(f'Fixture rendered: {target}')
    finally:
        audio.unlink(missing_ok=True)
        props_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
