@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Resume agent + export Word...
python scripts\generer_rapport.py
if errorlevel 1 pause
pause
