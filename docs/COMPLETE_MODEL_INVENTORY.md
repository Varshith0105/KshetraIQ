# KshetraIQ — Complete Multi-Collection Model Inventory & Audit Report

**Generated Date:** October 15, 2026  
**Auditor:** Senior ML Integration, MLOps, and Full-Stack Engineering Team  
**Scope:** Exhaustive audit of all models, training notebooks, dataset provenance, deployable artifacts, and runtime environments across all three repository source directories:
1. `E:\CapstoneProject\Agriverse_Models`
2. `E:\CapstoneProject\capstone-final`
3. `E:\CapstoneProject\AgriVerse-AI`

---

## 1. Executive Summary & Audit Methodology

Every artifact in the three source directories was systematically cataloged, measured, and inspected for:
- Binary format and exact file size in bytes
- Feature schemas, feature ordering, and units
- Training notebook code and training dataset provenance
- Model architectures, hyperparameters, and reported training metrics
- Runtime environment requirements and deserialization compatibility
- Output schemas, class distributions, and agronomic interpretation

Per KshetraIQ's **Zero-Fabrication Policy**, models are classified strictly into:
- **`VERIFIED`**: Full artifact exists, dependencies validated, input/output contract enforced, live inference active.
- **`PARTIALLY VERIFIED`**: Artifact and schema verified; live integration depends on external provider keys or runtime isolation.
- **`BLOCKED`**: Prerequisites missing or contract incomplete; transparently rejected with HTTP 400.
- **`UNAVAILABLE`**: Artifact was never saved to repository archives.
- **`EXTERNAL_SERVICE_REQUIRED`**: Dependent on third-party cloud infrastructure (e.g., Google Earth Engine).

---

## 2. Exhaustive Model Catalog

### Model 1: Multi-Crop Agronomic Suitability Recommender
- **Model ID:** `crop-recommendation-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/crop_recommendation_model.pkl` (7,281,161 bytes)
- **Companion Artifact:** `Agriverse_Models/crop_feature_names.pkl` (69 bytes)
- **Training Notebook:** `Agriverse_Models/Crop_Recommendation.ipynb`
- **Dataset Provenance:** `Crop_recommendation.csv` (2,200 records across 22 crops)
- **Algorithm:** Scikit-Learn `RandomForestClassifier` (100 estimators)
- **Input Features (7):** `N` (kg/ha), `P` (kg/ha), `K` (kg/ha), `temperature` (°C), `humidity` (%), `ph` (pH units 0–14), `rainfall` (mm)
- **Feature Order:** `[N, P, K, temperature, humidity, ph, rainfall]`
- **Output:** Multi-class probabilities across 22 crops (`apple`, `banana`, `blackgram`, `chickpea`, `coconut`, `coffee`, `cotton`, `grapes`, `jute`, `kidneybeans`, `lentil`, `maize`, `mango`, `mothbeans`, `mungbean`, `muskmelon`, `orange`, `papaya`, `pigeonpeas`, `pomegranate`, `rice`, `watermelon`).
- **Runtime:** Python 3.11–3.13, `scikit-learn>=1.6`, `joblib>=1.4` (utilizes `app.core.unpickle_patch` for Scikit-Learn 1.9+ remainder column compatibility).
- **Status:** **`VERIFIED`** — Active at `POST /api/v1/assessments`.

---

### Model 2: Crop Yield Forecaster
- **Model ID:** `crop-yield-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/crop_yield_prediction_model.pkl` (281,180,314 bytes)
- **Companion Artifact:** `Agriverse_Models/yield_feature_names.pkl`
- **Training Notebook:** `Agriverse_Models/Crop_Yield_Prediction.ipynb`
- **Dataset Provenance:** `crop_yield.csv` (historical district and state yield statistics across India)
- **Algorithm:** `Pipeline(ColumnTransformer(OneHotEncoder) + RandomForestRegressor)` ($R^2 = 0.9802$, MAE = 3.87 tonnes/ha)
- **Input Features (8):** `Crop` (string), `Season` (string), `State` (string), `Crop_Year` (int), `Area` (ha), `Annual_Rainfall` (mm), `Fertilizer` (kg), `Pesticide` (kg)
- **Output:** Yield in metric tonnes per hectare (`tonnes/ha`) and derived total farm production harvest (`tonnes` = `Yield * Area`).
- **Runtime:** Python 3.11–3.13, `scikit-learn>=1.6`, `joblib>=1.4`.
- **Status:** **`VERIFIED`** — Active at `POST /api/v1/predictions/crop-yield`.

---

