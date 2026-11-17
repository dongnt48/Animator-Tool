#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo " 🎬 TIKTOK ANIMATOR STUDIO (LOCAL AI & REMOTION ENGINE)"
echo " Server running at http://localhost:5000"
echo "====================================================================="

if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    echo "⚠️ Chưa tìm thấy .venv. Đang dùng python3 mặc định của hệ thống..."
    PYTHON_CMD="python3"
fi

# Tự động mở trình duyệt nếu có xdg-open
if command -v xdg-open > /dev/null 2>&1; then
    (sleep 1.5 && xdg-open http://localhost:5000) &
fi

exec "$PYTHON_CMD" app.py

