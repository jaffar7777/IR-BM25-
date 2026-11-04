@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python build_index.py
if errorlevel 1 goto fail
echo Setup finished. Use run.bat to search.
pause
exit /b 0
:fail
echo Setup failed. Read the error above before retrying.
pause
exit /b 1
