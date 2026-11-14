$ROOT_DIR = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $ROOT_DIR) { $ROOT_DIR = (Resolve-Path "$PSScriptRoot\..\..").Path }

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "       KSHETRAIQ - SYSTEM HEALTH AND DIAGNOSTIC AUDITOR" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- 1. ENVIRONMENT AND RUNTIME ENGINES ---" -ForegroundColor Cyan
$pyPath = Join-Path $ROOT_DIR ".venv\Scripts\python.exe"
if (Test-Path $pyPath) {
    $pyVer = & $pyPath --version
    Write-Host ("  [PASS] Python Venv: " + $pyVer) -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Python virtual environment missing at .venv" -ForegroundColor Red
}

$node = Get-Command node.exe -ErrorAction SilentlyContinue
if ($node) {
    $nVer = & node -v
    Write-Host ("  [PASS] Node.js: " + $nVer) -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Node.js not detected in system PATH" -ForegroundColor Red
}

Write-Host ""
Write-Host "--- 2. DATA STORE AND SQLITE INTEGRITY ---" -ForegroundColor Cyan
$dbPath = Join-Path $ROOT_DIR "backend\.tmp\kshetraiq.db"
if (Test-Path $dbPath) {
    $dbItem = Get-Item $dbPath
    $dbSizeMB = [math]::Round($dbItem.Length / 1MB, 2)
    Write-Host ("  [PASS] Active Database: " + $dbItem.FullName + " (" + $dbSizeMB + " MB)") -ForegroundColor Green
} else {
    Write-Host "  [WARN] Active SQLite database will be initialized on first run" -ForegroundColor Yellow
}

$backups = Get-ChildItem (Join-Path $ROOT_DIR "backend\.tmp") -Filter "*.db" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*backup*" }
if ($backups) {
    $bkNames = ($backups | ForEach-Object { $_.Name }) -join ", "
    Write-Host ("  [PASS] Backups Preserved: " + $bkNames) -ForegroundColor Green
}

Write-Host ""
Write-Host "--- 3. MACHINE LEARNING AND AI ARTIFACTS ---" -ForegroundColor Cyan
$artifacts = @(
    "Agriverse_Models\crop_recommendation_model.pkl",
    "Agriverse_Models\crop_yield_prediction_model.pkl",
    "Agriverse_Models\climate_change_yield_model.pkl",
    "Agriverse_Models\sustainability_score_config.pkl",
    "Agriverse_Models\weather_risk_xgboost_model.pkl",
    "Agriverse_Models\market_price_xgboost_model.pkl",
    "Agriverse_Models\final_rl_irrigation_ppo_model.pkl",
    "capstone-final\plant_disease.h5",
    "AgriVerse-AI\agriverse_ai.ipynb"
)

foreach ($art in $artifacts) {
    $full = Join-Path $ROOT_DIR $art
    if (Test-Path $full) {
        $sz = [math]::Round((Get-Item $full).Length / 1KB, 1)
        Write-Host ("  [PASS] " + $art + " (" + $sz + " KB)") -ForegroundColor Green
    } else {
        Write-Host ("  [FAIL] Missing: " + $art) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "--- 4. SERVICE LISTENERS AND HEALTH PROBES ---" -ForegroundColor Cyan
$bConn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($bConn) {
    Write-Host "  [ACTIVE] Port 8000 is LISTENING." -ForegroundColor Green
    try {
        $hResp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 -UseBasicParsing
        Write-Host ("  [PASS] Backend /health returned: " + $hResp.StatusCode + " OK") -ForegroundColor Green
    } catch {
        Write-Host ("  [WARN] Backend endpoint note: " + $_.Exception.Message) -ForegroundColor Yellow
    }

    try {
        $wResp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/weather/lookup?state=Andhra+Pradesh&district=Guntur" -TimeoutSec 5 -UseBasicParsing
        Write-Host ("  [PASS] Weather Open-Meteo API returned: " + $wResp.StatusCode + " OK") -ForegroundColor Green
    } catch {
        Write-Host ("  [WARN] Weather endpoint note: " + $_.Exception.Message) -ForegroundColor Yellow
    }
} else {
    Write-Host "  [STOPPED] Port 8000 (FastAPI Backend) is not running." -ForegroundColor Yellow
}

$fConn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($fConn) {
    Write-Host "  [ACTIVE] Port 3000 is LISTENING." -ForegroundColor Green
    try {
        $fResp = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 3 -UseBasicParsing
        Write-Host ("  [PASS] Frontend Homepage returned: " + $fResp.StatusCode + " OK") -ForegroundColor Green
    } catch {
        Write-Host ("  [WARN] Frontend endpoint note: " + $_.Exception.Message) -ForegroundColor Yellow
    }
} else {
    Write-Host "  [STOPPED] Port 3000 (Next.js Frontend) is not running." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "              DIAGNOSTIC AUDIT COMPLETE" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

