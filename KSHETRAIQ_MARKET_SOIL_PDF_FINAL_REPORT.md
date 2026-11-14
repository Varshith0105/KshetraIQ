# KshetraIQ market, soil, and PDF integrity update

Date: 11 November 2026

## Root cause and market correction

The repeated ₹2,500 result was not a LightGBM prediction. `MarketPriceService.get_latest_observation` supplied a generic fallback observation (₹2,500 dated `2024-01-01`) whenever no exact live, cache, or curated benchmark record existed. For horizons up to 14 days the hybrid policy intentionally uses persistence; it therefore copied that fabricated anchor into the forecast, trend component, and displayed observation.

The fallback has been removed. A forecast now requires a verified observation for the exact canonical commodity and mandi. The order is live AGMARKNET (when configured), exact-match SQLite cache, then an explicitly dated curated benchmark. Otherwise the API returns a clear unavailable-data error. It does not substitute Wheat, Varanasi, Andhra Pradesh/Guntur, a ₹2,500 price, or a fabricated date.

The API now requires commodity and mandi. The UI sends commodity, mandi, horizon, and the selected mandi's state/district. Model categorical fields are matched against the stored LightGBM vocabulary and incompatible state, district, or variety values fail honestly. The UI label now describes the actual persistence-anchor/LightGBM seasonal architecture; its displayed components are the verified observation anchor plus forecast change, which sum to the final forecast.

## Soil score

`backend/app/services/soil_health_service.py` is the shared source of truth. It scores only supplied N, P, K, and pH values against transparent general screening bands, averages the available parameter scores, and marks a partial profile provisional. Missing measurements are never zero-filled or treated as normal. Moisture is displayed but not universally scored because texture, crop stage, and irrigation context are needed. The result includes per-parameter statuses, deficiencies/excesses, methodology, and reference limitation. It is a decision-support indicator, not a certified soil test.

The score is persisted in the assessment advisory result, so the dashboard, Soil Health view, chatbot screen context, and report see the same output.

## PDF integrity changes

The PDF now adds a Soil Health Analysis section populated from the persisted score result. It has no independent score calculation. The report no longer auto-runs a forecast for a hardcoded Nizamabad mandi: where no farmer-selected market execution exists, it states that market analysis has not been requested.

## Files changed in this continuation

- `backend/app/services/market_price_service.py`
- `backend/app/schemas/prediction.py`
- `backend/app/main.py`
- `backend/app/services/soil_health_service.py`
- `backend/app/services/advisor_service.py`
- `backend/app/schemas/assessment.py`
- `backend/app/services/report_service.py`
- `frontend/src/app/dashboard/page.tsx`
- `backend/tests/test_market_soil_integrity.py`

## Verification

- A verified pre-change SQLite backup was created at `kshetraiq.pre-market-soil-pdf-20261111.db` before any schema-related work.
- Python compilation completed for `backend/app` (one pre-existing invalid-escape warning in `agriverse_service.py`).
- Frontend TypeScript `npx tsc --noEmit` completed with no errors.
- Full backend/model inference and PDF visual verification remain unexecuted in this shell because the active Python runtime lacks required dependency `joblib` (`ModuleNotFoundError`). No claim is made that those tests passed.

## Remaining limitation

Only commodity–mandi combinations with an exact verified source record can now forecast. This is intentional: unavailable pairs are surfaced instead of being fabricated. The comprehensive PDF still needs the existing persisted prediction-history records to be joined into its irrigation, weather-risk, and market sections for full cross-module report provenance; no default values should be introduced for those fields.
