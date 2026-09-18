@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".env" copy /Y ".env.example" ".env" >nul
py -3 -m pip install --disable-pip-version-check -r requirements_v47.txt
if errorlevel 1 (echo Dependency installation failed.&pause&exit /b 1)
py -3 start_bot.py
pause
