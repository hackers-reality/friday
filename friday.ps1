# Friday AI Assistant - PowerShell Launcher
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$python = "python"
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    $python = "venv\Scripts\python.exe"
}

if ($args.Count -eq 0 -or $args[0] -ieq "start" -or $args[0] -ieq "live") {
    Write-Host "[STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent..." -ForegroundColor Cyan
    Write-Host "[+] Starting dashboard, sidecar heartbeat, memory, monitor, and live voice loop..." -ForegroundColor Green
    Write-Host ""
    & $python friday.py
    exit $LASTEXITCODE
}

& $python -m friday.cli @args
exit $LASTEXITCODE
