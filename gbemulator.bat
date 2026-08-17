@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.11+ from https://python.org and try again.
    pause
    exit /b 1
)

python -c "import pygame" 2>nul
if errorlevel 1 (
    echo First run: installing dependencies...
    pip install -r requirements.txt
)

python main.py %*
if errorlevel 1 pause
