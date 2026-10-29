@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting C-Inspect Static Analysis Web App...
echo ========================================================
echo URL: http://127.0.0.1:8000
echo.
start http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
