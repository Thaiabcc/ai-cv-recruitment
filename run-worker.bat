@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Khong tim thay .venv. Hay cai dat theo README.md.
    pause
    exit /b 1
)
echo Worker tim viec va danh gia dang chay. Nhan Ctrl+C de dung.
".venv\Scripts\python.exe" -m app.worker %*
if errorlevel 1 pause
