# Model registry

Status names: **partially verified** means the notebook declares a contract but production inputs or runtime validation are missing. **Blocked** means inference must not be exposed. Artifact presence is not proof of correctness.

| ID | Artifact(s) | Verified contract | Status |
| --- | --- | --- | --- |
| crop-recommendation-v1 | `crop_recommendation_model.pkl`, `crop_feature_names.pkl` | N, P, K, temperature, humidity, pH, rainfall; output is one of 22 crop labels with class probability distributions | Verified: runtime deserialization and inference operational via `CropRecommender`. Weather sourced via Open-Meteo or farmer input. Top candidates and Telugu translations active. |
| crop-yield-v1 | `crop_yield_prediction_model.pkl` | Crop, season, state, year, area, annual rainfall, fertilizer, pesticide | Blocked: referenced yield feature manifest missing; encodings and target unit unknown |
| weather-risk-v1 | `weather_risk_xgboost_model.pkl`, feature names, label encoder | 27 weather/location/rolling fields; risk labels Low/Moderate/High/Extreme occur in notebooks | Blocked: must source actual observations and validate preprocessing/categories |
| market-price-v1 | XGBoost/trend models plus feature/info pickles | Not fully established | Blocked |
| climate-scenario-v1 | model plus feature/info pickles | Not fully established | Blocked |
| sustainability-v1 | score config/info pickles | Scoring logic not verified | Blocked |
| irrigation-rl-v1 | referenced PPO zip is absent | State/action contract not fully established | Unavailable |
| plant-disease-v1 | `plant_disease.h5` | 160×160 RGB ResNet50 experiment; 23 outputs | Blocked: missing label map, TensorFlow runtime and reproducible preprocessing manifest |
| vegetation-ndvi-v1 | none | Earth Engine Sentinel-2 calculation, not local inference | Requires external authorized service |

The API runs real inference for verified `crop-recommendation-v1` when all 7 required features are supplied or retrieved. Unverified models remain transparently `blocked` or `unavailable` and never fabricate predictions.
