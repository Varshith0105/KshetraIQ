import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import get_settings
from app.services.auth_service import AuthService
from app.services.soil_health_service import soil_health_service
from app.schemas.assessment import SoilHealthScoreRequest

# Test directly
req = SoilHealthScoreRequest(nitrogen=350, phosphorus=18, potassium=200, ph=6.8)
score_dict = soil_health_service.assess(req.model_dump(exclude_none=True))
print("Soil calculation test:", score_dict["score"], score_dict["category"], score_dict["badge_color"])
assert score_dict["score"] == 100.0
assert score_dict["category"] == "Excellent"

# Test deficient
req_def = SoilHealthScoreRequest(nitrogen=70, phosphorus=6, potassium=60, ph=5.5)
score_def = soil_health_service.assess(req_def.model_dump(exclude_none=True))
print("Deficient test:", score_def["score"], score_def["category"], score_def["badge_color"])
assert score_def["category"] in ["Poor", "Moderate"]
assert len(score_def["recommendations"]) > 0
print("Recommendations count:", len(score_def["recommendations"]))
print("ALL TESTS PASSED")
