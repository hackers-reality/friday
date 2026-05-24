@echo off
cd /d "%~dp0"
set PYTHONUTF8=1

:: Find pythonw.exe (windowless python - no console window)
set "FRIDAY_PY=pythonw.exe"
if exist ".venv\Scripts\pythonw.exe" set "FRIDAY_PY=.venv\Scripts\pythonw.exe"
if exist "venv\Scripts\pythonw.exe" set "FRIDAY_PY=venv\Scripts\pythonw.exe"

:: Log boot errors to file so silent crashes can be diagnosed
set "LOG_FILE=%~dp0stark_logs.txt"

echo [STARK INDUSTRIES] F.R.I.D.A.Y. Sovereign Agent - Booting...
echo [%DATE% %TIME%] Friday boot initiated >> "%LOG_FILE%"

:: Launch completely hidden - no console window, no flash
start "" /B "%FRIDAY_PY%" friday.py >> "%LOG_FILE%" 2>&1

:: Wait briefly then open browser (server needs ~2s to bind port)
timeout /t 3 /nobreak >nul
start "" "http://localhost:7070"

exit /b 0
