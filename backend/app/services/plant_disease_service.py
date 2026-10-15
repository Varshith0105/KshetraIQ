"""KshetraIQ Plant Disease Vision Classifier Service.

Audited and integrated using capstone-final/plant_disease.h5 (ResNet50 backbone, 23 classes).
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Verified 23 class names from capstone-final/resnet50_confusion_matrix.png
# and capstone-final/main_file_capstone(1).ipynb training generator
PLANT_DISEASE_CLASSES: list[str] = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Pepper__bell___Bacterial_spot",
    "Pepper__bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Tomato_Bacterial_spot",
    "Tomato_Early_blight",
    "Tomato_Late_blight",
    "Tomato_Leaf_Mold",
    "Tomato_Septoria_leaf_spot",
    "Tomato_Spider_mites_Two_spotted_spider_mite",
    "Tomato__Target_Spot",
    "Tomato__Tomato_YellowLeaf__Curl_Virus",
    "Tomato__Tomato_mosaic_virus",
    "Tomato_healthy",
]

# Telugu translations and actionable agronomic mitigations
DISEASE_METADATA: dict[str, dict[str, str]] = {
    "Apple___Apple_scab": {
        "te": "యాపిల్ స్కాబ్ తెగులు",
        "action": "Spray Mancozeb (0.25%) or Captan. Remove fallen infected leaves."
    },
    "Apple___Black_rot": {
        "te": "యాపిల్ నల్ల కుళ్ళు తెగులు",
        "action": "Prune infected cankers during dry weather; apply copper fungicides."
    },
    "Apple___Cedar_apple_rust": {
        "te": "యాపిల్ సెడార్ రస్ట్ తెగులు",
        "action": "Apply Myclobutanil or Chlorothalonil early in growing season."
    },
    "Apple___healthy": {
        "te": "ఆరోగ్యకరమైన యాపిల్ ఆకు",
        "action": "Maintain routine balanced nutrition and proper spacing."
    },
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "te": "మొక్కజొన్న బూడిద రంగు ఆకుమచ్చ తెగులు",
        "action": "Spray Azoxystrobin + Difenoconazole; avoid overhead sprinkler wetting."
    },
    "Corn_(maize)___Common_rust_": {
        "te": "మొక్కజొన్న సాధారణ రస్ట్ తెగులు",
        "action": "Apply Mancozeb 75% WP @ 2g/L or propiconazole at first sign of pustules."
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "te": "మొక్కజొన్న ఉత్తర ఆకు ఎండు తెగులు",
        "action": "Apply Mancozeb or Zineb; ensure crop rotation with non-host legumes."
    },
    "Corn_(maize)___healthy": {
        "te": "ఆరోగ్యకరమైన మొక్కజొన్న ఆకు",
        "action": "Maintain optimal nitrogen scheduling and weed control."
    },
    "Pepper__bell___Bacterial_spot": {
        "te": "బెల్ పెప్పర్ బ్యాక్టీరియల్ మచ్చ తెగులు",
        "action": "Spray Copper oxychloride (2.5 g/L) + Streptocycline (0.1 g/L)."
    },
    "Pepper__bell___healthy": {
        "te": "ఆరోగ్యకరమైన మిరప ఆకు",
        "action": "Continue recommended irrigation and pest monitoring."
    },
    "Potato___Early_blight": {
        "te": "బంగాళాదుంప ముందస్తు ఎండు తెగులు (ఆల్టర్నేరియా)",
        "action": "Spray Mancozeb 75 WP (2.5g/L) or Chlorothalonil before canopy closure."
    },
    "Potato___Late_blight": {
        "te": "బంగాళాదుంప లేట్ బ్లైట్ తెగులు (ఫైటోఫ్తోరా)",
        "action": "Urgent: Spray Metalaxyl + Mancozeb (2.5g/L) or Cymoxanil; destroy infected tubers."
    },
    "Potato___healthy": {
        "te": "ఆరోగ్యకరమైన బంగాళాదుంప ఆకు",
        "action": "Maintain earthing up and preventative fungicide schedule during humid periods."
    },
    "Tomato_Bacterial_spot": {
        "te": "టమోటా బ్యాక్టీరియా మచ్చ తెగులు",
        "action": "Spray Copper hydroxide (2g/L) mixed with Streptomycin sulphate."
    },
    "Tomato_Early_blight": {
        "te": "టమోటా ముందస్తు ఆకు ఎండు తెగులు",
        "action": "Remove lower diseased foliage; apply Mancozeb (2g/L) or Difenoconazole."
    },
    "Tomato_Late_blight": {
        "te": "టమోటా లేట్ బ్లైట్ తెగులు",
        "action": "Apply Dimethomorph (1g/L) or Metalaxyl; avoid waterlogging around stem base."
    },
    "Tomato_Leaf_Mold": {
        "te": "టమోటా ఆకు బూజు తెగులు",
        "action": "Improve greenhouse airflow; spray Carbendazim or Copper fungicides."
    },
    "Tomato_Septoria_leaf_spot": {
        "te": "టమోటా సెప్టోరియా ఆకుమచ్చ తెగులు",
        "action": "Apply Chlorothalonil or Azoxystrobin; mulch soil to prevent rain splash."
    },
    "Tomato_Spider_mites_Two_spotted_spider_mite": {
        "te": "టమోటా రెండు మచ్చల ఎర్ర నల్లి",
        "action": "Spray Spiromesifen (1ml/L) or Dicofol; ensure undersides of leaves are covered."
    },
    "Tomato__Target_Spot": {
        "te": "టమోటా టార్గెట్ స్పాట్ తెగులు",
        "action": "Apply Pyraclostrobin or Boscalid; maintain adequate plant spacing."
    },
    "Tomato__Tomato_YellowLeaf__Curl_Virus": {
        "te": "టమోటా ఆకు ముడుత తెగులు (జెమినీ వైరస్)",
        "action": "Control whitefly vectors using Acetamiprid or Imidacloprid (0.3ml/L) and yellow sticky traps."
    },
    "Tomato__Tomato_mosaic_virus": {
        "te": "టమోటా మొజాయిక్ వైరస్",
        "action": "Sanitize pruning tools with 10% trisodium phosphate; rogue out infected plants."
    },
    "Tomato_healthy": {
        "te": "ఆరోగ్యకరమైన టమోటా ఆకు",
        "action": "Maintain drip fertigation and routine prophylactic biopesticide sprays."
    },
}


class PlantDiseaseService:
    """Inference service for foliar crop leaf disease screening."""

    def __init__(self, artifact_path: Path | None = None) -> None:
        self.artifact_path = artifact_path or (
            Path(__file__).resolve().parents[3] / "capstone-final" / "plant_disease.h5"
        )
        self._model: Any = None
        self._load_error: str | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if self._load_error:
            raise RuntimeError(f"Plant disease model unavailable: {self._load_error}")

        if not self.artifact_path.exists():
            self._load_error = f"Artifact not found at {self.artifact_path}"
            raise FileNotFoundError(self._load_error)

        try:
            import keras

            logger.info("Loading plant disease vision model from %s", self.artifact_path)
            self._model = keras.models.load_model(str(self.artifact_path), compile=False)
            logger.info("Successfully loaded plant disease vision model.")
        except Exception as e:
            self._load_error = f"Failed to load Keras model: {e}"
            logger.exception("Plant disease model loading failed: %s", e)
            raise RuntimeError(self._load_error) from e

    def is_available(self) -> bool:
        """Check if model artifact exists and can be loaded."""
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False

    def predict_image(self, image_bytes: bytes, filename: str = "upload.jpg") -> dict[str, Any]:
        """Preprocess uploaded leaf photograph and run deep CNN inference."""
        self._ensure_loaded()

        if not image_bytes or len(image_bytes) < 100:
            raise ValueError("Empty or invalid image payload")

        if len(image_bytes) > 10 * 1024 * 1024:
            raise ValueError("Uploaded image exceeds the maximum 10MB limit")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Verify file format
            if image.format not in ("JPEG", "PNG", "WEBP", "MPO"):
                raise ValueError(f"Unsupported image format: {image.format}. Please upload JPEG, PNG, or WEBP.")
            if image.width < 32 or image.height < 32:
                raise ValueError("Image dimensions too small (minimum 32x32 pixels required).")
            image = image.convert("RGB")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Invalid or corrupted image format: {e}") from e

        # Model input shape is (160, 160, 3)
        resized = image.resize((160, 160), Image.Resampling.BILINEAR)
        img_array = np.array(resized, dtype=np.float32)

        # Batch dimension: (1, 160, 160, 3)
        batch = np.expand_dims(img_array, axis=0)

        # Run inference
        probs = self._model.predict(batch, verbose=0)[0]
        top_idx = int(np.argmax(probs))
        top_class = PLANT_DISEASE_CLASSES[top_idx]
        confidence = float(probs[top_idx])

        # Top 3 candidates
        top_indices = np.argsort(probs)[::-1][:3]
        top_candidates = []
        for idx in top_indices:
            cls_name = PLANT_DISEASE_CLASSES[idx]
            meta = DISEASE_METADATA.get(cls_name, {})
            top_candidates.append({
                "class_name": cls_name,
                "label_te": meta.get("te", cls_name),
                "confidence": round(float(probs[idx]) * 100, 2),
                "mitigation": meta.get("action", "")
            })

        meta_top = DISEASE_METADATA.get(top_class, {})
        is_healthy = "healthy" in top_class.lower()
        is_low_confidence = confidence < 0.35
        warning = None
        if is_low_confidence:
            warning = (
                f"Confidence ({round(confidence * 100, 1)}%) is below standard diagnostic certainty (35%). "
                "The uploaded image may not clearly depict leaf tissue from the 5 supported crops "
                "(Apple, Corn/Maize, Bell Pepper, Potato, Tomato) or lighting/blur affects classification."
            )

        return {
            "model_id": "plant-disease-v1",
            "model_architecture": "ResNet50 + GlobalAveragePooling2D + Dense(128) + Dense(23)",
            "predicted_class": top_class,
            "label_te": meta_top.get("te", top_class),
            "confidence_pct": round(confidence * 100, 2),
            "is_healthy": is_healthy,
            "is_low_confidence": is_low_confidence,
            "warning": warning,
            "recommended_mitigation": meta_top.get("action", "Consult local Krishi Vigyan Kendra (KVK) agronomist."),
            "top_candidates": top_candidates,
            "supported_crops": ["Apple", "Corn (Maize)", "Bell Pepper", "Potato", "Tomato"],
            "filename": filename,
            "disclaimer": "Automated screening assistance only. Image predictions do not constitute a guaranteed professional laboratory diagnosis. Confirm critical symptoms with an authorized agricultural officer."
        }


# Singleton service
plant_disease_service = PlantDiseaseService()
