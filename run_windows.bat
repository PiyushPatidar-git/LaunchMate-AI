@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.11 or 3.12 was not found. Install it from python.org and tick "Add python.exe to PATH". & pause & exit /b 1)
if not exist .venv ( echo Creating virtual environment... & python -m venv .venv || (pause & exit /b 1) )
call .venv\Scripts\activate.bat
echo Installing requirements...
python -m pip install -q -r requirements.txt || (echo Install failed. Check your internet connection. & pause & exit /b 1)
if not exist .env ( copy .env.example .env >nul & echo Created .env - add your API keys there for live mode. )
echo.
echo Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
