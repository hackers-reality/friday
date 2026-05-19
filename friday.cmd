@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "FRIDAY_PY=python"
if exist ".venv\Scripts\python.exe" set "FRIDAY_PY=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "FRIDAY_PY=venv\Scripts\python.exe"
echo [STARK INDUSTRIES] F.R.I.D.A.Y. Sovereign Agent
echo.
%FRIDAY_PY% friday.py %*
exit /b %ERRORLEVEL%
