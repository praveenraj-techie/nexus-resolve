@echo off
setlocal

set "ROOT=%~dp0.."
set "NODE_DIR=C:\Program Files\nodejs"
set "BACKEND=%ROOT%\services\backend"
set "DASHBOARD=%ROOT%\apps\dashboard"

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo Backend virtual environment is missing. Run scripts\setup-all.cmd first.
  exit /b 1
)

if not exist "%NODE_DIR%\npm.cmd" (
  echo npm was not found at "%NODE_DIR%\npm.cmd".
  exit /b 1
)

pushd "%BACKEND%" || exit /b 1
call ".venv\Scripts\python.exe" -m pytest || exit /b %errorlevel%
popd

set "PATH=%NODE_DIR%;%PATH%"
pushd "%DASHBOARD%" || exit /b 1
call "%NODE_DIR%\npm.cmd" run lint || exit /b %errorlevel%
call "%NODE_DIR%\npm.cmd" run test || exit /b %errorlevel%
call "%NODE_DIR%\npm.cmd" run build || exit /b %errorlevel%
popd

echo NEXUS-RESOLVE checks passed.

