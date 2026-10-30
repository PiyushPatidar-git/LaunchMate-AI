Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Host "Python not found. Install 3.11/3.12 from python.org (tick Add to PATH)."; exit 1 }
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env - add API keys for live mode." }
Write-Host "Open http://127.0.0.1:8000 in your browser. Ctrl+C to stop."
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
