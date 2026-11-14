@echo off
setlocal
title KshetraIQ Comprehensive Diagnostics

set "ROOT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%backend\scripts\check_health.ps1"

echo.
pause
