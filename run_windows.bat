@echo off
if not exist ".venv\Scripts\python.exe" (
    echo Run build_windows.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" app.py