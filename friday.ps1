# Friday AI Assistant - PowerShell Launcher
Write-Host "[STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent..." -ForegroundColor Cyan

# Kill any existing processes on port 5123
Get-NetTCPConnection -LocalPort 5123 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

# Start Alexa Bridge (optional)
if (Test-Path "e:\open-interpreter\alexa_webhook_server.py") {
    Write-Host "[+] Starting Alexa Bridge (Port 5123)..." -ForegroundColor Green
    Start-Process -FilePath "python" -ArgumentList "e:\open-interpreter\alexa_webhook_server.py" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# Start UI Dashboard (optional - use --ui flag)
if ($args -contains "--ui") {
    Write-Host "[+] Starting UI Dashboard..." -ForegroundColor Green
    Start-Process -FilePath "python" -ArgumentList "e:\open-interpreter\friday_ui.py" -WindowStyle Hidden
    Start-Sleep -Seconds 2
    Write-Host "[+] UI available at http://127.0.0.1:5000" -ForegroundColor Yellow
}

Write-Host "[+] Loading Neural Uplink..." -ForegroundColor Green
Write-Host "[+] Features: Voice AI, Screen Awareness, GitHub Integration, Multi-LLM, Command Chaining" -ForegroundColor Cyan
Write-Host ""

# Run Friday
python "e:\open-interpreter\friday_live.py" @args
