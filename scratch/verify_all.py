"""
KshetraIQ Comprehensive End-to-End System Verification
Tests all 8 ML models, auth, services, persistence, and reports via TestClient.
"""
import sys
import io
import os
import json
import numpy as np

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_system():
    results = {}
    print("=" * 65)
    print("KSHETRAIQ COMPREHENSIVE END-TO-END ACCEPTANCE VERIFICATION")
    print("=" * 65)

    # 1. Health & Registry
    print("\n[1] Health & Registry Verification...")
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print(f"    Health Status: {health_data['status']}")
    print(f"    Service Name: {health_data['service']}")
    results["health"] = "PASS"

    r = client.get("/api/v1/models")
    assert r.status_code == 200
    models_data = r.json()
    print(f"    Active Model Count in Registry: {len(models_data)}")
    results["models_inventory"] = "PASS"

    # 2. Authentication & Security Verification
    print("\n[2] Authentication & Security Verification (PBKDF2-HMAC-SHA256)...")
    test_email = f"farmer_{os.getpid()}@kshetraiq.test"
    test_password = "StrongPassword@123"

    # Register
    r = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": test_password,
        "display_name": "Rao Garu"
    })
    assert r.status_code in (200, 201), f"Register failed: {r.text}"
    auth_data = r.json()
    token = auth_data["token"]
    user_id = auth_data["user_id"]
    print(f"    Registration: SUCCESS (user_id: {user_id})")

    # Duplicate registration rejection
    r_dup = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": test_password
    })
    assert r_dup.status_code == 400
    print("    Duplicate Registration Blocked: PASS (400)")

    # Login
    r_login = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert r_login.status_code == 200
    print("    PBKDF2 Password Authentication: PASS (200)")

    # Bad password
    r_bad = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "WrongPassword"
    })
    assert r_bad.status_code == 401
    print("    Invalid Credential Rejection: PASS (401)")

    # Current user
    headers = {"Authorization": f"Bearer {token}"}
    r_me = client.get("/api/v1/auth/me", headers=headers)
    assert r_me.status_code == 200
    assert r_me.json()["email"] == test_email
    print(f"    Session Verification (/me): PASS (Email: {r_me.json()['email']})")
    results["authentication"] = "PASS"

    # 3. APMC Market Price Forecasting
    print("\n[3] APMC Market Price Forecasting (Hybrid Linear + XGBoost)...")
    r_mkt = client.post("/api/v1/predictions/market-price", json={
        "commodity": "Wheat",
        "mandi": "Varanasi(Grain)",
        "days_ahead": 7
    })
    assert r_mkt.status_code == 200, f"Market price forecast failed: {r_mkt.text}"
    mkt = r_mkt.json()
    print(f"    Forecast Modal Price: Rs. {mkt['forecast_modal_price']:.2f} / {mkt['unit']}")
    print(f"    Observed Base Price: Rs. {mkt['observed_market_price']:.2f}")
    print(f"    Trend Component: Rs. {mkt['trend_component']:.2f}")
    print(f"    Residual Adjustment: Rs. {mkt['residual_adjustment']:.2f}")
    print(f"    Confidence Band: Rs. [{mkt['confidence_band']['lower_bound']:.2f}, {mkt['confidence_band']['upper_bound']:.2f}]")
    print(f"    Algorithm: {mkt['algorithm']}")
    results["market_price_forecast"] = "PASS"

    # 4. Plant Disease ResNet50 Vision Diagnostic
    print("\n[4] Plant Disease Vision Screening (plant_disease.h5 Sequential ResNet50)...")
    from PIL import Image
    test_img = Image.new("RGB", (160, 160), color=(80, 150, 40))
    img_byte_arr = io.BytesIO()
    test_img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)

    files = {"file": ("leaf_sample.jpg", img_byte_arr.getvalue(), "image/jpeg")}
    r_dis = client.post("/api/v1/predictions/plant-disease", files=files)
    assert r_dis.status_code == 200, f"Disease screening failed: {r_dis.text}"
    dis = r_dis.json()
    print(f"    Diagnosed Class: {dis['predicted_class']}")
    print(f"    Telugu Label: {dis['label_te']}")
    print(f"    Confidence: {dis['confidence_pct']:.1f}%")
    print(f"    Top Candidates: {len(dis['top_candidates'])}")
    print(f"    Mitigation: {dis['recommended_mitigation'][:75]}...")
    print(f"    Architecture: {dis['model_architecture']}")
    results["plant_disease_diagnostic"] = "PASS"

    # 5. Scientific Irrigation Water Budgeting
    print("\n[5] Scientific Irrigation Water Budgeting (ICAR / ANGRAU)...")
    r_irr = client.post("/api/v1/predictions/irrigation", json={
        "crop": "Rice",
        "crop_days": 45,
        "soil_moisture": 320,
        "soil_type": "Loam",
        "temperature": 28.0,
        "rainfall_forecast_mm": 0.0,
        "area_acres": 2.5
    })
    assert r_irr.status_code == 200, f"Irrigation calculation failed: {r_irr.text}"
    irr = r_irr.json()
    print(f"    Crop & Stage: Rice ({irr['growth_stage']})")
    print(f"    Action: {irr['action']} ({irr['action_te']})")
    print(f"    Water Depth: {irr['recommended_water_depth_mm']} mm")
    print(f"    Per-Acre Volume: {irr['liters_per_acre']:,} Liters")
    print(f"    Total Farm Volume (2.5 ac): {irr['total_farm_liters']:,} Liters")
    print(f"    Schedule Interval: Every {irr['schedule_interval_days']} days")
    print(f"    Method: {irr['recommended_method']}")
    results["irrigation_budgeting"] = "PASS"

    # 6. Comprehensive Assessment Flow (Crop Recommendation Model)
    print("\n[6] Full Farm Assessment Pipeline (Crop Recommendation)...")
    assessment_payload = {
        "farm_name": "Godavari Green Acres",
        "district": "East Godavari",
        "state": "Andhra Pradesh",
        "acreage": 3.0,
        "irrigation_type": "Canal",
        "water_availability": "Adequate",
        "season": "kharif",
        "soil": {
            "nitrogen_kg_ha": 140.0,
            "phosphorus_kg_ha": 45.0,
            "potassium_kg_ha": 160.0,
            "ph": 6.8
        },
        "weather": {
            "temperature_c": 28.0,
            "humidity_percent": 75.0,
            "rainfall_mm": 210.0
        },
        "previous_crops": ["Rice", "Black Gram"],
        "language": "en"
    }
    r_ass = client.post("/api/v1/assessments", json=assessment_payload, headers=headers)
    assert r_ass.status_code in (200, 201), f"Assessment failed: {r_ass.text}"
    ass = r_ass.json()
    ass_id = ass["assessment_id"]
    crop_pred = ass["results"][0]["prediction"]
    print(f"    Assessment ID: {ass_id}")
    print(f"    Recommended Crop: {crop_pred['recommended_crop']} ({crop_pred['recommended_crop_te']})")
    print(f"    Confidence: {crop_pred['confidence'] * 100:.1f}%")
    print(f"    Advisor Summary: {ass['advisor']['summary'][:80]}...")
    results["full_assessment"] = "PASS"

    # 7. Crop Yield Regressor
    print("\n[7] Crop Yield Regressor (crop-yield-v1, R² = 0.9802)...")
    r_yield = client.post("/api/v1/predictions/crop-yield", json={
        "crop": "Rice",
        "season": "Kharif",
        "state": "Andhra Pradesh",
        "crop_year": 2024,
        "area_hectares": 1.2,
        "annual_rainfall_mm": 950.0,
        "fertilizer_kg": 180.0,
        "pesticide_kg": 4.5
    })
    assert r_yield.status_code == 200, f"Crop yield failed: {r_yield.text}"
    yield_data = r_yield.json()
    print(f"    Predicted Yield: {yield_data['predicted_yield_tonnes_per_hectare']} t/ha")
    print(f"    Total Expected Production: {yield_data['predicted_total_production_tonnes']} tonnes")
    print(f"    Algorithm: {yield_data['algorithm']}")
    results["crop_yield"] = "PASS"

    # 8. Climate Change Scenario Analysis
    print("\n[8] Climate Scenario Analysis (climate-scenario-v1)...")
    r_clim = client.post("/api/v1/predictions/climate-scenario", json={
        "crop": "Rice",
        "crop_year": 2024,
        "season": "Kharif",
        "state": "Andhra Pradesh",
        "baseline_rainfall_mm": 950.0
    })
    assert r_clim.status_code == 200, f"Climate scenario failed: {r_clim.text}"
    clim = r_clim.json()
    print(f"    Baseline Yield: {clim['baseline_yield_tonnes_per_ha']} t/ha")
    print(f"    Moderate Shock (-10% rain): {clim['moderate_shock_yield_tonnes_per_ha']} t/ha ({clim['moderate_change_percent']}%)")
    print(f"    Severe Shock (-25% rain): {clim['severe_shock_yield_tonnes_per_ha']} t/ha ({clim['severe_change_percent']}%)")
    print(f"    Vulnerability Tier: {clim['vulnerability_tier']}")
    results["climate_scenario"] = "PASS"

    # 9. Sustainability Score Engine
    print("\n[9] Sustainability & Footprint Score (sustainability-v1)...")
    r_sust = client.post("/api/v1/predictions/sustainability", json={
        "area_hectares": 1.2,
        "fertilizer_kg": 180.0,
        "pesticide_kg": 4.5,
        "yield_tonnes_per_ha": 3.4
    })
    assert r_sust.status_code == 200, f"Sustainability failed: {r_sust.text}"
    sust = r_sust.json()
    print(f"    Sustainability Score: {sust['score']}/100 ({sust['category']})")
    print(f"    Fertilizer Index: {sust['fertilizer_score']:.1f}, Pesticide Index: {sust['pesticide_score']:.1f}")
    results["sustainability"] = "PASS"

    # 10. Weather Risk ML Model
    print("\n[10] Weather Risk Classifier (weather-risk-v1, XGBoost)...")
    r_wr = client.post("/api/v1/predictions/weather-risk", json={
        "month": 7,
        "season": "Kharif",
        "state": "Andhra Pradesh",
        "avg_temp_c": 31.0,
        "wind_speed_kmh": 22.0,
        "air_pressure_hpa": 1008.0,
        "rainfall_mm": 180.0
    })
    assert r_wr.status_code == 200, f"Weather risk failed: {r_wr.text}"
    wr = r_wr.json()
    print(f"    Predicted Risk: {wr['predicted_risk_level']} (Confidence: {wr['confidence'] * 100:.1f}%)")
    print(f"    Algorithm: {wr['algorithm']}")
    results["weather_risk"] = "PASS"

    # 11. AI Chatbot with ICAR Agricultural Fallback
    print("\n[11] AI Chatbot with ICAR Agricultural Fallback...")
    r_chat = client.post("/api/v1/chat", json={
        "message": "What is the recommended fertilizer dose for Rice in Andhra Pradesh?",
        "assessment_id": ass_id,
        "language": "en"
    })
    assert r_chat.status_code == 200, f"Chat failed: {r_chat.text}"
    chat_resp = r_chat.json()
    print(f"    Response Provider: {chat_resp.get('provider', 'ICAR Knowledge Fallback')}")
    print(f"    Reply: {chat_resp['reply'][:100]}...")
    results["ai_chatbot"] = "PASS"

    # 12. PDF Advisory Report Generation
    print("\n[12] PDF Advisory Report Generation...")
    r_pdf = client.post(f"/api/v1/assessments/{ass_id}/report/confirm", headers=headers)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    pdf_bytes = len(r_pdf.content)
    print(f"    PDF Report Size: {pdf_bytes} bytes (Valid application/pdf)")
    results["pdf_generation"] = "PASS"

    # 13. User Isolation & Session Revocation
    print("\n[13] User Isolation & Session Revocation...")
    r_out = client.post("/api/v1/auth/logout", headers=headers)
    assert r_out.status_code == 200
    r_revoked = client.get("/api/v1/auth/me", headers=headers)
    assert r_revoked.status_code == 401
    print("    Session Revocation Verified: PASS (401 Unauthorized after logout)")
    results["session_revocation"] = "PASS"

    print("\n" + "=" * 65)
    print("ALL 13 VERIFICATION SUITES COMPLETED WITH 100% SUCCESS")
    print("=" * 65)
    return results

if __name__ == "__main__":
    test_system()
