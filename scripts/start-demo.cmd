@echo off
setlocal

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\services\backend"
set "DASHBOARD=%ROOT%\apps\dashboard"
set "NODE_DIR=C:\Program Files\nodejs"

echo NEXUS-RESOLVE local judge demo launcher
echo Root: %ROOT%
echo.

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo Backend virtual environment is missing. Run scripts\setup-all.cmd first.
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  exit /b 1
)

if not exist "%NODE_DIR%\npm.cmd" (
  echo npm was not found at "%NODE_DIR%\npm.cmd".
  exit /b 1
)

call :ensure_backend
call :ensure_dashboard
call :ensure_deep_dive

echo.
echo Waiting for health checks...
timeout /t 4 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest 'http://127.0.0.1:8000/api/health' -TimeoutSec 3; Write-Host ('Backend health: ' + $r.StatusCode) } catch { Write-Host 'Backend health: not reachable yet' }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest 'http://127.0.0.1:5173' -TimeoutSec 3; Write-Host ('Dashboard: ' + $r.StatusCode) } catch { Write-Host 'Dashboard: not reachable yet' }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest 'http://127.0.0.1:5174/apps/deep-dive/' -TimeoutSec 3; Write-Host ('Deep dive: ' + $r.StatusCode) } catch { Write-Host 'Deep dive: not reachable yet' }"

echo.
echo Open these URLs:
echo   Dashboard:  http://localhost:5173/#/incident/disk-space
echo   Deep dive:  http://localhost:5174/apps/deep-dive/#both
echo   Backend:    http://localhost:8000/api/health
echo.
echo Use the dashboard Live mode only when OPENAI_API_KEY is configured in .env.
exit /b 0

:port_in_use
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
exit /b %errorlevel%

:ensure_backend
call :port_in_use 8000
if "%errorlevel%"=="0" (
  echo Port 8000 already has a listener. Reusing existing backend.
  exit /b 0
)
echo Starting backend on 8000...
start "NEXUS backend" /D "%BACKEND%" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
exit /b 0

:ensure_dashboard
call :port_in_use 5173
if "%errorlevel%"=="0" (
  echo Port 5173 already has a listener. Reusing existing dashboard.
  exit /b 0
)
echo Starting dashboard on 5173...
start "NEXUS dashboard" /D "%DASHBOARD%" cmd /k "set "PATH=%NODE_DIR%;%PATH%" && call "%NODE_DIR%\npm.cmd" run dev -- --host localhost --port 5173"
exit /b 0

:ensure_deep_dive
call :port_in_use 5174
if "%errorlevel%"=="0" (
  echo Port 5174 already has a listener. Reusing existing deep-dive server.
  exit /b 0
)
echo Starting deep-dive page on 5174...
start "NEXUS deep dive" /D "%ROOT%" cmd /k "python -m http.server 5174 --bind 127.0.0.1"
exit /b 0
