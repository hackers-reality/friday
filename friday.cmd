@echo off
title Friday AI Assistant

echo [STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent...

REM Kill any existing processes on port 5123
powershell -Command "Get-NetTCPConnection -LocalPort 5123 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [+] Starting Alexa Bridge (Port 5123)...
if exist e:\open-interpreter\alexa_webhook_server.py (
    start /b python e:\open-interpreter\alexa_webhook_server.py > NUL 2>&1
)

REM Start UI Dashboard in background (optional)
if "%1"=="--ui" (
    echo [+] Starting UI Dashboard...
    start /b python e:\open-interpreter\friday_ui.py > NUL 2>&1
    timeout /t 2 /nobreak >nul
    echo [+] UI available at http://127.0.0.1:5000
)

echo [+] Loading Neural Uplink...
echo [+] Features: Voice AI, Screen Awareness, GitHub Integration, Multi-LLM, Command Chaining
echo.

python e:\open-interpreter\friday_live.py %*
