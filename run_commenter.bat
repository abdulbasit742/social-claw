@echo off
echo Starting Auto-Commenting Engagement Bot...
cd /d "%~dp0"
venv\Scripts\python.exe scripts\auto_commenter.py %*
pause
