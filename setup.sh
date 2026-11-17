#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/3] Khởi tạo môi trường ảo Python ==="
if [ ! -f ".venv/bin/python" ]; then
    if command -v uv > /dev/null 2>&1 || [ -f "$HOME/.local/bin/uv" ]; then
        UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
        "$UV_BIN" venv .venv
    else
        python3 -m venv .venv || (curl -LsSf https://astral.sh/uv/install.sh | sh && "$HOME/.local/bin/uv" venv .venv)
    fi
fi

echo "=== [2/3] Cài đặt dependencies Python & Playwright ==="
if command -v uv > /dev/null 2>&1 || [ -f "$HOME/.local/bin/uv" ]; then
    UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
    "$UV_BIN" pip install --python .venv -r requirements.txt
else
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

.venv/bin/python -m playwright install chromium

echo "=== [3/3] Cài đặt dependencies cho Remotion Engine ==="
if [ -d "remotion" ]; then
    cd remotion
    npm install
    cd ..
fi

echo ""
echo "✅ Cài đặt hoàn tất! Bạn có thể chạy ứng dụng bằng: ./run.sh"
