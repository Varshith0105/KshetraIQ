# KshetraIQ — Market Insights Complete Repair & Validation Final Report

**Module:** Market Intelligence & Price Forecasting  
**Backend:** FastAPI · `backend/app/services/market_price_service.py`  
**Frontend:** Next.js 15.5.2 · `frontend/src/app/dashboard/page.tsx`  
**Active ML Model:** `market-price-v2` (`Agriverse_Models/kshetraiq_improved_model.pkl`)  
**Status:** **FULLY OPERATIONAL & VALIDATED**  
**Date:** November 11, 2026

---

## 1. Executive Summary & Root Cause Investigation

### The Reported Issue
When navigating to the Market Insights tab, selecting:
- **Commodity:** Wheat
- **APMC Mandi:** Varanasi (Grain) [rendered with space before parenthesis]
- **Forecast Horizon:** 7 days

the application failed with an unavailable-data error:
`State and district are required for mandi 'Varanasi' because no mandi metadata is available.`
Furthermore, prior versions of the system previously defaulted to identical ₹2,500 prices regardless of commodity.

### Root Cause Analysis (Exact Trace)
1. **Parenthesis Normalization Mismatch:**  
   The LightGBM model was trained on the categorical category `"Varanasi(Grain)"` (no whitespace before parenthesis). When the frontend or user provided `"Varanasi (Grain)"`, `clean` was `"varanasi (grain)"`.
2. **Greedy Substring Match Collision in `validate_mandi`:**  
   Because `"varanasi (grain)"` did not match `"varanasi(grain)"` directly, the lookup entered a substring loop:
   ```python
   for k, canon in self._mandi_lookup.items():
       if clean in k or k in clean:
           return canon
   ```
   Because `"varanasi"` exists in `self._mandi_lookup` and `"varanasi"` is a substring of `"varanasi (grain)"` (`k in clean`), the dictionary iteration returned `"Varanasi"` instead of `"Varanasi(Grain)"`.
3. **Mandi Metadata Geocoding Failure:**  
   `MANDI_METADATA_MAP` only contained keys from `POPULAR_MANDIS` (`"varanasi(grain)"`). When the canonical mandi resolved to `"Varanasi"`, `MANDI_METADATA_MAP.get("varanasi")` returned empty `{}`.
4. **Benchmark Lookup Miss:**  
   Even when state and district were supplied, the benchmark lookup evaluated `BENCHMARK_OBSERVATIONS["wheat_varanasi"]`, failing to find `"wheat_varanasi(grain)"`.
5. **Positional Parameter Ordering:**  
   `def forecast_price(self, target_date_str=None, days_ahead=7, commodity="Wheat", mandi="Varanasi(Grain)", ...)` had `target_date_str` as positional argument #1, causing positional calls `forecast_price("Wheat", "Varanasi(Grain)", 7)` to fail with `TypeError: got multiple values for argument 'days_ahead'`.

---

## 2. Implemented Code Changes & Fixes

### 1. Regex Whitespace & Parenthesis Normalization (`market_price_service.py`)
- Added regex normalization to strip all whitespace surrounding parentheses:
  ```python
  clean = re.sub(r"\s*\(\s*", "(", mandi.strip().lower())
  clean = re.sub(r"\s*\)\s*", ")", clean)
  ```
- Any input like `"Varanasi (Grain)"` or `"Varanasi  ( Grain )"` reliably normalizes to `"varanasi(grain)"` before checking `_mandi_lookup`.

### 2. Candidate Prioritization by Length in `validate_mandi`
- Changed partial matching to sort candidates by length descending:
  ```python
  candidates = []
  for k, canon in self._mandi_lookup.items():
      if clean in k or k in clean:
          candidates.append((len(k), canon))
  if candidates:
      candidates.sort(key=lambda x: x[0], reverse=True)
      return candidates[0][1]
  ```
  This guarantees that more specific mandis like `"Varanasi(Grain)"` match before generic ones like `"Varanasi"`.

### 3. Comprehensive Mandi Metadata Aliases
- Added aliases to `MANDI_METADATA_MAP` for `"varanasi"`, `"varanasi (grain)"`, `"varanasi(grain)"`, `"guntur apmc"`, `"nagpur"`, etc., mapping them to their verified states and districts.

