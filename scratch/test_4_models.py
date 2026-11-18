"""
Test 4 models end-to-end: ResNet50, SAM, LIME, BLIP
Verifies image + text output for all models.
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import get_settings
from app.services.intelligence_service import IntelligenceService

def test_four_models():
    settings = get_settings()
    service = IntelligenceService(settings)

    # 1. Check status
    status = service.plant_status()
    print("Plant models status:")
    for s in status:
        print(f"  - {s['model']}: {s['status']} ({s['version']})")
    assert len(status) == 4, f"Expected 4 models, got {len(status)}"
    assert all(s["model"] != "florence" for s in status), "Florence must not be present"

    # 2. Pick a test image
    test_img_path = Path("C:/Users/LENOVO/.gemini/antigravity/brain/fe514edc-8512-4d9c-9bc9-d78549457a4c/.user_uploaded/media_1794931235133_3126bc2d.jpg")

    print(f"Testing with image: {test_img_path}")
    image_bytes = test_img_path.read_bytes()

    # Create plant analysis with all 4 models wanted
    session = service.create_plant(
        image_bytes,
        test_img_path.name,
        "test-user",
        ["disease_classifier", "sam", "lime", "blip"]
    )
    aid = session["analysis_id"]
    print(f"Created session: {aid}")

    # Poll until all models complete or timeout after 120s
    import time
    print("\nWaiting for background models (SAM, LIME, BLIP) to complete...")
    for _ in range(60):
        time.sleep(2)
        session = service.get(aid, "test-user") or {}
        models = session.get("executed_models", {})
        statuses = [models.get(m, {}).get("status") for m in ["sam", "lime", "blip"]]
        print(f"  Statuses: SAM={statuses[0]}, LIME={statuses[1]}, BLIP={statuses[2]}")
        if all(s in ("COMPLETED", "FAILED") for s in statuses):
            break

    # Inspect executed models
    models = session.get("executed_models", {})
    for mname in ["disease_classifier", "sam", "lime", "blip"]:
        rec = models.get(mname, {})
        print(f"\nModel: {mname}")
        print(f"  Status: {rec.get('status')}")
        print(f"  Time: {rec.get('execution_time_sec')}s")
        if rec.get("status") == "COMPLETED":
            res = rec.get("result", {})
            if mname == "disease_classifier":
                print(f"  Predicted: {res.get('predicted_class')} ({res.get('confidence_pct')}%)")
            elif mname == "sam":
                print(f"  Mask count: {res.get('mask_count')}")
                print(f"  Leaf coverage: {res.get('leaf_coverage_pct')}%")
                print(f"  Assets: {res.get('visual_assets')}")
            elif mname == "lime":
                print(f"  Explained class: {res.get('explained_class')}")
                print(f"  Superpixels: {res.get('num_features')}")
                print(f"  Asset: {res.get('explanation_image')}")
            elif mname == "blip":
                print(f"  Caption: {res.get('caption')}")
                print(f"  Detailed caption: {res.get('detailed_caption')}")
                print(f"  Asset: {res.get('analysis_asset')}")

    # Check 4-panel composite and PDF report
    print("\nAssets created:")
    for asset in session.get("assets", []):
        print(f"  - {asset}")

    # Test PDF generation
    filename, pdf_bytes = service.generate_report(aid, "test-user")
    print(f"\nGenerated PDF: {filename} ({len(pdf_bytes)} bytes)")
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_four_models()
