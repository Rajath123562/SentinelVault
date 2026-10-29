@echo off
echo ============================================================
echo Starting SentinelVault / HOTFIX Backend Gateway (FastAPI)
echo ============================================================
cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend
python -m uvicorn app.main:app --port 8000 --reload

