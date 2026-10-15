from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.assessment import FarmAssessmentRequest, ModelResult
from app.schemas.prediction import ModelHealthResponse
from app.services.crop_recommender import CropRecommender


@dataclass(frozen=True)
class ModelDefinition:
    model_id: str
    display_name: str
    artifact: str
    required_fields: tuple[str, ...]
    contract_status: str
    note: str
    endpoint: str | None = None


MODEL_REGISTRY: tuple[ModelDefinition, ...] = (
    ModelDefinition(
        model_id="crop-recommendation-v1",
        display_name="Crop Recommendation Classifier",
        artifact="crop_recommendation_model.pkl",
        required_fields=(
            "soil.nitrogen_kg_ha",
            "soil.phosphorus_kg_ha",
            "soil.potassium_kg_ha",
            "soil.ph",
            "weather.temperature_c",
            "weather.humidity_percent",
            "weather.rainfall_mm",
        ),
        contract_status="verified",
        note="Random Forest model (200 estimators) trained on verified N, P, K, pH, temperature, humidity, rainfall features across 22 crops.",
        endpoint="/api/v1/predictions/crop-recommendation",
    ),
    ModelDefinition(
        model_id="crop-yield-v1",
        display_name="Crop Yield Regressor",
        artifact="crop_yield_prediction_model.pkl",
        required_fields=("crop", "season", "state", "crop_year", "area", "annual_rainfall", "fertilizer", "pesticide"),
        contract_status="verified",
        note="Pipeline with OneHotEncoder and Random Forest Regressor calibrated on historical state crop yield records (R² = 0.9802).",
        endpoint="/api/v1/predictions/crop-yield",
    ),
    ModelDefinition(
        model_id="climate-scenario-v1",
        display_name="Climate Change Scenario Analysis",
        artifact="climate_change_yield_model.pkl",
        required_fields=("crop", "crop_year", "season", "state", "baseline_rainfall_mm"),
        contract_status="verified",
        note="Random Forest Scenario Engine measuring crop yield sensitivity under simulated 10% and 25% moisture stress shocks.",
        endpoint="/api/v1/predictions/climate-scenario",
    ),
    ModelDefinition(
        model_id="sustainability-v1",
        display_name="Sustainability & Carbon Footprint Score",
        artifact="sustainability_score_config.pkl",
        required_fields=("area_hectares", "fertilizer_kg", "pesticide_kg", "yield_tonnes_per_ha"),
        contract_status="verified",
        note="Deterministic agronomic eco-efficiency index (0-100) weighing chemical fertilizer, pesticide intensity, and yield density.",
        endpoint="/api/v1/predictions/sustainability",
    ),
    ModelDefinition(
        model_id="weather-risk-v1",
        display_name="Weather Risk Assessment Classifier",
        artifact="weather_risk_xgboost_model.pkl",
        required_fields=("month", "season", "state", "avg_temp_c", "wind_speed_kmh", "air_pressure_hpa", "rainfall_mm"),
        contract_status="verified",
        note="XGBoost Classifier (multi:softprob) predicting agricultural meteorological hazard tiers (Low, Moderate, High, Extreme).",
        endpoint="/api/v1/predictions/weather-risk",
    ),
    ModelDefinition(
        model_id="market-price-v1",
        display_name="Mandi Price Time-Series Forecasting",
        artifact="market_price_xgboost_model.pkl",
        required_fields=("crop", "district", "state"),
        contract_status="blocked",
        note="Time-series autoregressive lag pipeline trained specifically on Varanasi Wheat; blocked pending APMC live streaming feed.",
        endpoint=None,
    ),
    ModelDefinition(
        model_id="irrigation-rl-v1",
        display_name="Reinforcement Learning Irrigation Agent",
        artifact="final_rl_irrigation_ppo_model.zip",
        required_fields=("soil_moisture", "soil_temperature", "humidity"),
        contract_status="unavailable",
        note="Referenced Stable-Baselines3 PPO zip artifact is absent from repository; rule-based ICAR scheduling active instead.",
        endpoint=None,
    ),
    ModelDefinition(
        model_id="plant-disease-v1",
        display_name="Plant Disease Diagnostic Vision",
        artifact="plant_disease.h5",
        required_fields=("image",),
        contract_status="blocked",
        note="ResNet50 H5 model is missing deployable class labels mapping and TensorFlow runtime manifest in Python 3.13.",
        endpoint=None,
    ),
)


