Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$python = "python"
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    $python = "venv\Scripts\python.exe"
}

Write-Host "[STARK INDUSTRIES] F.R.I.D.A.Y. Sovereign Agent" -ForegroundColor Cyan
Write-Host ""
& $python friday.py @args
exit $LASTEXITCODE
