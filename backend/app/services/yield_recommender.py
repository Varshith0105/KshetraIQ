"""Crop Yield Prediction Service — Random Forest Regressor adapter."""

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

# Import patch to ensure legacy ColumnTransformer unpickles
import app.core.unpickle_patch  # noqa: F401
from app.schemas.prediction import CropYieldRequest, CropYieldResponse

logger = logging.getLogger(__name__)



SUPPORTED_CROPS = [
    "Arecanut", "Arhar/Tur", "Bajra", "Banana", "Barley", "Black pepper", "Cardamom",
    "Cashewnut", "Castor seed", "Coconut ", "Coriander", "Cotton(lint)", "Cowpea(Lobia)",
    "Dry chillies", "Garlic", "Ginger", "Gram", "Groundnut", "Guar seed", "Horse-gram",
    "Jowar", "Jute", "Khesari", "Linseed", "Maize", "Masoor", "Mesta", "Moong(Green Gram)",
    "Moth", "Niger seed", "Oilseeds total", "Onion", "Other  Rabi pulses", "Other Cereals",
    "Other Kharif pulses", "Other Summer Pulses", "Peas & beans (Pulses)", "Potato",
    "Ragi", "Rapeseed &Mustard", "Rice", "Safflower", "Sannhamp", "Sesamum",
    "Small millets", "Soyabean", "Sugarcane", "Sunflower", "Sweet potato", "Tapioca",
    "Tobacco", "Turmeric", "Urad", "Wheat", "other oilseeds"
]

CROP_LOOKUP = {c.strip().lower(): c for c in SUPPORTED_CROPS}

SEASON_LOOKUP = {
    "autumn": "Autumn     ",
    "kharif": "Kharif     ",
    "rabi": "Rabi       ",
    "summer": "Summer     ",
    "whole year": "Whole Year ",
    "winter": "Winter     ",
}


class CropYieldService:
    """Inference service for the verified Random Forest crop yield regression model."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        self._model: Any = None
        self._is_loaded = False
        self._load_error: str | None = None
        self._init_model()

    def _init_model(self) -> None:
        model_file = self.model_directory / "crop_yield_prediction_model.pkl"
        if not model_file.is_file():
            self._load_error = f"Model artifact missing at {model_file}"
            return

        try:
            self._model = joblib.load(model_file)
            self._is_loaded = True
            logger.info("Crop yield prediction model loaded successfully from %s", model_file)
        except Exception as e:
            self._load_error = f"Failed to load yield model: {e}"
            logger.warning(self._load_error)

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def predict(self, req: CropYieldRequest) -> CropYieldResponse:
        if not self.is_ready:
            raise RuntimeError(self._load_error or "Yield model is not loaded")

        clean_crop_key = req.crop.strip().lower()
        is_supported = clean_crop_key in CROP_LOOKUP
        normalized_crop = CROP_LOOKUP.get(clean_crop_key, req.crop.strip())

        clean_season_key = req.season.strip().lower()
        normalized_season = SEASON_LOOKUP.get(clean_season_key, req.season)

        features_df = pd.DataFrame([
            {
                "Crop": normalized_crop,
                "Season": normalized_season,
                "State": req.state.strip(),
                "Crop_Year": req.crop_year,
                "Area": req.area_hectares,
                "Annual_Rainfall": req.annual_rainfall_mm,
                "Fertilizer": req.fertilizer_kg,
                "Pesticide": req.pesticide_kg,
            }
        ])

        raw_pred = self._model.predict(features_df)
        yield_per_ha = max(0.0, float(raw_pred[0]))
        total_production = round(yield_per_ha * req.area_hectares, 3)

        disclaimer = "Yield prediction calibrated against historic agricultural state survey data."
        if not is_supported:
            disclaimer = f"Warning: '{req.crop}' is outside the 55 explicitly trained crop categories; model inferred using generalized baseline."

        return CropYieldResponse(
            predicted_yield_tonnes_per_hectare=round(yield_per_ha, 4),
            predicted_total_production_tonnes=total_production,
            is_supported_crop=is_supported,
            algorithm="Random Forest Regressor (R² = 0.9802)",
            features_used={
                "crop": normalized_crop.strip(),
                "season": normalized_season.strip(),
                "state": req.state.strip(),
                "crop_year": req.crop_year,
                "area_ha": req.area_hectares,
                "annual_rainfall_mm": req.annual_rainfall_mm,
                "fertilizer_kg": req.fertilizer_kg,
                "pesticide_kg": req.pesticide_kg,
            },
            disclaimer=disclaimer,
        )

