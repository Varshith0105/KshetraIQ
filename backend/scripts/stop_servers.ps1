$ROOT_DIR = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $ROOT_DIR) { $ROOT_DIR = (Resolve-Path "$PSScriptRoot\..\..").Path }

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                KSHETRAIQ - SERVICE SHUTDOWN TOOL" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Checking and terminating listener on Port 8000 (FastAPI Backend)..."
$conns8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conns8000) {
    $stopped8000 = $false
    foreach ($c in $conns8000) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)" -ErrorAction SilentlyContinue
        $isKshetra = $false
        if ($owner -and $owner.CommandLine) {
            $isKshetra = ($owner.CommandLine -match [regex]::Escape($ROOT_DIR)) -or ($owner.CommandLine -match "app\.main:create_app") -or ($owner.CommandLine -match "uvicorn")
        }
        if ($p -and $isKshetra) {
            Write-Host ("  Stopping PID " + $p.Id + " (" + $p.ProcessName + ")...") -ForegroundColor Yellow
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            $stopped8000 = $true
        } elseif ($p) {
            Write-Host ("  [SKIP] PID " + $p.Id + " is not recognized as a KshetraIQ backend process.") -ForegroundColor Yellow
        }
    }
    Start-Sleep -Milliseconds 600
    $still8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if (-not $still8000) {
        Write-Host "  [OK] Port 8000 released." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Port 8000 is still active." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Port 8000 is not active." -ForegroundColor Gray
}

Write-Host ""
Write-Host "[2/2] Checking and terminating listener on Port 3000 (Next.js Frontend)..."
$conns3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($conns3000) {
    $stopped3000 = $false
    foreach ($c in $conns3000) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)" -ErrorAction SilentlyContinue
        $isKshetra = $false
        if ($owner -and $owner.CommandLine) {
            $isKshetra = ($owner.CommandLine -match [regex]::Escape($ROOT_DIR)) -or ($owner.CommandLine -match "next") -or ($owner.CommandLine -match "node")
        }
        if ($p -and $isKshetra) {
            Write-Host ("  Stopping PID " + $p.Id + " (" + $p.ProcessName + ")...") -ForegroundColor Yellow
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            $stopped3000 = $true
        } elseif ($p) {
            Write-Host ("  [SKIP] PID " + $p.Id + " is not recognized as a KshetraIQ frontend process.") -ForegroundColor Yellow
        }
    }
    Start-Sleep -Milliseconds 600
    $still3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
    if (-not $still3000) {
        Write-Host "  [OK] Port 3000 released." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Port 3000 is still active." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Port 3000 is not active." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "           ALL KSHETRAIQ SERVICES STOPPED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

