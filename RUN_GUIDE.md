# KshetraIQ — Final Production & Runtime Run Guide
**Platform:** KshetraIQ Agricultural Intelligence Platform  
**Root:** `F:\KshetraIQ`

---

## 1. System Architecture & Prerequisites

- **Python Runtime:** Python 3.11.9 (`.venv\Scripts\python.exe`)
- **Node.js Runtime:** Node.js 18+ / npm (`frontend/`)
- **Database:** SQLite at `backend/.tmp/kshetraiq.db`
- **Machine Learning Directory:** `Agriverse_Models/`

---

## 2. Starting the Backend Server

Open a terminal at `F:\KshetraIQ`:

```powershell
cd F:\KshetraIQ\backend
..\.venv\Scripts\uvicorn.exe app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

- **API Base URL:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/health`

---

## 3. Starting the Frontend Application

Open a second terminal at `F:\KshetraIQ`:

```powershell
cd F:\KshetraIQ\frontend
npm.cmd run dev
```

- **Web Application URL:** `http://localhost:3000`
- **Production Build Check:**
  ```powershell
  cd F:\KshetraIQ\frontend
  npm.cmd run build
  npm.cmd start
  ```

---

## 4. Environment Variables Configuration

The `.env` file at `F:\KshetraIQ\.env` contains:

```ini
KSHETRAIQ_ENVIRONMENT=development
KSHETRAIQ_MODEL_DIRECTORY=Agriverse_Models
KSHETRAIQ_STORAGE_BACKEND=sqlite
KSHETRAIQ_SQLITE_PATH=backend/.tmp/kshetraiq.db
KSHETRAIQ_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

*(Never commit `.env` or expose API secrets in version control.)*

---

## 5. Running the Complete Automated Test Suite

To verify all 159 automated unit and integration tests:

```powershell
cd F:\KshetraIQ
.venv\Scripts\python.exe -m pytest backend/tests/ -o pythonpath=backend -v
```

To run individual module test suites:
- **Chatbot 40-Question Evaluation:**
  ```powershell
  .venv\Scripts\python.exe -m pytest backend/tests/test_chatbot_40q.py -o pythonpath=backend -v
  ```
- **Live Weather Suite:**
  ```powershell
  .venv\Scripts\python.exe -m pytest backend/tests/test_weather_live.py -o pythonpath=backend -v
  ```
- **Market Forecasting Suite:**
  ```powershell
  .venv\Scripts\python.exe -m pytest backend/tests/test_market_insights_deep.py -o pythonpath=backend -v
  ```
- **Soil Health 5-Band Suite:**
  ```powershell
  .venv\Scripts\python.exe -m pytest backend/tests/test_soil_health_bands.py -o pythonpath=backend -v
  ```

---

## 6. Model Verification Audit Script

To execute standalone smoke-inference across all 8 models:

```powershell
cd F:\KshetraIQ
.venv\Scripts\python.exe backend/scripts/audit_all_models.py
```
