@echo off
setlocal
title KshetraIQ Comprehensive Diagnostics

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI\"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\check_health.ps1"

echo.
pause
