"""Weather Risk Assessment Service — XGBoost pipeline adapter."""

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

import app.core.unpickle_patch  # noqa: F401
from app.schemas.prediction import WeatherRiskRequest, WeatherRiskResponse

logger = logging.getLogger(__name__)

MONTH_NAMES: list[str] = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Map common Indian states to standard two-letter meteorological state abbreviations
STATE_ABBR_MAP: dict[str, str] = {
    "andhra pradesh": "AP",
    "telangana": "TG",
    "tamil nadu": "TN",
    "karnataka": "KA",
    "maharashtra": "MH",
    "kerala": "KL",
    "gujarat": "GJ",
    "rajasthan": "RJ",
    "punjab": "PB",
    "haryana": "HR",
    "uttar pradesh": "UP",
    "madhya pradesh": "MP",
    "bihar": "BR",
    "odisha": "OD",
    "west bengal": "WB",
    "assam": "AS",
}

SEASON_MAP: dict[str, str] = {
    "kharif": "Monsoon",
    "rabi": "Winter",
    "summer": "Summer",
    "zaid": "Summer",
    "monsoon": "Monsoon",
    "post-monsoon": "Post-monsoon",
    "winter": "Winter",
}


class WeatherRiskService:
    """Inference service for assessing meteorological disaster and crop weather risk."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        self._model: Any = None
        self._encoder: Any = None
        self._feature_names: list[str] = []
        self._is_loaded = False
        self._load_error: str | None = None
        self._init_model()

    def _init_model(self) -> None:
        model_file = self.model_directory / "weather_risk_xgboost_model.pkl"
        encoder_file = self.model_directory / "weather_risk_label_encoder.pkl"
        features_file = self.model_directory / "weather_risk_feature_names.pkl"

        if not model_file.is_file() or not encoder_file.is_file():
            self._load_error = f"Weather risk model artifacts missing in {self.model_directory}"
            return

        try:
            self._model = joblib.load(model_file)
            self._encoder = joblib.load(encoder_file)
            self._feature_names = joblib.load(features_file) if features_file.is_file() else []
            self._is_loaded = True
            logger.info("Weather risk XGBoost model and encoder loaded successfully")
        except Exception as e:
            self._load_error = f"Failed to load weather risk model: {e}"
            logger.warning(self._load_error)

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and self._model is not None and self._encoder is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def predict(self, req: WeatherRiskRequest) -> WeatherRiskResponse:
        if not self.is_ready:
            raise RuntimeError(self._load_error or "Weather risk model is not loaded")

        month_str = MONTH_NAMES[req.month - 1]
        season_str = SEASON_MAP.get(req.season.lower().strip(), "Monsoon")
        state_code = STATE_ABBR_MAP.get(req.state.lower().strip(), "AP")

        min_t = req.min_temp_c if req.min_temp_c is not None else req.avg_temp_c - 3.5
        max_t = req.max_temp_c if req.max_temp_c is not None else req.avg_temp_c + 3.5
        day_of_year = int((req.month - 1) * 30.4 + 15)

        row_dict = {
            "month": month_str,
            "season": season_str,
            "state": state_code,
            "avg_temp": float(req.avg_temp_c),
            "min_temp": float(min_t),
            "max_temp": float(max_t),
            "wind_speed": float(req.wind_speed_kmh),
            "air_pressure": float(req.air_pressure_hpa),
            "elevation": 500.0,
            "latitude": 16.5,
            "longitude": 80.5,
            "previous_rainfall": float(req.rainfall_mm),
            "previous_avg_temp": float(req.avg_temp_c),
            "previous_wind_speed": float(req.wind_speed_kmh),
            "previous_pressure": float(req.air_pressure_hpa),
            "rainfall_3day": float(req.rainfall_mm * 1.5),
            "rainfall_7day": float(req.rainfall_mm * 2.5),
            "rainfall_3day_avg": float(req.rainfall_mm / 2.0),
            "rainfall_7day_avg": float(req.rainfall_mm / 3.0),
            "temp_3day_avg": float(req.avg_temp_c),
            "temp_7day_avg": float(req.avg_temp_c),
            "pressure_change": 0.0,
            "temp_change": 0.0,
            "wind_change": 0.0,
            "day_of_year": day_of_year,
            "month_sin": float(np.sin(2 * np.pi * req.month / 12)),
            "month_cos": float(np.cos(2 * np.pi * req.month / 12)),
        }

        df = pd.DataFrame([row_dict])[self._feature_names]

        pred_idx = self._model.predict(df)
        pred_label = str(self._encoder.inverse_transform(pred_idx)[0])
        probabilities = self._model.predict_proba(df)[0]

        prob_dict = {
            str(cls): round(float(prob), 4)
            for cls, prob in zip(self._encoder.classes_, probabilities)
        }
        confidence = prob_dict.get(pred_label, float(np.max(probabilities)))

        advisories = {
            "Low": "Normal agro-meteorological conditions expected. Standard agronomic schedule recommended.",
            "Moderate": "Moderate weather disturbance potential. Check field drainage and reinforce nursery covers.",
            "High": "High meteorological risk (excess rainfall or gale winds). Delay fertilizer/spray operations.",
            "Extreme": "Extreme agro-climatic hazard alert! Secure standing crops, clear excess drainage immediately.",
        }

        return WeatherRiskResponse(
            predicted_risk_level=pred_label,
            confidence=round(confidence, 4),
            class_probabilities=prob_dict,
            algorithm="XGBoost Classifier (multi:softprob, 27 features)",
            advisory=advisories.get(pred_label, "Follow local IMD district agro-meteorological bulletins."),
        )
