@echo off
echo ============================================================
echo Starting Full SentinelVault System (Backend + Frontend)
echo ============================================================
start "SentinelVault Backend" cmd /k "%~dp0start_backend.bat"
start "SentinelVault Frontend" cmd /k "%~dp0start_frontend.bat"
echo.
echo Both servers have been launched in separate windows!
echo - Frontend Dashboard: http://localhost:5173
echo - Backend API Docs:   http://127.0.0.1:8000/docs
echo ============================================================

