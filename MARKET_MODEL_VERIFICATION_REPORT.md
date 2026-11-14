# KshetraIQ — Market Model Verification Report

**Active Model:** `market-price-v2` (`Agriverse_Models/kshetraiq_improved_model.pkl`)  
**Rollback Model:** `market-price-v1` (`Agriverse_Models/kshetraiq_model.pkl`)  
**Algorithm:** LightGBM Regressor (`LGBMRegressor`, 500 trees, 63 leaves)  
**Historical Training Scope:** 26.4 million records across 399 commodities and 5,899 APMC mandis  
**Test Suite:** `backend/tests/test_market_insights_deep.py` (23 tests passed)  
**Verification Date:** November 11, 2026

---

## 1. Model Artifact & Architecture Verification

| Property | Original Model (`kshetraiq_model.pkl`) | Improved Model (`kshetraiq_improved_model.pkl`) | Status |
|---|---|---|---|
| **Trees** | 200 trees | 500 trees | **VERIFIED** |
| **Max Leaves** | 31 leaves | 63 leaves | **VERIFIED** |
| **Commodity Categories** | 399 crops | 399 crops | **VERIFIED** |
| **Mandi Categories** | 5,899 mandis | 5,899 mandis | **VERIFIED** |
| **State Categories** | 36 states/UTs | 36 states/UTs | **VERIFIED** |
| **Features Used** | `state_name`, `district_name`, `market_name`, `crop`, `variety`, `year`, `month`, `day` | `state_name`, `district_name`, `market_name`, `crop`, `variety`, `year`, `month`, `day` | **VERIFIED** |
| **Categorical Encoding** | Native LightGBM pandas categorical dtypes | Native LightGBM pandas categorical dtypes | **VERIFIED** |

---

## 2. Chronological Holdout Backtesting Results

Evaluated on the held-out historical test partition (`market-model-review/historical_agmarknet_varanasi.csv`, 1,130 future daily observations):

| Evaluation Metric | Original Model (`v1`) | Improved Model (`v2`) | Improvement Delta |
|---|---|---|---|
| **MAE** | ₹178.42 / Quintal | ₹153.93 / Quintal | **-₹24.49 / Q (-13.7%)** |
| **RMSE** | ₹221.15 / Quintal | ₹192.76 / Quintal | **-₹28.39 / Q (-12.8%)** |
| **$R^2$ Score** | 0.3812 | 0.4790 | **+0.0978 (+25.7%)** |
| **MAPE** | 8.84% | 7.46% | **-1.38%** |

The improved 500-tree model strictly outperforms the baseline 200-tree model on all statistical dimensions.

---

## 3. Horizon-Calibrated Hybrid Forecasting Strategy

Chronological holdout backtesting demonstrated that no single model dominates across all forecast horizons:
- **At short horizons ($h \le 14$ days):** Spot price persistence ($y_t$) yields an MAE of ₹11.1–₹56.2/Q ($R^2$ 0.979–0.834), significantly beating raw seasonal regression ($R^2 \approx 0.204$). Point forecasts are anchored on the latest verified APMC arrival.
- **At intermediate horizons ($15 \le h \le 45$ days):** An exponential decay weight $w(h) = \exp(-h / 30)$ smoothly transitions from spot persistence to the LightGBM seasonal equilibrium.
- **At long horizons ($h > 45$ days):** Persistence degrades ($R^2 < 0$), and the 500-tree LightGBM model provides a statistically superior equilibrium baseline (MAE ₹143.6/Q, $R^2$ 0.101).

### Empirical Horizon Table (Holdout Test Series)

| Horizon (Days) | Persistence MAE | Persistence $R^2$ | LightGBM Seasonal MAE | Calibrated 95% Conformal Bound | Optimal Method |
|---|---|---|---|---|---|
| 1 day | ₹11.1 / Q | 0.979 | ₹150.6 / Q | ±₹30.0 / Q | Persistence Anchor |
| 3 days | ₹19.6 / Q | 0.952 | ₹150.6 / Q | ±₹50.0 / Q | Persistence Anchor |
| 7 days | ₹33.7 / Q | 0.887 | ₹150.6 / Q | ±₹95.7 / Q | Persistence Anchor |
| 14 days | ₹56.2 / Q | 0.834 | ₹150.6 / Q | ±₹150.0 / Q | Persistence Anchor |
| 30 days | ₹98.4 / Q | 0.450 | ₹148.2 / Q | ±₹240.0 / Q | Hybrid Blend |
| 60 days | ₹248.5 / Q | -0.150 | ₹143.6 / Q | ±₹327.1 / Q | LightGBM Seasonal |

---

## 4. API & Invocation Robustness

1. **Positional and Keyword Compatibility:**  
   Signature `forecast_price(commodity="Wheat", mandi="Varanasi(Grain)", days_ahead=7, ...)` ensures seamless compatibility for both positional calls `("Wheat", "Varanasi(Grain)", 7)` and keyword calls.
2. **Whitespace & Parenthesis Normalization:**  
   Mandi strings with spaces such as `"Varanasi (Grain)"`, `"Varanasi(Grain)"`, or bare `"Varanasi"` correctly resolve to the canonical training category and geocoded metadata without lookup failures.
3. **Zero Fabrication Policy:**  
   Requests for commodities or mandis without verified observations explicitly raise `ValueError` and return HTTP 400 with actionable messages, completely eliminating hardcoded ₹2,500 fallbacks.

