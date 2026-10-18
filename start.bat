@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Notion2API Next
set "PY=python"
%PY% --version >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% -c "import sys; assert sys.version_info >= (3, 11)" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Install Python 3.11+ from https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto :failed
)
set "PY=.venv\Scripts\python.exe"
%PY% -m pip install -r requirements.txt -c constraints.txt
if errorlevel 1 goto :failed
if not exist ".env" copy /y .env.example .env >nul
if not exist "accounts.json" (
  %PY% login.py --timeout 900
  if errorlevel 1 goto :failed
)
echo Web UI: http://127.0.0.1:8000
echo Open this address in your browser. Press Ctrl+C to stop.
%PY% -m uvicorn app.server:app --host 127.0.0.1 --port 8000
pause
exit /b 0
:failed
echo [ERROR] Setup failed. See the message above; manual setup is in README.md.
pause
exit /b 1
