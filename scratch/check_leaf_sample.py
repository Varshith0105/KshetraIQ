import sys
sys.path.insert(0, "backend")
from pathlib import Path
from app.services.plant_disease_service import plant_disease_service

img_bytes = Path("scratch/sample_tomato_leaf.jpg").read_bytes()
res = plant_disease_service.predict_image(img_bytes, "sample_tomato_leaf.jpg")
print("Prediction on scratch/sample_tomato_leaf.jpg:")
print("Predicted Class:", res["predicted_class"])
print("Confidence:", res["confidence_pct"], "%")
print("Top 3:", res["top_3_candidates"])
print("Telugu:", res["label_te"])
print("Mitigation:", res["recommended_mitigation"])
