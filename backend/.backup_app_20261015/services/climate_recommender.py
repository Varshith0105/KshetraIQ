"""Climate Change Scenario Analysis Service."""

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

import app.core.unpickle_patch  # noqa: F401
from app.schemas.prediction import ClimateScenarioRequest, ClimateScenarioResponse

logger = logging.getLogger(__name__)


class ClimateScenarioService:
    """Inference service for assessing crop yield sensitivity to simulated rainfall shocks."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        self._model: Any = None
        self._is_loaded = False
        self._load_error: str | None = None
        self._init_model()

    def _init_model(self) -> None:
        model_file = self.model_directory / "climate_change_yield_model.pkl"
        if not model_file.is_file():
            self._load_error = f"Climate model artifact missing at {model_file}"
            return

        try:
            self._model = joblib.load(model_file)
            self._is_loaded = True
            logger.info("Climate change scenario model loaded successfully from %s", model_file)
        except Exception as e:
            self._load_error = f"Failed to load climate scenario model: {e}"
            logger.warning(self._load_error)

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def predict(self, req: ClimateScenarioRequest) -> ClimateScenarioResponse:
        if not self.is_ready:
            raise RuntimeError(self._load_error or "Climate model is not loaded")

        baseline_df = pd.DataFrame([
            {
                "Crop": req.crop,
                "Crop_Year": req.crop_year,
                "Season": req.season,
                "State": req.state,
                "Annual_Rainfall": req.baseline_rainfall_mm,
            }
        ])

        base_yield = max(0.01, float(self._model.predict(baseline_df)[0]))

        # Moderate shock: -10% rainfall deficit
        moderate_df = baseline_df.copy()
        moderate_df["Annual_Rainfall"] = req.baseline_rainfall_mm * 0.90
        mod_yield = max(0.0, float(self._model.predict(moderate_df)[0]))
        mod_change = ((mod_yield - base_yield) / base_yield) * 100.0

        # Severe shock: -25% drought rainfall deficit
        severe_df = baseline_df.copy()
        severe_df["Annual_Rainfall"] = req.baseline_rainfall_mm * 0.75
        sev_yield = max(0.0, float(self._model.predict(severe_df)[0]))
        sev_change = ((sev_yield - base_yield) / base_yield) * 100.0

        # Vulnerability assessment
        if sev_change < -20.0:
            tier = "High Vulnerability (Severe Drought Sensitivity)"
            rec = "Consider micro-irrigation systems, farm ponds, or drought-tolerant varieties."
        elif sev_change < -10.0:
            tier = "Moderate Vulnerability (Buffer Capable)"
            rec = "Implement soil mulching and moisture conservation practices to buffer moderate deficit."
        else:
            tier = "Low Vulnerability (Climate Resilient)"
            rec = "Crop displays resilient yield response under simulated moisture variation."

        return ClimateScenarioResponse(
            crop=req.crop,
            baseline_rainfall_mm=req.baseline_rainfall_mm,
            baseline_yield_tonnes_per_ha=round(base_yield, 4),
            moderate_shock_yield_tonnes_per_ha=round(mod_yield, 4),
            moderate_change_percent=round(mod_change, 2),
            severe_shock_yield_tonnes_per_ha=round(sev_yield, 4),
            severe_change_percent=round(sev_change, 2),
            vulnerability_tier=tier,
            recommendation=rec,
            algorithm="Random Forest Climate Scenario Regressor",
        )
