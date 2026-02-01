@echo off
setlocal

chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "HOST=127.0.0.1"
set "PORT=8001"
set "MODE=%~1"
if not defined MODE set "MODE=dev"

if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo [ERROR] Missing %ROOT%.venv\Scripts\python.exe
  pause
  exit /b 1
)

if /i "%MODE%"=="dev" goto DEV
if /i "%MODE%"=="prod" goto PROD

echo Usage:
echo   start_litreview.bat        ^(default dev: two terminals: frontend 3000 + backend %PORT%^
echo   start_litreview.bat prod   ^(backend serves built frontend at http://%HOST%:%PORT%/^
echo   start_litreview.bat dev    ^(same as default^)
pause
exit /b 1

:DEV
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Missing npm.cmd. Please install Node.js and make sure npm is in PATH.
  pause
  exit /b 1
)

start "litreview-backend" cmd /k ""%ROOT%.venv\Scripts\python.exe" -m uvicorn litreview.server:create_app --factory --host %HOST% --port %PORT% --reload"
start "litreview-frontend" cmd /k "cd /d "%ROOT%frontend" && npm.cmd run dev"

echo [INFO] UI URL: http://127.0.0.1:3000/
start "" "http://127.0.0.1:3000/"
exit /b 0

:PROD
if not exist "%ROOT%frontend\dist\index.html" (
  echo [WARN] Missing %ROOT%frontend\dist\index.html
  echo [WARN] Run: cd frontend ^&^& npm run build
)

echo [INFO] UI URL: http://%HOST%:%PORT%/
start "litreview-prod-backend" cmd /k ""%ROOT%.venv\Scripts\python.exe" -m litreview.cli start --host %HOST% --port %PORT%"

timeout /t 1 /nobreak >nul
start "" "http://%HOST%:%PORT%/"
exit /b 0
