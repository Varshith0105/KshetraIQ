@echo off
setlocal
title KshetraIQ Service Terminator

set "ROOT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\stop_servers.ps1"

echo.
pause
