@echo off
cd /d "%~dp0"
set PYTHONUTF8=1

:: Canonical launch (per install.ps1): .venv preferred, then venv, then system python.
set "FRIDAY_PY=%cd%\.venv\Scripts\python.exe"
if not exist "%FRIDAY_PY%" if exist "venv\Scripts\python.exe" set "FRIDAY_PY=venv\Scripts\python.exe"
if not exist "%FRIDAY_PY%" set "FRIDAY_PY=python.exe"

if "%~1"=="" goto start_friday
if /I "%~1"=="start" goto start_friday
if /I "%~1"=="live" goto start_friday
"%FRIDAY_PY%" -m friday.cli %*
exit /b %ERRORLEVEL%

:start_friday
echo [STARK INDUSTRIES] Booting F.R.I.D.A.Y. Sovereign Agent...
echo.
"%FRIDAY_PY%" friday.py

:: If python exits, keep window open if started by double-clicking
echo [STARK INDUSTRIES] Friday has exited.
pause
