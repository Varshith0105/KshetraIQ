import urllib.request
import urllib.parse
import json
import mimetypes
import uuid
from pathlib import Path

# Build multipart form data
boundary = uuid.uuid4().hex
img_path = Path("scratch/sample_tomato_leaf.jpg")
img_data = img_path.read_bytes()

body = bytearray()
body.extend(f"--{boundary}\r\n".encode())
body.extend(f'Content-Disposition: form-data; name="file"; filename="{img_path.name}"\r\n'.encode())
body.extend(b"Content-Type: image/jpeg\r\n\r\n")
body.extend(img_data)
body.extend(b"\r\n")
body.extend(f"--{boundary}--\r\n".encode())

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/plant-intelligence/analyze",
    data=bytes(body),
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "KshetraIQ-Test/1.0"
    },
    method="POST"
)

print("Dispatching live analysis request to http://127.0.0.1:8000/api/plant-intelligence/analyze ...")
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
        print("Analysis completed successfully!")
        print("Analysis ID:", data.get("analysis_id"))
        print("Composite 2x2:", data.get("composite_2x2"))
        print("\nModel Statuses:")
        for m, d in data.get("executed_models", {}).items():
            print(f"  - {m}: status={d.get('status')}, runtime={d.get('execution_time_sec')}s, visual_assets={d.get('visual_assets')}")
            if m == "disease_classifier":
                print(f"    Diagnosis: {d.get('result', {}).get('predicted_class')} ({d.get('result', {}).get('confidence_pct')}%)")
            elif m == "sam":
                print(f"    SAM: {d.get('result', {}).get('mask_count')} masks, {d.get('result', {}).get('leaf_coverage_pct')}% coverage")
            elif m == "lime":
                print(f"    LIME: Explained {d.get('result', {}).get('explained_class')}")
            elif m == "blip":
                print(f"    BLIP: \"{d.get('result', {}).get('caption')}\"")
            elif m == "florence":
                print(f"    Florence: \"{d.get('result', {}).get('caption')}\"")
                print(f"    Detailed: \"{d.get('result', {}).get('detailed_caption')}\"")
except Exception as e:
    print("Error calling live analyze:", e)
    if hasattr(e, 'read'):
        print("Response body:", e.read().decode())
