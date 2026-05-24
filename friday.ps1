Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"
$LogFile = "$PSScriptRoot\stark_logs.txt"

$pythonw = "pythonw.exe"
if (Test-Path ".venv\Scripts\pythonw.exe") {
    $pythonw = ".venv\Scripts\pythonw.exe"
} elseif (Test-Path "venv\Scripts\pythonw.exe") {
    $pythonw = "venv\Scripts\pythonw.exe"
}

Write-Host "[STARK INDUSTRIES] F.R.I.D.A.Y. Booting..." -ForegroundColor Cyan
"[$([datetime]::Now)] Friday boot initiated" | Add-Content $LogFile

# Start completely hidden — no console window at all
$proc = Start-Process -FilePath $pythonw -ArgumentList "friday.py" `
    -WindowStyle Hidden -PassThru -RedirectStandardError $LogFile

Write-Host "[STARK INDUSTRIES] Process started (PID: $($proc.Id)). Opening dashboard in 3s..." -ForegroundColor Green
Start-Sleep -Seconds 3

# Open browser to dashboard
Start-Process "http://localhost:7070"
exit 0
