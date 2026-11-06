@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Ouverture de l'interface de selection...
python scripts\serve.py
if errorlevel 1 pause
