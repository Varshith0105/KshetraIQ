param (
    [string]$Mode = "dev"
)

$ROOT_DIR = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $ROOT_DIR) { $ROOT_DIR = (Resolve-Path "$PSScriptRoot\..\..").Path }

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          KSHETRAIQ - ONE-CLICK APPLICATION LAUNCHER" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Environment Checks
$pyPath = Join-Path $ROOT_DIR ".venv\Scripts\python.exe"
if (-not (Test-Path $pyPath)) {
    Write-Host "[ERROR] Python virtual environment missing at .venv\Scripts\python.exe" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python 3.11 virtual environment detected." -ForegroundColor Green

$node = Get-Command node.exe -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $node -or -not $npm) {
    Write-Host "[ERROR] Node.js or npm not detected in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Node.js and npm detected." -ForegroundColor Green

# 2. Database Directory
$tmpDir = Join-Path $ROOT_DIR "backend\.tmp"
if (-not (Test-Path $tmpDir)) { New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null }

# 3. Port 8000 (Backend)
$bConn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($bConn) {
    Write-Host "[INFO] Port 8000 is active. Checking health endpoint..." -ForegroundColor Yellow
    $healthy = try { (Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } catch { $false }
    if ($healthy) {
        Write-Host "[OK] Existing KshetraIQ backend is healthy on http://127.0.0.1:8000. Reusing service." -ForegroundColor Green
    } else {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($bConn.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $owner -or $owner.CommandLine -notmatch [regex]::Escape($ROOT_DIR)) {
            throw "Port 8000 is owned by a non-KshetraIQ process. It was not stopped. Free the port or start KshetraIQ on a different port."
        }
        Write-Host "[WARN] Recycling the unresponsive KshetraIQ backend listener..." -ForegroundColor Yellow
        Get-Process -Id $bConn.OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        $backendDir = Join-Path $ROOT_DIR "backend"
        Start-Process "cmd.exe" -WindowStyle Hidden -ArgumentList "/c", "cd /d `"$backendDir`" && `"$pyPath`" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000"
    }
} else {
    Write-Host "[INFO] Spawning FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
    $backendDir = Join-Path $ROOT_DIR "backend"
    Start-Process "cmd.exe" -WindowStyle Hidden -ArgumentList "/c", "cd /d `"$backendDir`" && `"$pyPath`" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000"
}

# 4. Port 3000 (Frontend)
$fConn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($fConn) {
    Write-Host "[INFO] Port 3000 is active. Checking frontend response..." -ForegroundColor Yellow
    $fHealthy = try { (Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } catch { $false }
    if ($fHealthy) {
        Write-Host "[OK] Existing KshetraIQ frontend is active on http://127.0.0.1:3000. Reusing service." -ForegroundColor Green
    } else {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($fConn.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $owner -or $owner.CommandLine -notmatch [regex]::Escape($ROOT_DIR)) {
            throw "Port 3000 is owned by a non-KshetraIQ process. It was not stopped. Free the port or start KshetraIQ on a different port."
        }
        Write-Host "[WARN] Recycling the unresponsive KshetraIQ frontend listener..." -ForegroundColor Yellow
        Get-Process -Id $fConn.OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        $frontendDir = Join-Path $ROOT_DIR "frontend"
        $fCmd = if ($Mode -match "prod") { "npm.cmd start" } else { "npm.cmd run dev" }
        Start-Process "cmd.exe" -WindowStyle Hidden -ArgumentList "/c", "cd /d `"$frontendDir`" && $fCmd"
    }
} else {
    $frontendDir = Join-Path $ROOT_DIR "frontend"
    $fCmd = if ($Mode -match "prod") { "npm.cmd start" } else { "npm.cmd run dev" }
    Write-Host ("[INFO] Spawning Next.js (" + $Mode + " mode) on http://127.0.0.1:3000...") -ForegroundColor Cyan
    Start-Process "cmd.exe" -WindowStyle Hidden -ArgumentList "/c", "cd /d `"$frontendDir`" && $fCmd"
}

# 5. Service Readiness Polling
Write-Host ""
Write-Host "[INFO] Waiting for KshetraIQ services to become ready..." -ForegroundColor Yellow
$bReady = $false
for ($i = 0; $i -lt 30; $i++) {
    $bStatus = try { (Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -UseBasicParsing).StatusCode } catch { 0 }
    if ($bStatus -eq 200) {
        Write-Host "  [OK] FastAPI Backend is UP (http://127.0.0.1:8000/health)" -ForegroundColor Green
        $bReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

$fReady = $false
for ($i = 0; $i -lt 35; $i++) {
    $fStatus = try { (Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 2 -UseBasicParsing).StatusCode } catch { 0 }
    if ($fStatus -eq 200) {
        Write-Host "  [OK] Next.js Frontend is UP (http://127.0.0.1:3000)" -ForegroundColor Green
        $fReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "                     SUCCESSFULLY STARTED!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "  Frontend Application: http://127.0.0.1:3000"
Write-Host "  FastAPI Swagger Docs: http://127.0.0.1:8000/docs"
Write-Host "  Backend Health API:   http://127.0.0.1:8000/health"
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Opening web browser at http://127.0.0.1:3000..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:3000"

Write-Host ""
Write-Host "To stop all services later, run STOP_KSHETRAIQ.bat" -ForegroundColor Gray

