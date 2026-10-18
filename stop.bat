@echo off
setlocal EnableExtensions
set "PORT=8000"
echo Stopping Notion2API Next (port %PORT%) ...
set "FOUND="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "FOUND=1"
  taskkill /F /PID %%P >nul 2>nul && echo   stopped PID %%P
)
if not defined FOUND echo   nothing is listening on port %PORT%.
timeout /t 2 >nul
