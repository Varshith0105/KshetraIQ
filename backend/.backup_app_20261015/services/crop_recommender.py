import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.schemas.assessment import CropCandidate, CropPredictionDetail

logger = logging.getLogger(__name__)

CROP_NAMES_TE: dict[str, str] = {
    "apple": "ఆపిల్ (Apple)",
    "banana": "అరటి (Banana)",
    "blackgram": "మినుములు (Black gram)",
    "chickpea": "శనగలు (Chickpea)",
    "coconut": "కొబ్బరి (Coconut)",
    "coffee": "కాఫీ (Coffee)",
    "cotton": "పత్తి (Cotton)",
    "grapes": "ద్రాక్ష (Grapes)",
    "jute": "జనపనార (Jute)",
    "kidneybeans": "రాజ్మా (Kidney beans)",
    "lentil": "మసూర్ పప్పు (Lentil)",
    "maize": "మొక్కజొన్న (Maize)",
    "mango": "మామిడి (Mango)",
    "mothbeans": "బొబ్బర్లు / మినుములు (Moth beans)",
    "mungbean": "పెసలు (Mung bean)",
    "muskmelon": "ఖర్బూజా (Muskmelon)",
    "orange": "నారింజ / కమలా (Orange)",
    "papaya": "బొప్పాయి (Papaya)",
    "pigeonpeas": "కందులు (Pigeon peas / Red gram)",
    "pomegranate": "దానిమ్మ (Pomegranate)",
    "rice": "వరి (Rice / Paddy)",
    "watermelon": "పుచ్చకాయ (Watermelon)",
}


class CropRecommender:
    """Verified adapter for the trained Random Forest crop recommendation model."""

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = model_directory
        self._model: Any = None
        self._feature_names: list[str] = []
        self._classes: list[str] = []
        self._is_loaded = False
        self._load_error: str | None = None
        self._init_model()

    def _init_model(self) -> None:
        model_file = self.model_directory / "crop_recommendation_model.pkl"
        features_file = self.model_directory / "crop_feature_names.pkl"

        if not model_file.is_file():
            self._load_error = f"Model artifact missing at {model_file}"
            return

        try:
            self._model = joblib.load(model_file)
            if features_file.is_file():
                self._feature_names = list(joblib.load(features_file))
            else:
                self._feature_names = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

            if hasattr(self._model, "classes_"):
                self._classes = list(self._model.classes_)
            self._is_loaded = True
            logger.info("Successfully loaded crop recommendation model with %d classes", len(self._classes))
        except Exception as exc:
            self._load_error = f"Failed to deserialize crop model: {exc}"
            logger.exception("Model loading error")

    @property
    def is_available(self) -> bool:
        return self._is_loaded and self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def predict(
        self,
        n: float,
        p: float,
        k: float,
        temperature: float,
        humidity: float,
        ph: float,
        rainfall: float,
    ) -> CropPredictionDetail:
        if not self.is_available:
            raise RuntimeError(self._load_error or "Crop recommendation model is not loaded.")

        input_data = pd.DataFrame(
            [[n, p, k, temperature, humidity, ph, rainfall]],
            columns=self._feature_names,
        )

        pred_label = self._model.predict(input_data)[0]
        probs = self._model.predict_proba(input_data)[0]

        top_indices = np.argsort(probs)[::-1][:4]
        candidates: list[CropCandidate] = []
        for idx in top_indices:
            crop_name = str(self._classes[idx])
            crop_conf = float(probs[idx])
            if crop_conf > 0.001 or len(candidates) < 2:
                candidates.append(
                    CropCandidate(
                        crop=crop_name,
                        crop_te=CROP_NAMES_TE.get(crop_name, crop_name),
                        confidence=round(crop_conf, 4),
                    )
                )

        main_confidence = round(float(np.max(probs)), 4)

        return CropPredictionDetail(
            recommended_crop=str(pred_label),
            recommended_crop_te=CROP_NAMES_TE.get(str(pred_label), str(pred_label)),
            confidence=main_confidence,
            top_candidates=candidates,
            features_used={
                "N": float(n),
                "P": float(p),
                "K": float(k),
                "temperature": float(temperature),
                "humidity": float(humidity),
                "ph": float(ph),
                "rainfall": float(rainfall),
            },
            model_id="crop-recommendation-v1",
            algorithm="RandomForestClassifier (200 estimators)",
            artifact_name="crop_recommendation_model.pkl",
        )
