Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$python = "python.exe"
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    $python = "venv\Scripts\python.exe"
}

Write-Host "[STARK INDUSTRIES] F.R.I.D.A.Y. Booting..." -ForegroundColor Cyan
Write-Host "[STARK INDUSTRIES] Starting server and live engine in this window..." -ForegroundColor Yellow

# Run python directly so all logs print to the active PowerShell terminal
& $python friday.py

Write-Host "[STARK INDUSTRIES] Friday has exited." -ForegroundColor Red
Read-Host -Prompt "Press Enter to exit"
