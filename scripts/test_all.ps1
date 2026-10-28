# Executes full test suite across backend and frontend
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "HOTFIX Phase 1 Automated Test Suite" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Backend tests
Write-Host "`n[1/3] Running Backend Tests (pytest)..." -ForegroundColor Yellow
Set-Location "$RepoRoot/backend"
python -m pytest tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend test suite failed!"
    exit 1
}

# 2. Frontend type check
Write-Host "`n[2/3] Running Frontend TypeScript Check..." -ForegroundColor Yellow
Set-Location "$RepoRoot/frontend"
npm run typecheck
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend TypeScript validation failed!"
    exit 1
}

# 3. Frontend unit tests
Write-Host "`n[3/3] Running Frontend Unit Tests (vitest)..." -ForegroundColor Yellow
npm test
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend test suite failed!"
    exit 1
}

Set-Location $RepoRoot
Write-Host "`n=================================================" -ForegroundColor Green
Write-Host "All HOTFIX Phase 1 Automated Tests Passed!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