### Model 3: Climate Shock Scenario Simulator
- **Model ID:** `climate-scenario-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/crop_yield_prediction_model.pkl` (281,180,314 bytes)
- **Companion Artifacts:** `Agriverse_Models/climate_change_yield_model.pkl` (64,001,658 bytes), `climate_change_feature_names.pkl`, `climate_change_model_info.pkl`
- **Training Notebook:** `Agriverse_Models/Climate_Change_Scenario_Analysis.ipynb`
- **Algorithm:** Stress Simulation Engine executing parallel perturbations at baseline, -10% precipitation shock, and -25% severe drought shock.
- **Output:** Baseline vs. shocked yields, percentage drop, farm harvest tonnage delta, and ICAR climate resilience recommendations.
- **Status:** **`VERIFIED`** — Active at `POST /api/v1/predictions/climate-scenario`.

---

### Model 4: Agronomic Sustainability Scoring Engine
- **Model ID:** `sustainability-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/sustainability_score_config.pkl` (256 bytes)
- **Companion Artifact:** `Agriverse_Models/sustainability_model_info.pkl` (477 bytes)
- **Training Notebook:** `Agriverse_Models/Carbon_Footprint_Sustainability_Score.ipynb`
- **Algorithm:** Deterministic multi-factor scoring engine evaluating fertilizer intensity (35%), pesticide intensity (30%), and yield efficiency (35%) on a 0–100 scale.
- **Output:** Score (0–100), rating (High / Moderate / Low), and reduction guidance for excess nitrogen/pesticides.
- **Status:** **`VERIFIED`** — Active at `POST /api/v1/predictions/sustainability`.

---

### Model 5: Agro-Climatic Weather Risk Classifier
- **Model ID:** `weather-risk-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/weather_risk_xgboost_model.pkl` (6,234,109 bytes)
- **Companion Artifacts:** `Agriverse_Models/weather_risk_label_encoder.pkl` (455 bytes), `Agriverse_Models/weather_risk_feature_names.pkl` (407 bytes)
- **Training Notebook:** `Agriverse_Models/Weather_Risk_Prediction.ipynb`
- **Dataset Provenance:** `india_weather_rainfall_data.xlsx`
- **Algorithm:** XGBoost Multi-Class Classifier (`xgboost==2.1.4`)
- **Input Features (27):** `month`, `season`, `state`, `avg_temp`, `min_temp`, `max_temp`, `wind_speed`, `air_pressure`, `elevation`, `latitude`, `longitude`, `previous_rainfall`, `previous_avg_temp`, `previous_wind_speed`, `previous_pressure`, `rainfall_3day`, `rainfall_7day`, `rainfall_3day_avg`, `rainfall_7day_avg`, `temp_3day_avg`, `temp_7day_avg`, `pressure_change`, `temp_change`, `wind_change`, `day_of_year`, `temp_range`, `rainfall_intensity`.
- **Output:** Risk Tier (`Low`, `Moderate`, `High`, `Extreme`) with calibrated probability distribution and field mitigations.
- **Status:** **`VERIFIED`** — Active at `POST /api/v1/predictions/weather-risk`.

---

### Model 6: APMC Mandi Price Forecasting Engine
- **Model ID:** `market-price-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/market_price_xgboost_model.pkl` (1,250,835 bytes)
- **Companion Artifacts:** `Agriverse_Models/market_price_trend_model.pkl` (851 bytes), `market_price_feature_names.pkl` (121 bytes), `market_price_model_info.pkl` (273 bytes)
- **Training Notebook:** `Agriverse_Models/Market_Price_Forecasting.ipynb`
- **Dataset Provenance:** AGMARKNET historical daily price records (2003–2023) for Wheat at Varanasi(Grain) APMC mandi (5,651 observations).
- **Algorithm:** Hybrid Time-Index Trend (`LinearRegression`) + Residual Boosting (`XGBRegressor`) ($R^2 = 0.8261$, MAE = 55.89 Rs/Quintal).
- **Features (8):** `res_lag_1`, `res_lag_7`, `res_lag_14`, `res_lag_30`, `res_rolling_7`, `res_rolling_14`, `month`, `day_of_year`.
- **Target:** `Modal_Price` (Rs./Quintal).
- **Live Data Adapter:** AGMARKNET / data.gov.in official mandi API adapter. When an API key is unconfigured or government endpoint is unreachable, returns latest verified benchmark observation with date and limitations.
- **Status:** **`PARTIALLY_VERIFIED`** — Real model and adapter contract verified.

---

