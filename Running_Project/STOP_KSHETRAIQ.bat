@echo off
setlocal
title KshetraIQ Service Terminator

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI\"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\stop_servers.ps1"

echo.
pause
