@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "web\.work-console-build" python install.py
if errorlevel 1 goto error
python serve.py --open
:error
pause
