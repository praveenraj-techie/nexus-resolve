@echo off
setlocal

set "ROOT=%~dp0.."
set "NODE_DIR=C:\Program Files\nodejs"
set "PYTHON=C:\Users\mittu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "BACKEND=%ROOT%\services\backend"
set "DASHBOARD=%ROOT%\apps\dashboard"

if not exist "%PYTHON%" (
  echo Python was not found at "%PYTHON%".
  exit /b 1
)

if not exist "%NODE_DIR%\npm.cmd" (
  echo npm was not found at "%NODE_DIR%\npm.cmd".
  exit /b 1
)

pushd "%BACKEND%" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  call "%PYTHON%" -m venv .venv || exit /b %errorlevel%
)
call ".venv\Scripts\python.exe" -m pip install --upgrade pip || exit /b %errorlevel%
call ".venv\Scripts\python.exe" -m pip install -e .[dev] || exit /b %errorlevel%
popd

set "PATH=%NODE_DIR%;%PATH%"
pushd "%DASHBOARD%" || exit /b 1
call "%NODE_DIR%\npm.cmd" install || exit /b %errorlevel%
popd

echo NEXUS-RESOLVE setup complete.

