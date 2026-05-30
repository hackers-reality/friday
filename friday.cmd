@echo off
cd /d "%~dp0"
set PYTHONUTF8=1

:: Prefer .venv, then venv, then system python.
set "FRIDAY_PY=python.exe"
if exist ".venv\Scripts\python.exe" (
    set "FRIDAY_PY=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "FRIDAY_PY=venv\Scripts\python.exe"
)

echo [STARK INDUSTRIES] Starting F.R.I.D.A.Y. Sovereign CLI Agent...

:: Run python directly so all logs print to this command prompt window
"%FRIDAY_PY%" friday.py

:: If python exits, keep window open if started by double-clicking
echo [STARK INDUSTRIES] Friday has exited.
pause
