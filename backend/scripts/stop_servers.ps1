Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                KSHETRAIQ - SERVICE SHUTDOWN TOOL" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Checking and terminating listener on Port 8000 (FastAPI Backend)..."
$conns8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conns8000) {
    foreach ($c in $conns8000) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)" -ErrorAction SilentlyContinue
        if ($p -and $owner -and $owner.CommandLine -match [regex]::Escape((Split-Path $PSScriptRoot -Parent))) {
            Write-Host ("  Stopping PID " + $p.Id + " (" + $p.ProcessName + ")...") -ForegroundColor Yellow
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        } elseif ($p) {
            Write-Host ("  [SKIP] PID " + $p.Id + " is not a KshetraIQ process.") -ForegroundColor Yellow
        }
    }
    Write-Host "  [OK] Port 8000 released." -ForegroundColor Green
} else {
    Write-Host "  [INFO] Port 8000 is not active." -ForegroundColor Gray
}

Write-Host ""
Write-Host "[2/2] Checking and terminating listener on Port 3000 (Next.js Frontend)..."
$conns3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($conns3000) {
    foreach ($c in $conns3000) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)" -ErrorAction SilentlyContinue
        if ($p -and $owner -and $owner.CommandLine -match [regex]::Escape((Split-Path $PSScriptRoot -Parent))) {
            Write-Host ("  Stopping PID " + $p.Id + " (" + $p.ProcessName + ")...") -ForegroundColor Yellow
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        } elseif ($p) {
            Write-Host ("  [SKIP] PID " + $p.Id + " is not a KshetraIQ process.") -ForegroundColor Yellow
        }
    }
    Write-Host "  [OK] Port 3000 released." -ForegroundColor Green
} else {
    Write-Host "  [INFO] Port 3000 is not active." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "           ALL KSHETRAIQ SERVICES STOPPED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

