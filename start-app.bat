@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found in PATH.
  pause
  exit /b 1
)

echo Starting backend on http://127.0.0.1:8000 ...
start "MMW Backend" powershell -NoExit -ExecutionPolicy Bypass -File "%ROOT%scripts\start-backend.ps1"

echo Starting frontend on http://127.0.0.1:5173 ...
start "MMW Frontend" powershell -NoExit -ExecutionPolicy Bypass -File "%ROOT%scripts\start-frontend.ps1"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173

echo Backend and frontend launch commands have been started.
exit /b 0
