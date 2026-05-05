@echo off
REM Friday Install Script (CMD)
REM Run: install.cmd

echo =============================================================
echo   FFFFF  RRRR   III  DDDD   AAA   Y   Y
echo   F      R   R   I   D   D  A   A   Y Y
echo   FFF    RRRR    I   D   D  AAAAA    Y
echo   F      R   R   I   D   D  A   A    Y
echo   F      R    R III  DDDD   A   A    Y
echo.
echo   Ultimate AI Agent - Installation Script
echo =============================================================
echo.

REM Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python not found. Please install Python 3.10+
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    echo   ✅ Python found
)

REM Check pip
echo.
echo [2/6] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ pip not found. Installing...
    python -m ensurepip --upgrade
) else (
    echo   ✅ pip found
)

REM Ask about virtual environment
echo.
echo [3/6] Setting up environment...
set /p venv="  Create virtual environment? (y/n): "
if /i "%venv%"=="y" (
    if not exist "venv" (
        python -m venv venv
        echo   ✅ Virtual environment created
    )
    call .\venv\Scripts\activate.bat
    echo   ✅ Virtual environment activated
)

REM Install dependencies
echo.
echo [4/6] Installing Python packages...
echo   This may take a few minutes...

python -m pip install langgraph>=1.0 --quiet
echo   ✅ langgraph
python -m pip install langchain>=0.2 --quiet
echo   ✅ langchain
python -m pip install langchain-google-genai>=1.0 --quiet
echo   ✅ langchain-google-genai
python -m pip install langchain-community>=0.2 --quiet
echo   ✅ langchain-community
python -m pip install mcp>=1.0 --quiet
echo   ✅ mcp
python -m pip install pywinctl>=0.0.52 --quiet
echo   ✅ pywinctl
python -m pip install pycaw>=1.5 --quiet
echo   ✅ pycaw
python -m pip install psutil>=5.9 --quiet
echo   ✅ psutil
python -m pip install browser-history>=0.5 --quiet
echo   ✅ browser-history
python -m pip install google-auth>=2.28 --quiet
echo   ✅ google-auth
python -m pip install requests>=2.31 --quiet
echo   ✅ requests
python -m pip install Pillow>=10.0 --quiet
echo   ✅ Pillow
python -m pip install pyautogui>=0.9 --quiet
echo   ✅ pyautogui
python -m pip install langgraph-checkpoint-sqlite>=3.0 --quiet
echo   ✅ langgraph-checkpoint-sqlite

REM Optional packages
echo.
echo [5/6] Installing optional packages...
python -m pip install pvporcupine --quiet 2>nul
echo   ✅ pvporcupine (optional)
python -m pip install openwakeword --quiet 2>nul
echo   ✅ openwakeword (optional)

REM Setup .env file
echo.
echo [6/6] Setting up environment...
if not exist ".env" (
    echo # Friday API Keys > .env
    echo # Keep this file secret. Never commit it to git. >> .env
    echo. >> .env
    echo # Google Gemini (Brain ^& Vision^) >> .env
    echo GOOGLE_API_KEY=your_google_api_key_here >> .env
    echo. >> .env
    echo # Groq (Fast inference^) >> .env
    echo GROQ_API_KEY=your_groq_api_key_here >> .env
    echo. >> .env
    echo # Picovoice (Voice wake word^) >> .env
    echo PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here >> .env
    echo. >> .env
    echo # Telegram Bot (optional^) >> .env
    echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here >> .env
    echo. >> .env
    echo # Discord Bot (optional^) >> .env
    echo DISCORD_BOT_TOKEN=your_discord_bot_token_here >> .env
    echo DISCORD_WEBHOOK_URL=your_discord_webhook_url_here >> .env
    echo. >> .env
    echo # Google Calendar (optional^) >> .env
    echo # Run setup_google_calendar.py to generate credentials.json >> .env
    echo. >> .env
    echo   ✅ .env file created. Please edit it with your API keys.
) else (
    echo   ✅ .env file already exists
)

REM Create memory directory
if not exist "friday_memory" (
    mkdir friday_memory
    echo   ✅ Created friday_memory\ directory
)

REM Add friday command to PATH
echo.
echo [7/7] Adding friday command to PATH...
echo @python "%~dp0friday_master.py" %* > "%PWD%\friday.cmd"
echo   ✅ Created friday.cmd wrapper

REM Add to user PATH using setx
setx PATH "%PATH%;%PWD%"
echo   ✅ Added Friday to PATH (restart terminal to use 'friday' command)

REM Verify installation
echo.
echo =============================================================
echo   Verifying installation...
echo =============================================================

set all_good=true

if exist "friday_graph.py" (echo   ✅ friday_graph.py) else (echo   ❌ friday_graph.py missing! & set all_good=false)
if exist "friday_mcp.py" (echo   ✅ friday_mcp.py) else (echo   ❌ friday_mcp.py missing! & set all_good=false)
if exist "friday_live.py" (echo   ✅ friday_live.py) else (echo   ❌ friday_live.py missing! & set all_good=false)
if exist "screen_watcher.py" (echo   ✅ screen_watcher.py) else (echo   ❌ screen_watcher.py missing! & set all_good=false)
if exist "multi_agent.py" (echo   ✅ multi_agent.py) else (echo   ❌ multi_agent.py missing! & set all_good=false)
if exist "friday_master.py" (echo   ✅ friday_master.py) else (echo   ❌ friday_master.py missing! & set all_good=false)

echo.
echo =============================================================
if "%all_good%"=="true" (
    echo   ✅ Installation complete!
    echo.
    echo   Next steps:
    echo     1. Edit .env with your API keys
    echo     2. Run: friday status
    echo     3. Start Friday: friday multi-agent
) else (
    echo   ⚠️  Some files are missing. Please check the errors above.
)
echo =============================================================
echo.

REM Ask to run Friday
set /p run_now="  Run Friday now? (y/n): "
if /i "%run_now%"=="y" (
    echo.
    echo   Starting Friday...
    python friday_master.py status
    echo.
    set /p start_friday="  Start Friday multi-agent? (y/n): "
    if /i "%start_friday%"=="y" (
        python friday_master.py multi-agent
    )
)

echo.
pause
