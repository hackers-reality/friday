# Friday AI Assistant - PowerShell Launcher
Write-Host "[STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent..." -ForegroundColor Cyan
Write-Host "[+] Loading Neural Uplink..." -ForegroundColor Green
Write-Host "[+] Features: Voice AI, Screen Awareness, GitHub Integration, Multi-LLM, Command Chaining" -ForegroundColor Cyan
Write-Host ""

# Run Friday
Set-Location -LiteralPath $PSScriptRoot
python friday.py @args
