import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {'mode': 'antigravity', 'model': '', 'speech_model': 'small'}
SPEECH_MODELS = ('tiny', 'base', 'small', 'medium', 'large-v3')


def find_cli():
    configured = os.environ.get('ANTIGRAVITY_CLI')
    if configured:
        return str(Path(configured).resolve()) if Path(configured).is_file() else None
    return shutil.which('agy') or next((str(p) for p in (
        Path(os.environ.get('LOCALAPPDATA', ''))/'agy/bin/agy.exe',
        Path.home()/'.local/bin/agy',
    ) if p.is_file()), None)


def speech_python():
    configured = os.environ.get('ANIMATION_PYTHON')
    if configured:
        return configured
    separate = ROOT/'.venv-speech'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(separate) if separate.is_file() else sys.executable


def validate_update(body):
    if not isinstance(body, dict) or not body or set(body) - set(DEFAULTS):
        raise ValueError('Cấu hình dựng video không hợp lệ.')
    result = {}
    for key, value in body.items():
        if not isinstance(value, str):
            raise ValueError('Cấu hình phải là chuỗi.')
        value = value.strip()
        if key == 'mode' and value not in ('legacy', 'antigravity'):
            raise ValueError('Chọn dựng hiện tại hoặc Antigravity.')
        if key == 'speech_model' and value not in SPEECH_MODELS:
            raise ValueError('Model nhận diện lời thoại không hợp lệ.')
        if key == 'model' and value and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', value):
            raise ValueError('Tên model Antigravity không hợp lệ.')
        result[key] = value
    return result


def load_settings(store):
    with store.transaction() as db:
        row = db.execute("SELECT value FROM metadata WHERE key='animation_settings'").fetchone()
    return {**DEFAULTS, **(json.loads(row['value']) if row else {})}


def save_settings(store, body):
    updates = validate_update(body)
    with store.transaction() as db:
        row = db.execute("SELECT value FROM metadata WHERE key='animation_settings'").fetchone()
        value = {**DEFAULTS, **(json.loads(row['value']) if row else {}), **updates}
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('animation_settings', ?)", (json.dumps(value),))
    return value
