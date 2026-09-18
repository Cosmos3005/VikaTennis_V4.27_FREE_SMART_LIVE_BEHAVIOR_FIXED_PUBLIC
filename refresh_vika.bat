@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 -m pip install --disable-pip-version-check -r requirements_v47.txt
if errorlevel 1 (echo Dependency installation failed.&pause&exit /b 1)
py -3 scripts_v424_production_refresh.py
pause
