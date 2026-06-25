@echo off
setlocal

set "ROOT=%~dp0.."
set "NODE_DIR=C:\Program Files\nodejs"
set "DASHBOARD=%ROOT%\apps\dashboard"

set "PATH=%NODE_DIR%;%PATH%"
pushd "%DASHBOARD%" || exit /b 1
call "%NODE_DIR%\npm.cmd" run dev -- --host 127.0.0.1 --port 5173
popd

