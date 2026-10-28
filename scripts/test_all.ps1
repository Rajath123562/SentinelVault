# Executes full test suite across backend and frontend
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "HOTFIX MVP Automated Test & Verification Suite" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Backend tests
Write-Host "`n[1/5] Running Backend Tests (pytest - 44 tests)..." -ForegroundColor Yellow
Set-Location "$RepoRoot/backend"
python -m pytest tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend test suite failed!"
    exit 1
}

# 2. Empirical Utility Benchmark
Write-Host "`n[2/5] Running DP Empirical Utility Benchmark (50 trials/eps)..." -ForegroundColor Yellow
Set-Location $RepoRoot
python scripts/run_utility_benchmark.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Utility benchmark script failed!"
    exit 1
}

# 3. Frontend type check
Write-Host "`n[3/5] Running Frontend TypeScript Check..." -ForegroundColor Yellow
Set-Location "$RepoRoot/frontend"
npm run typecheck
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend TypeScript validation failed!"
    exit 1
}

# 4. Frontend unit tests
Write-Host "`n[4/5] Running Frontend Unit Tests (vitest - 10 tests)..." -ForegroundColor Yellow
npm test
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend test suite failed!"
    exit 1
}

# 5. Frontend production build
Write-Host "`n[5/5] Running Frontend Production Build (vite build)..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend production build failed!"
    exit 1
}

Set-Location $RepoRoot
Write-Host "`n=================================================" -ForegroundColor Green
Write-Host "All HOTFIX MVP Automated Tests & Builds Passed!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
