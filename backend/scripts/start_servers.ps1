param (
    [ValidateSet("dev", "prod")]
    [string]$Mode = "dev"
)

$ErrorActionPreference = "Stop"
$ROOT_DIR = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $ROOT_DIR ".venv\Scripts\python.exe"
$backendDir = Join-Path $ROOT_DIR "backend"
$frontendDir = Join-Path $ROOT_DIR "frontend"
$runtimeDir = Join-Path $backendDir ".tmp"
$backendOut = Join-Path $runtimeDir "backend.stdout.log"
$backendErr = Join-Path $runtimeDir "backend.stderr.log"
$frontendOut = Join-Path $runtimeDir "frontend.stdout.log"
$frontendErr = Join-Path $runtimeDir "frontend.stderr.log"

function Test-Url([string]$Url) {
    try { return (Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
    catch { return $false }
}

function Get-Listener([int]$Port) {
    @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) | Select-Object -First 1
}

function Wait-ForService([string]$Name, [string]$Url, [int]$Seconds, [string]$ErrorLog) {
    Write-Host "[INFO] Waiting for $Name..." -ForegroundColor Yellow
    for ($attempt = 1; $attempt -le $Seconds; $attempt++) {
        if (Test-Url $Url) {
            Write-Host "[OK] $Name is ready: $Url" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "[FAIL] $Name did not become healthy within $Seconds seconds." -ForegroundColor Red
    if (Test-Path $ErrorLog) {
        Write-Host "--- Recent $Name error log ---" -ForegroundColor Red
        Get-Content $ErrorLog -Tail 40 -ErrorAction SilentlyContinue
    }
    return $false
}

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "             KSHETRAIQ ONE-CLICK APPLICATION LAUNCHER" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

if (-not (Test-Path $python)) { throw "Python environment missing: $python. Run: py -3.11 -m venv .venv, then install backend requirements." }
if (-not (Get-Command node.exe -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Node.js and npm.cmd must be available on PATH." }
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) { throw "Frontend dependencies are missing. Run npm.cmd --prefix frontend install once." }
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

# Never terminate a listener we cannot positively identify as this app.
foreach ($pair in @(@{ Port = 8000; Name = "backend" }, @{ Port = 3000; Name = "frontend" })) {
    $listener = Get-Listener $pair.Port
    $healthUrl = if ($pair.Port -eq 8000) { "http://127.0.0.1:8000/health" } else { "http://127.0.0.1:3000/" }
    if ($listener -and -not (Test-Url $healthUrl)) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $owner -or $owner.CommandLine -notmatch [regex]::Escape($ROOT_DIR)) { throw "Port $($pair.Port) belongs to an unhealthy non-KshetraIQ process. It was left untouched." }
        Write-Host "[WARN] Recycling unhealthy KshetraIQ $($pair.Name) listener (PID $($listener.OwningProcess))." -ForegroundColor Yellow
        Stop-Process -Id $listener.OwningProcess -Force
        Start-Sleep -Seconds 1
        if ($pair.Name -eq "frontend" -and $Mode -eq "dev") {
            Remove-Item -Recurse -Force (Join-Path $frontendDir ".next-dev") -ErrorAction SilentlyContinue
        }
    }
}

if (-not (Test-Url "http://127.0.0.1:8000/health")) {
    Remove-Item -LiteralPath $backendOut, $backendErr -Force -ErrorAction SilentlyContinue
    Write-Host "[INFO] Starting FastAPI backend..." -ForegroundColor Cyan
    Start-Process -FilePath $python -WorkingDirectory $backendDir -WindowStyle Hidden `
        -ArgumentList @("-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000") `
        -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr | Out-Null
}

if (-not (Test-Url "http://127.0.0.1:3000/")) {
    Remove-Item -LiteralPath $frontendOut, $frontendErr -Force -ErrorAction SilentlyContinue
    if ($Mode -eq "prod" -and -not (Test-Path (Join-Path $frontendDir ".next-kshetraiq"))) {
        Write-Host "[INFO] Building Next.js production bundle..." -ForegroundColor Cyan
        $buildProc = Start-Process -FilePath "npm.cmd" -WorkingDirectory $frontendDir -ArgumentList @("run", "build") -Wait -PassThru -NoNewWindow
        if ($buildProc.ExitCode -ne 0) { throw "Frontend build failed with exit code $($buildProc.ExitCode)." }
    }
    $frontendArgs = if ($Mode -eq "prod") { @("start", "--", "-p", "3000", "-H", "127.0.0.1") } else { @("run", "dev", "--", "-p", "3000", "-H", "127.0.0.1") }
    Write-Host "[INFO] Starting Next.js frontend in $Mode mode..." -ForegroundColor Cyan
    Start-Process -FilePath "npm.cmd" -WorkingDirectory $frontendDir -WindowStyle Hidden -ArgumentList $frontendArgs `
        -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr | Out-Null
}

$backendReady = Wait-ForService "FastAPI backend" "http://127.0.0.1:8000/health" 90 $backendErr
$frontendReady = Wait-ForService "Next.js frontend" "http://127.0.0.1:3000/" 90 $frontendErr
if (-not ($backendReady -and $frontendReady)) {
    Write-Host "[FAIL] KshetraIQ was not opened because one or more required services failed." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] KshetraIQ is ready. Opening http://127.0.0.1:3000" -ForegroundColor Green
Start-Process "http://127.0.0.1:3000"
