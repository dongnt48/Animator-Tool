@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
echo.
echo Cai dat xong. Mo run.bat de khoi dong Studio.
pause
exit /b 0
:failed
echo.
echo Cai dat that bai. Kiem tra thong bao loi o tren va thu lai.
pause
exit /b 1
