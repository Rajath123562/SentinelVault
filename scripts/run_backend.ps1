# Starts HOTFIX FastAPI backend server
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location $RepoRoot
$env:PYTHONPATH = "backend"

Write-Host "Starting HOTFIX FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

