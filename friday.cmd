@echo off
cd /d "%~dp0"
set PYTHONUTF8=1

:: Find python.exe (standard python with console)
set "FRIDAY_PY=python.exe"
if exist ".venv\Scripts\python.exe" set "FRIDAY_PY=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "FRIDAY_PY=venv\Scripts\python.exe"

echo [STARK INDUSTRIES] F.R.I.D.A.Y. Sovereign Agent - Booting...
echo [STARK INDUSTRIES] Starting server and live engine in this window...

:: Run python directly so all logs print to this command prompt window
"%FRIDAY_PY%" friday.py

:: If python exits, keep window open if started by double-clicking
echo [STARK INDUSTRIES] Friday has exited.
pause
