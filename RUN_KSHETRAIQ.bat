@echo off
setlocal
title KshetraIQ Application Launcher

set "ROOT_DIR=%~dp0"
set "MODE=dev"
if /i "%~1"=="prod" set "MODE=prod"
if /i "%~1"=="production" set "MODE=prod"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\start_servers.ps1" -Mode %MODE%

echo.
pause
