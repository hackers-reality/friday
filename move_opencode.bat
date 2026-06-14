@echo off
echo ============================================
echo  Moving opencode.db to E: drive
echo  CLOSE OPENCODE FIRST, then run this
echo ============================================
echo.

REM Delete originals
del "C:\Users\admin\.local\share\opencode\opencode.db" 2>nul
del "C:\Users\admin\.local\share\opencode\opencode.db-shm" 2>nul
del "C:\Users\admin\.local\share\opencode\opencode.db-wal" 2>nul

REM Create symlinks
mklink "C:\Users\admin\.local\share\opencode\opencode.db" "E:\opencode_data\opencode.db"
mklink "C:\Users\admin\.local\share\opencode\opencode.db-shm" "E:\opencode_data\opencode.db-shm"
mklink "C:\Users\admin\.local\share\opencode\opencode.db-wal" "E:\opencode_data\opencode.db-wal"

echo.
echo Done! opencode.db now lives on E: drive
echo Restart opencode to verify.
pause
