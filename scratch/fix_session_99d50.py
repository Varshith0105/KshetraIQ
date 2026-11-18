import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.intelligence_service import IntelligenceService

svc = IntelligenceService()
aid = "plant_99d50d5087794bae91e0e71a7bc5ab0f"
print(f"Executing models for {aid}...")

for m in ["sam", "lime", "blip", "florence"]:
    print(f"Running {m}...")
    svc.run_plant(aid, m, None)
    print(f"  {m} finished.")

svc._generate_composite_2x2(aid, None)
print("Composite finished. Session 99d50 fully completed!")
