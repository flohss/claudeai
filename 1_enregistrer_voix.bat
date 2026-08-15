@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" record_sample.py
) else (
    python record_sample.py
)
if errorlevel 1 pause
