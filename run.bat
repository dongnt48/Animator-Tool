@echo off
title TikTok Animator Studio - 2D Cozy Storytelling 9:16
cd /d "%~dp0"
echo =====================================================================
echo  TIKTOK ANIMATOR STUDIO (LOCAL AI ^& REMOTION ENGINE)
echo  Local Studio - Social publishing requires internet
echo =====================================================================
echo Dang khoi dong server tai http://localhost:5000 ...
echo Vui long giu cua so nay mo trong qua trinh su dung!
echo =====================================================================

start "" http://localhost:5000
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    echo Chay setup.bat de cai them chuc nang len lich dang bai.
    python app.py
)
pause