_recommender_cache: dict[Path, CropRecommender] = {}


def get_crop_recommender(model_directory: Path) -> CropRecommender:
    if model_directory not in _recommender_cache:
        _recommender_cache[model_directory] = CropRecommender(model_directory)
    return _recommender_cache[model_directory]


def get_model_health(model_id: str, model_directory: Path) -> ModelHealthResponse | None:
    defn = next((m for m in MODEL_REGISTRY if m.model_id == model_id), None)
    if not defn:
        return None

    artifact_path = model_directory / defn.artifact
    artifact_found = artifact_path.is_file()
    runtime_ready = defn.contract_status == "verified" and artifact_found

    return ModelHealthResponse(
        model_id=defn.model_id,
        display_name=defn.display_name,
        status=defn.contract_status,
        artifact_name=defn.artifact,
        artifact_found=artifact_found,
        runtime_ready=runtime_ready,
        required_inputs=list(defn.required_fields),
        notes=defn.note,
        endpoint=defn.endpoint,
    )


def assessment_model_status(payload: FarmAssessmentRequest, model_directory: Path) -> list[ModelResult]:
    weather = payload.weather
    values: dict[str, Any] = {
        "soil.nitrogen_kg_ha": payload.soil.nitrogen_kg_ha,
        "soil.phosphorus_kg_ha": payload.soil.phosphorus_kg_ha,
        "soil.potassium_kg_ha": payload.soil.potassium_kg_ha,
        "soil.ph": payload.soil.ph,
        "weather.temperature_c": weather.temperature_c if weather else None,
        "weather.humidity_percent": weather.humidity_percent if weather else None,
        "weather.rainfall_mm": weather.rainfall_mm if weather else None,
        "season": payload.season,
        "state": payload.state,
        "acreage": payload.acreage,
    }

    results: list[ModelResult] = []

    for definition in MODEL_REGISTRY:
        missing = [field for field in definition.required_fields if values.get(field) is None]
        artifact_exists = (model_directory / definition.artifact).is_file()

        if definition.model_id == "crop-recommendation-v1":
            if missing:
                results.append(
                    ModelResult(
                        model_id=definition.model_id,
                        status="needs_input",
                        message=f"Additional verified inputs are required before inference: {', '.join(missing)}.",
                        missing_inputs=missing,
                        contract_note=definition.note,
                    )
                )
            elif not artifact_exists:
                results.append(
                    ModelResult(
                        model_id=definition.model_id,
                        status="unavailable",
                        message="The configured model artifact crop_recommendation_model.pkl was not found.",
                        contract_note=definition.note,
                    )
                )
            else:
                try:
                    recommender = get_crop_recommender(model_directory)
                    if recommender.is_available:
                        prediction = recommender.predict(
                            n=float(values["soil.nitrogen_kg_ha"]),
                            p=float(values["soil.phosphorus_kg_ha"]),
                            k=float(values["soil.potassium_kg_ha"]),
                            temperature=float(values["weather.temperature_c"]),
                            humidity=float(values["weather.humidity_percent"]),
                            ph=float(values["soil.ph"]),
                            rainfall=float(values["weather.rainfall_mm"]),
                        )
                        results.append(
                            ModelResult(
                                model_id=definition.model_id,
                                status="predicted",
                                message="Crop recommendation verified and generated from trained Random Forest model.",
                                prediction=prediction,
                                contract_note=definition.note,
                            )
                        )
                    else:
                        results.append(
                            ModelResult(
                                model_id=definition.model_id,
                                status="unavailable",
                                message=recommender.load_error or "Model artifact could not be initialized.",
                                contract_note=definition.note,
                            )
                        )
                except Exception as exc:
                    results.append(
                        ModelResult(
                            model_id=definition.model_id,
                            status="unavailable",
                            message=f"Error executing crop recommendation: {exc}",
                            contract_note=definition.note,
                        )
                    )
        else:
            # Other models in assessment status overview
            results.append(
                ModelResult(
                    model_id=definition.model_id,
                    status=definition.contract_status,
                    message=definition.note,
                    contract_note=definition.note,
                )
            )

    return results
