@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Khong tim thay Python trong .venv. Hay cai dat theo README.md.
    pause
    exit /b 1
)
echo Dang khoi dong ung dung. Cong mac dinh: 8001.
echo Xem dia chi truy cap trong dong "Uvicorn running on" ben duoi.
echo Neu cong dang duoc su dung, thu: run.bat --port 8002
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 %*
set "app_exit_code=%errorlevel%"
if not "%app_exit_code%"=="0" (
    echo.
    echo Khong khoi dong duoc ung dung. Xem thong bao loi phia tren.
    pause
)
exit /b %app_exit_code%
