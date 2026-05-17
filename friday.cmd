@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "FRIDAY_PY=python"
if exist ".venv\Scripts\python.exe" set "FRIDAY_PY=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "FRIDAY_PY=venv\Scripts\python.exe"
if "%~1"=="" goto start_friday
if /I "%~1"=="start" goto start_friday
if /I "%~1"=="live" goto start_friday
%FRIDAY_PY% -m friday.cli %*
exit /b %ERRORLEVEL%
:start_friday
echo [STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent...
echo [+] Starting dashboard, sidecar heartbeat, memory, monitor, and live voice loop...
echo.
%FRIDAY_PY% friday.py
