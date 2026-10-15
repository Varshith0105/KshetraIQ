"""Agricultural Sustainability & Carbon Footprint Scoring Service."""

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.schemas.prediction import SustainabilityRequest, SustainabilityResponse

logger = logging.getLogger(__name__)


class SustainabilityService:
    """Service for computing deterministic ICAR/Agriverse agronomic sustainability scores."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        self._config: dict[str, Any] = {}
        self._is_loaded = False
        self._load_error: str | None = None
        self._init_config()

    def _init_config(self) -> None:
        config_file = self.model_directory / "sustainability_score_config.pkl"
        if not config_file.is_file():
            self._load_error = f"Sustainability config missing at {config_file}"
            return

        try:
            self._config = joblib.load(config_file)
            self._is_loaded = True
            logger.info("Sustainability score config loaded successfully from %s", config_file)
        except Exception as e:
            self._load_error = f"Failed to load sustainability config: {e}"
            logger.warning(self._load_error)

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and bool(self._config)

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def calculate(self, req: SustainabilityRequest) -> SustainabilityResponse:
        if not self.is_ready:
            raise RuntimeError(self._load_error or "Sustainability config not loaded")

        cfg = self._config
        fert_per_ha = req.fertilizer_kg / req.area_hectares
        pest_per_ha = req.pesticide_kg / req.area_hectares
        prod_per_ha = req.yield_tonnes_per_ha

        # Fertilizer score: lower input is better for sustainability
        fert_range = cfg["fertilizer_max"] - cfg["fertilizer_min"]
        if fert_range > 0:
            fert_norm = (fert_per_ha - cfg["fertilizer_min"]) / fert_range
            fert_score = float(np.clip(100.0 * (1.0 - fert_norm), 0.0, 100.0))
        else:
            fert_score = 50.0

        # Pesticide score: lower input is better for eco-balance
        pest_range = cfg["pesticide_max"] - cfg["pesticide_min"]
        if pest_range > 0:
            pest_norm = (pest_per_ha - cfg["pesticide_min"]) / pest_range
            pest_score = float(np.clip(100.0 * (1.0 - pest_norm), 0.0, 100.0))
        else:
            pest_score = 50.0

        # Production efficiency: higher yield per unit land is better
        prod_range = cfg["production_max"] - cfg["production_min"]
        if prod_range > 0:
            prod_norm = (prod_per_ha - cfg["production_min"]) / prod_range
            prod_score = float(np.clip(100.0 * prod_norm, 0.0, 100.0))
        else:
            prod_score = 50.0

        w_fert = float(cfg.get("fertilizer_weight", 0.35))
        w_pest = float(cfg.get("pesticide_weight", 0.30))
        w_prod = float(cfg.get("production_weight", 0.35))

        total_score = float(np.clip(
            (w_fert * fert_score) + (w_pest * pest_score) + (w_prod * prod_score),
            0.0,
            100.0
        ))

        if total_score >= 60.0:
            category = "High Sustainability"
        elif total_score >= 30.0:
            category = "Moderate Sustainability"
        else:
            category = "Low Sustainability"

        notes = []
        if fert_score < 40.0:
            notes.append("High fertilizer loading detected. Integrate bio-fertilizers and green manuring.")
        if pest_score < 40.0:
            notes.append("Elevated chemical pesticide application. Transition to Integrated Pest Management (IPM).")
        if prod_score >= 70.0:
            notes.append("High biological production efficiency per cultivated hectare.")
        if not notes:
            notes.append("Farm agronomic inputs fall within sustainable ecological bounds.")

        return SustainabilityResponse(
            score=round(total_score, 2),
            category=category,
            fertilizer_score=round(fert_score, 2),
            pesticide_score=round(pest_score, 2),
            production_efficiency_score=round(prod_score, 2),
            weights={
                "fertilizer": w_fert,
                "pesticide": w_pest,
                "production_efficiency": w_prod,
            },
            advisory_notes=notes,
        )
