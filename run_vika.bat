@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo.
  echo .env created. Put LIVETENNISAPI_KEY and TELEGRAM_BOT_TOKEN into it, then run this file again.
  notepad .env
  pause
  exit /b 1
)

echo [VIKA] Checking Python...
py -3 -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.11+ and run again.
  pause
  exit /b 1
)

echo [VIKA] Installing/updating required packages...
py -3 -m pip install --disable-pip-version-check -r requirements_v47.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Dependency installation failed. Vika was NOT changed.
  pause
  exit /b 1
)

echo [VIKA] Refreshing data/model...
set "REFRESH_LOG=%TEMP%\vika_refresh_%RANDOM%.log"
py -3 scripts_v424_production_refresh.py --start 2026-01-01 > "%REFRESH_LOG%" 2>&1
if errorlevel 1 (
  findstr /C:"403: check key and history entitlement" "%REFRESH_LOG%" >nul 2>&1
  if not errorlevel 1 (
    echo.
    echo [VIKA] History API is not enabled for this key.
    echo [VIKA] This is OK for first launch: keeping the bundled historical state and continuing.
  ) else (
    echo.
    echo [ERROR] Refresh failed for a reason other than missing History access.
    type "%REFRESH_LOG%"
    echo.
    echo Previous model/state backup was preserved.
    pause
    exit /b 1
  )
) else (
  echo [VIKA] History refresh completed.
)
del "%REFRESH_LOG%" >nul 2>&1

echo.
echo [VIKA] Starting Telegram bot...
py -3 start_bot.py
pause