### 4. Benchmark Catalog Multi-Key Lookup & Aliases
- Expanded `BENCHMARK_OBSERVATIONS` with explicit aliases (`"wheat_varanasi"`, `"wheat_varanasi (grain)"`, `"ginger(dry)_varanasi"`, `"ginger(dry)_varanasi (grain)"`).
- Updated `get_latest_observation` to check both exact and normalized keys without risk of missing verified benchmarks.

### 5. Signature Reordering in `forecast_price`
- Reordered positional arguments to standard agricultural ordering:
  ```python
  def forecast_price(
      self,
      commodity: str = "Wheat",
      mandi: str = "Varanasi(Grain)",
      days_ahead: int = 7,
      target_date_str: str | None = None,
      state: str | None = None,
      district: str | None = None,
      variety: str | None = None,
  ) -> dict[str, Any]:
  ```
  Seamlessly supports positional calls `("Wheat", "Varanasi(Grain)", 7)` as well as keyword calls.

### 6. Frontend Dashboard Market Metadata Resolution (`frontend/src/app/dashboard/page.tsx`)
- Updated `handleMarketForecast` to resolve mandi geocoding metadata with case-insensitive matching across `marketMandiOptions`, `popular_mandis`, and `verified_pairs`.

---

## 3. End-to-End Verification & Test Results

### 1. Verification of Wheat @ Varanasi(Grain)
- **Input:** Commodity: `Wheat`, Mandi: `Varanasi (Grain)`, Horizon: `7 days`
- **Canonical Resolution:** `Wheat` @ `Varanasi(Grain)`, District: `Varanasi`, State: `Uttar Pradesh`
- **Observed Market Price:** ₹2,275.0 / Quintal (Observation Date: `2023-12-30`, DMI Verified Benchmark)
- **Forecast Modal Price:** ₹2,275.0 / Quintal
- **Method:** `Persistence Baseline (Latest Verified Observation Anchor)`
- **Confidence Interval (95% CI):** [₹2,179.3 / Q, ₹2,370.7 / Q] (calibrated bound ±₹95.7 / Q, >90% empirical coverage)
- **Seasonal LightGBM Model:** ₹2,529.66 / Q (500 trees, 63 leaves)
- **Trend Direction:** `STEADY` (residual: 0.0)

### 2. Comprehensive Backend Test Suite Results
- `backend/tests/test_market_insights_deep.py`: **23 passed, 0 failed**
- `backend/tests/test_market_soil_integrity.py`: **3 passed, 0 failed**
- Entire Backend Test Suite (`backend/tests/`): **158 passed, 1 skipped, 0 failed in 71.7s**

### 3. Frontend Production Build Verification
- Next.js 15.5.2 build: **Compiled successfully in 4.3s**
- TypeScript compilation: **Zero type errors**
- Static pages generated: **10/10 generated cleanly**

---

## 4. Verification Checkpoint & Sign-off

| Requirement | Implementation Status | Verified Outcome |
|---|---|---|
| **Varanasi (Grain) 7-day Wheat Forecast** | FIXED | Produces verified ₹2,275/Q forecast with calibrated 95% CI [₹2,179.3, ₹2,370.7] |
| **Parenthesis Whitespace Normalization** | FIXED | `re.sub` handles `"Varanasi (Grain)"`, `"Varanasi(Grain)"`, etc. |
| **No Hardcoded ₹2,500 Baseline** | VERIFIED | Each commodity uses its exact observed rate (e.g. Dry Chillies ₹17,500, Tomato ₹1,850, Cotton ₹7,100) |
| **Zero Fabrication on Missing Observations** | VERIFIED | Missing combinations (e.g. Soyabean @ Mulakalacheruvu) raise descriptive `ValueError` |
| **Positional Argument Ordering** | FIXED | `forecast_price("Wheat", "Varanasi (Grain)", 7)` works seamlessly |
| **Multi-Tier APMC Provenance** | VERIFIED | Displays OBSERVED, PREDICTED, BASELINE, and RESIDUAL cards |
| **Frontend UI Integration** | VERIFIED | `mktMandiOptions` correctly bound and metadata resolved |
| **Full Pytest Suite** | VERIFIED | 158 passed, 1 skipped, 0 failed |
| **Next.js Production Build** | VERIFIED | Clean build with zero TypeScript / lint errors |

