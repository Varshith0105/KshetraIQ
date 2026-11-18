@echo off
setlocal
title KshetraIQ Application Launcher

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI\"
set "MODE=dev"
if /i "%~1"=="prod" set "MODE=prod"
if /i "%~1"=="production" set "MODE=prod"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\start_servers.ps1" -Mode %MODE%
if errorlevel 1 (
  echo.
  echo KshetraIQ could not start. Review the error and log paths shown above.
)

echo.
pause
