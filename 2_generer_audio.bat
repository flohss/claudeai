@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" clone_voice.py
) else (
    python clone_voice.py
)
if errorlevel 1 pause
