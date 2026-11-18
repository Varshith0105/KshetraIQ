import os
import sys
import time

# Ensure offline mode so transformers doesn't stall on blocked network calls
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

sys.path.insert(0, "backend")

from pathlib import Path
from PIL import Image
from app.services.intelligence_service import IntelligenceService
from app.services.plant_disease_service import plant_disease_service

print("=== 1. Inspecting Plant Disease Artifacts ===", flush=True)
audit = plant_disease_service.inspect_artifacts()
print("Artifact audit:", audit, flush=True)

svc = IntelligenceService()

print("\n=== 2. Checking Model Readiness Statuses ===", flush=True)
plant_st = svc.plant_status()
print("Plant models status:")
for m in plant_st:
    print(f"  - {m['model']}: status={m['status']}, live={m.get('is_live')}, reason={m.get('reason')}")

sat_st = svc.satellite_status()
print("\nSatellite status:")
for m in sat_st:
    print(f"  - {m['model']}: status={m['status']}, live={m.get('is_live')}, reason={m.get('reason')}")

print("\n=== 3. Running Full Integrated Plant Intelligence Pipeline ===", flush=True)
# Load test image
test_img_path = Path(".uploads/intelligence/plant_25218beecdee4310958e5a5135cb00ce/original.jpg")
if not test_img_path.exists():
    # Fallback to any existing image
    imgs = list(Path(".uploads").glob("**/*.jpg"))
    test_img_path = imgs[0]
print(f"Using test leaf image: {test_img_path} ({test_img_path.stat().st_size} bytes)", flush=True)

img_bytes = test_img_path.read_bytes()

t0 = time.time()
manifest = svc.create_plant(
    content=img_bytes,
    filename="tomato_leaf_test.jpg",
    user_id="test-user-verification",
)
total_time = time.time() - t0
print(f"\nPipeline finished in {total_time:.2f}s!", flush=True)
print(f"Analysis ID: {manifest['analysis_id']}", flush=True)

print("\n--- Model Execution Results ---")
for model_name, exec_data in manifest["executed_models"].items():
    st = exec_data.get("status")
    runtime = exec_data.get("execution_time_sec")
    res = exec_data.get("result")
    err = exec_data.get("error")
    assets = exec_data.get("visual_assets", [])
    print(f"\n[{model_name.upper()}] Status: {st} ({runtime}s)")
    if err:
        print(f"  Error: {err}")
    if res:
        if model_name == "disease_classifier":
            print(f"  Predicted: {res.get('predicted_class')} ({res.get('confidence_pct')}%)")
            print(f"  Telugu: {res.get('label_te')}")
            print(f"  Active Artifact: {res.get('active_artifact')}")
            print(f"  Mitigation: {res.get('recommended_mitigation')}")
        elif model_name == "sam":
            print(f"  Mask count: {res.get('mask_count')}")
            print(f"  Leaf coverage: {res.get('leaf_coverage_pct')}%")
            print(f"  Assets: {assets}")
        elif model_name == "lime":
            print(f"  Explained class: {res.get('explained_class')}")
            print(f"  Interpretation: {res.get('interpretation')}")
            print(f"  Assets: {assets}")
        elif model_name == "blip":
            print(f"  Caption: {res.get('caption')}")
        elif model_name == "florence":
            print(f"  Brief Caption: {res.get('caption')}")
            print(f"  Detailed Caption: {res.get('detailed_caption')}")

print("\n--- 2x2 Composite Visualization ---")
comp = manifest.get("composite_2x2")
print(f"Composite 2x2 path: {comp}")
print(f"Composite file exists: {Path(comp).exists() if comp else False}")

print("\n=== 4. Testing PDF Report Generation ===", flush=True)
rec, pdf_bytes = svc.generate_report(manifest["analysis_id"], user_id="test-user-verification")
print(f"PDF Report generated: {rec['path']} ({len(pdf_bytes)} bytes)")
print("PDF file exists:", Path(rec["path"]).exists())

print("\n=== 5. Testing Chatbot Context Tool ===", flush=True)
wf, ctx = svc.chatbot_tool("What did each model find on the tomato leaf?", user_id="test-user-verification", analysis_id=manifest["analysis_id"])
print(f"Chatbot workflow: {wf}")
print("Chatbot context preview:\n", ctx[:300], "...")

print("\nALL INFERENCE TESTS COMPLETE.")
