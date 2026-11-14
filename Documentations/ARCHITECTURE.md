# Architecture

## Boundary and flow

`Next.js browser` → `FastAPI validation/API` → `service + repository interface` → `approved model adapter` → `versioned result/history`.

The current implementation provides the browser shell, FastAPI boundary, typed assessment contract, an in-memory development repository, and registry status. Supabase is intentionally an interface/configuration concern until credentials and migrations are supplied.

## Routes and contracts

* `GET /health` returns API liveness.
* `POST /api/v1/assessments` accepts a farm profile, soil-report values, water context and language; it returns an ID, validated payload, model statuses, assumptions, and limitations.
* `GET /api/v1/assessments/{id}` reads an in-memory record in this scaffold.

Planned frontend routes: `/` landing/assessment entry, `/dashboard`, `/farms/[id]`, `/assessments/[id]`, `/assistant`, `/history`, and `/reports/[id]`.

## Data model and security boundary

Supabase tables should be `profiles`, `farms`, `farm_assessments`, `prediction_runs`, `conversations`, `messages`, and `report_jobs`. Each row must carry `farmer_id`; RLS must limit it to `auth.uid()`. Private Storage buckets should hold land photos, soil reports, and generated reports with short-lived signed URLs only.

The browser may use only the Supabase anon key. The service-role key, LLM provider keys, model paths, OCR and report generation run server-side. Validate size/MIME, virus-scan uploads before extraction, retain original uploads privately, require review of any OCR fields, and do not log request bodies containing sensitive farm data or secrets.

## Assistant and reporting design

A supervisor can select only explicit tools: read authorized farm context, read a persisted prediction run, fetch configured weather/market sources, and ask a verified model adapter. The assistant must cite tool output/model version, request missing inputs, and never manufacture predictions. LangGraph is optional and should be introduced only after tool authorization and persistent state are implemented.

Report creation is a two-step action: `POST /reports/preview` produces reviewable metadata, then an explicit `POST /reports/{id}/confirm` queues generation. A report includes inputs, sourced data, model versions, assumptions, limitations and date; no automatic download or generation follows an assessment.
