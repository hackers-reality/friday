@echo off

echo [STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent...

powershell -Command "Get-NetTCPConnection -LocalPort 5123 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [+] Spawning Alexa Bridge (Port 5123)...
start /b python e:\open-interpreter\alexa_webhook_server.py > NUL 2>&1

timeout /t 3 /nobreak >nul

echo [+] Loading Neural Uplink...
python e:\open-interpreter\friday_live.py %*
