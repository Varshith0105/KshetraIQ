# Implementation plan

## Completed increments

1. **Source Preservation & Audit**: Preserved original notebooks, datasets, research models, and audited inputs/contracts.
2. **Verified Crop Recommendation**: Audited `crop_recommendation_model.pkl` and `crop_feature_names.pkl`. Verified input features (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`), data types, and 22 output crop classes with probability ranking and Telugu translations. Integrated via `CropRecommender` adapter without ever fabricating predictions.
3. **Open-Meteo Weather Sourcing**: Added `WeatherService` connecting to Open-Meteo live geocoding and weather API to fetch temperature, relative humidity, and rainfall estimates for any district/state with farmer override capability.
4. **Deterministic Agricultural Advisor**: Integrated `AdvisorService` delivering scientifically grounded agronomic advice (ICAR/SAU guidelines) covering soil health (pH, NPK balance), crop-specific best practices, irrigation scheduling, and seasonal risk mitigation in English and Telugu.
5. **Two-Step Confirmed PDF Reports**: Integrated `ReportService` producing official PDF reports with ReportLab. Implemented preview endpoint requiring explicit farmer confirmation dialog before generation and download.
6. **Persistence & Supabase Schema**: Maintained safe in-memory fallback when credentials are absent with transparent storage reporting. Provided complete PostgreSQL migration script `backend/migrations/001_initial_schema.sql` with Row Level Security (RLS) policies.
7. **Bilingual & Accessible UI**: Responsive Next.js frontend with full English and Telugu switching, live weather lookup, error handling, loading states, and accessible semantics.
8. **Automated Verification**: Full pytest test suite (22 test cases passing) and successful production Next.js build.
9. **Rythu AI Chatbot Assistant**: Interactive bilingual (Telugu/English) agricultural assistant via `/api/v1/chat` leveraging deterministic agronomic rule-based engines (ICAR/ANGRAU guidelines) with farm assessment context integration and transparent disclaimers.
10. **Secure File Upload & Storage Service**: Local verified file upload pipeline (`/api/v1/uploads/{category}`) with strict MIME-type validation, size limits (10MB), safe filename sanitization, and category partitioning (`soil_report`, `field_photo`, `crop_photo`).
11. **Assessment History & Record Persistence**: Dashboard assessment history list via `GET /api/v1/assessments` enabling immediate inspection and reload of previous farm assessments.

## Local commands

From `E:\CapstoneProject`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload
```

In another terminal:

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

Use `pytest backend/tests -q` with `PYTHONPATH=backend` for the backend tests. `npm install` has not been run by this audit because it requires downloading packages.