### Model 7: Plant Disease Vision Classifier
- **Model ID:** `plant-disease-v1`
- **Source Collection:** `E:\CapstoneProject\capstone-final`
- **Artifact Path:** `capstone-final/plant_disease.h5` (97,936,084 bytes)
- **Companion Artifacts:** `capstone-final/resnet50_confusion_matrix.png`, `resnet50_normalized_confusion_matrix.png`
- **Training Notebook:** `capstone-final/main_file_capstone(1).ipynb`
- **Dataset Provenance:** Kaggle `karagwaanntreasure/plant-disease-detection` (35,725 images across 23 classes, 80/20 train/validation split).
- **Architecture:** Keras 3.13.2 Sequential model with ResNet50 backbone (160×160×3 RGB) + GlobalAveragePooling2D + Dense(128, relu) + Dense(23, softmax).
- **Recovered 23 Classes:**
  1. `Apple___Apple_scab`
  2. `Apple___Black_rot`
  3. `Apple___Cedar_apple_rust`
  4. `Apple___healthy`
  5. `Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot`
  6. `Corn_(maize)___Common_rust_`
  7. `Corn_(maize)___Northern_Leaf_Blight`
  8. `Corn_(maize)___healthy`
  9. `Pepper__bell___Bacterial_spot`
  10. `Pepper__bell___healthy`
  11. `Potato___Early_blight`
  12. `Potato___Late_blight`
  13. `Potato___healthy`
  14. `Tomato_Bacterial_spot`
  15. `Tomato_Early_blight`
  16. `Tomato_Late_blight`
  17. `Tomato_Leaf_Mold`
  18. `Tomato_Septoria_leaf_spot`
  19. `Tomato_Spider_mites_Two_spotted_spider_mite`
  20. `Tomato__Target_Spot`
  21. `Tomato__Tomato_YellowLeaf__Curl_Virus`
  22. `Tomato__Tomato_mosaic_virus`
  23. `Tomato_healthy`
- **Input Preprocessing:** RGB image resize to (160, 160), float32 scaling.
- **Status:** **`PARTIALLY_VERIFIED`** — Class mapping and architecture verified.

---

### Model 8: PPO Reinforcement Learning Irrigation Policy
- **Model ID:** `irrigation-rl-v1`
- **Source Collection:** `E:\CapstoneProject\Agriverse_Models`
- **Artifact Path:** `Agriverse_Models/final_rl_irrigation_ppo_model.zip` (0 bytes / absent)
- **Training Notebook:** `Agriverse_Models/RL_Irrigation_Optimization.ipynb`
- **Algorithm:** Stable-Baselines3 PPO ActorCriticPolicy with normalized Box(6,) observation space.
- **Status:** **`UNAVAILABLE`** — Artifact was saved to Colab temporary filesystem (`/content`) but omitted from repository archives. The platform transparently marks this as `UNAVAILABLE` and runs the verified ICAR deterministic irrigation advisory instead.

---

### Model 9: Sentinel-2 Satellite Vegetation Index (NDVI)
- **Model ID:** `vegetation-ndvi-v1`
- **Source Collection:** `E:\CapstoneProject\capstone-final`
- **Training Notebook:** `capstone-final/satellitle_part.ipynb`
- **Provenance:** Google Earth Engine `COPERNICUS/S2_SR_HARMONIZED`
- **Algorithm:** Remote-sensing NDVI calculation formula $(B8 - B4) / (B8 + B4)$.
- **Status:** **`EXTERNAL_SERVICE_REQUIRED`** — Requires authorized Google Earth Engine service account credentials.

---

## 3. Artifact Compatibility & Consolidation Matrix

| Model ID | Artifact Size | Runtime Requirement | Verified Contract | Production Endpoint | Capability Status |
|---|---|---|---|---|---|
| `crop-recommendation-v1` | 7.28 MB | scikit-learn 1.6+ | N, P, K, temp, humidity, pH, rain | `POST /api/v1/assessments` | **VERIFIED** |
| `crop-yield-v1` | 281.18 MB | scikit-learn 1.6+ | 8 farm & climatic factors | `POST /api/v1/predictions/crop-yield` | **VERIFIED** |
| `climate-scenario-v1` | 281.18 MB | scikit-learn 1.6+ | Baseline vs -10% / -25% rain | `POST /api/v1/predictions/climate-scenario` | **VERIFIED** |
| `sustainability-v1` | 256 B | python builtins | NPK, pesticide, yield, area | `POST /api/v1/predictions/sustainability` | **VERIFIED** |
| `weather-risk-v1` | 6.23 MB | xgboost 2.1.4 | 27 weather/location features | `POST /api/v1/predictions/weather-risk` | **VERIFIED** |
| `market-price-v1` | 1.25 MB | xgboost 2.1.4 | 8 lag/rolling price residuals | `POST /api/v1/predictions/market-price` | **PARTIALLY VERIFIED** |
| `plant-disease-v1` | 97.94 MB | keras 3.x / tf | 160×160 RGB leaf images | `POST /api/v1/predictions/plant-disease` | **PARTIALLY VERIFIED** |
| `irrigation-rl-v1` | 0 B (missing) | stable-baselines3 | Soil moisture / climate state | ICAR Deterministic Advisory | **UNAVAILABLE** |
| `vegetation-ndvi-v1` | Cloud service | Earth Engine API | Lat/Long bounding polygon | Requires Cloud Auth | **EXTERNAL SERVICE** |

