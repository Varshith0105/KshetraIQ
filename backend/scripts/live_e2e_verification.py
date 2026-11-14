import secrets
import requests

BASE_URL = "http://127.0.0.1:8000"

print("=====================================================================")
print("          KSHETRAIQ LIVE END-TO-END FLOW VERIFICATION")
print("=====================================================================")

# 1. Register a test farmer
email = f"farmer_{secrets.token_hex(4)}@kshetraiq.in"
pw = "SecureFarmerPass123!"
reg_resp = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
    "email": email,
    "full_name": "Sita Ramaraju",
    "password": pw,
    "confirm_password": pw
})
assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
token = reg_resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"[1/5 PASS] Farmer Registered & Authenticated: {email}")

# 2. Submit Farm Assessment
assess_resp = requests.post(f"{BASE_URL}/api/v1/assessments", headers=headers, json={
    "farm_name": "Rythu Mitra Model Farm",
    "district": "Guntur",
    "state": "Andhra Pradesh",
    "acreage": 3.0,
    "irrigation_type": "Drip",
    "water_availability": "Borewell",
    "season": "Kharif",
    "soil": {"nitrogen_kg_ha": 120.0, "phosphorus_kg_ha": 35.0, "potassium_kg_ha": 180.0, "ph": 6.7},
    "weather": {"temperature_c": 28.5, "humidity_percent": 75.0, "rainfall_mm": 680.0},
    "previous_crops": ["cotton"],
    "language": "en"
})
assert assess_resp.status_code == 201, f"Assessment failed: {assess_resp.text}"
assess_data = assess_resp.json()
assess_id = assess_data["assessment_id"]
crop_pred = next(r for r in assess_data["results"] if r["model_id"] == "crop-recommendation-v1")
print(f"[2/5 PASS] Assessment Created: ID={assess_id}")
print(f"           Recommended Crop: {crop_pred['prediction']['recommended_crop'].upper()} ({crop_pred['prediction']['confidence']:.1%})")

# 3. Chat with AgriVerse-AI Multi-Agent Chatbot
chat_resp = requests.post(f"{BASE_URL}/api/v1/chat", headers=headers, json={
    "message": "What is the recommended spacing for cotton sowing and which pests affect it?",
    "language": "en",
    "assessment_id": assess_id
})
assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
chat_data = chat_resp.json()
print(f"[3/5 PASS] AgriVerse-AI Chat Response ({chat_data['provider']}):")
print(f"           \"{chat_data['reply'][:120]}...\"")

# 4. Preview PDF Report
prev_resp = requests.get(f"{BASE_URL}/api/v1/assessments/{assess_id}/report/preview", headers=headers)
assert prev_resp.status_code == 200, f"Preview failed: {prev_resp.text}"
print(f"[4/5 PASS] PDF Report Preview Verified for: {prev_resp.json()['farm_name']}")

# 5. Download Formal PDF Dossier
pdf_resp = requests.post(f"{BASE_URL}/api/v1/assessments/{assess_id}/report/confirm", headers=headers)
assert pdf_resp.status_code == 200, f"PDF failed: {pdf_resp.text}"
assert pdf_resp.headers["content-type"] == "application/pdf"
assert b"BLOCKED" not in pdf_resp.content, "PDF contains BLOCKED!"
print(f"[5/5 PASS] Farmer PDF Generated & Downloaded: {len(pdf_resp.content)} bytes (Clean, Zero BLOCKED messages)")

print("=====================================================================")
print("           ALL 5 LIVE END-TO-END FLOWS FULLY VERIFIED")
print("=====================================================================")

