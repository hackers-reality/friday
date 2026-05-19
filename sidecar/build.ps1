$ErrorActionPreference = "Stop"

Write-Host "=== FRIDAY Sidecar Build ===" -ForegroundColor Cyan

# Ensure build directory
New-Item -ItemType Directory -Path "build" -Force | Out-Null

# Tidy dependencies
go mod tidy
if ($LASTEXITCODE -ne 0) { throw "go mod tidy failed" }

# Test compile
Write-Host "`nVerifying compilation..." -ForegroundColor Yellow
go build -o build/friday-sidecar.exe .
if ($LASTEXITCODE -ne 0) { throw "Compilation failed" }
Write-Host "  Windows amd64: OK" -ForegroundColor Green

# Cross-compile all targets
$targets = @(
    @{GOOS="windows"; GOARCH="amd64"; Ext=".exe"},
    @{GOOS="windows"; GOARCH="arm64"; Ext=".exe"},
    @{GOOS="linux";   GOARCH="amd64"; Ext=""},
    @{GOOS="darwin";  GOARCH="amd64"; Ext=""},
    @{GOOS="darwin";  GOARCH="arm64"; Ext=""}
)

foreach ($t in $targets) {
    $env:GOOS = $t.GOOS
    $env:GOARCH = $t.GOARCH
    $outName = "friday-sidecar-$($t.GOOS)-$($t.GOARCH)$($t.Ext)"
    Write-Host "  Building $outName ..." -NoNewline
    go build -ldflags="-s -w" -o "build/$outName" .
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item "build/$outName").Length
        Write-Host " $([math]::Round($size/1KB)) KB" -ForegroundColor Green
    } else {
        Write-Host " FAILED" -ForegroundColor Red
    }
}

Write-Host "`n=== Build complete ===" -ForegroundColor Cyan
Get-ChildItem -Path "build" -Name
