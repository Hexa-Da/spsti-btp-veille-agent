@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Collecte + tri en cours...
python scripts\collect.py
if errorlevel 1 pause
pause
