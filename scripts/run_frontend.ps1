# Starts HOTFIX React/Vite frontend server
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location "$RepoRoot/frontend"

Write-Host "Starting HOTFIX Frontend on http://localhost:5173..." -ForegroundColor Cyan
npm run dev
