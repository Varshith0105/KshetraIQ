import os
import sys
import secrets
import tempfile
from pathlib import Path

# Ensure offline deterministic test without socket delay
os.environ.pop("DATA_GOV_IN_API_KEY", None)

sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app

def main():
    print("=" * 80, flush=True)
    print("SECTION 8: BROWSER / CLIENT END-TO-END FLOW VERIFICATION", flush=True)
    print("=" * 80, flush=True)

    temp_dir = tempfile.mkdtemp()
    test_db = Path(temp_dir) / "e2e_test.db"

    # Use test settings with isolated database
    settings = Settings(environment="test", sqlite_db_path=test_db, _env_file=None)
    app = create_app(settings)

    with TestClient(app) as client:
        # Step 1: User Registration & Authentication
        email = f"farmer_audit_{secrets.token_hex(4)}@kshetraiq.test"
        pw = "SecurePassword123!"
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Ramesh Reddy", "password": pw, "confirm_password": pw},
        )
        assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
        auth_data = reg_resp.json()
        token = auth_data["token"]
        user_id = auth_data["user"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Step 1: Authenticated user 'Ramesh Reddy' (ID: {user_id}, Token: {token[:16]}...)", flush=True)

        # Configure farm profile
        prof_resp = client.put(
            "/api/v1/farm-profile",
            headers=headers,
            json={
                "farm_name": "Ramesh Krishi Farm",
                "state": "Andhra Pradesh",
                "district": "Guntur",
                "acreage": 3.5,
                "season": "Kharif",
                "irrigation_method": "Drip",
                "water_availability": "Borewell",
            }
        )
        assert prof_resp.status_code == 200, f"Farm profile failed: {prof_resp.text}"
        print(f"Farm profile configured: Status {prof_resp.status_code} (Guntur, AP, 3.5 acres)", flush=True)

        # Steps 2-8: Open Market Insights & Request Forecast for Wheat @ Varanasi(Grain)
        print("\nStep 2-8: Requesting Market Forecast for Wheat @ Varanasi(Grain)...", flush=True)
        payload = {
            "commodity": "Wheat",
            "mandi": "Varanasi(Grain)",
            "days_ahead": 7
        }
        resp = client.post("/api/v1/predictions/market-price", json=payload, headers=headers)
        assert resp.status_code == 200, f"Forecast failed with status {resp.status_code}: {resp.text}"
        data = resp.json()

        print(f"-> Status Code: {resp.status_code}", flush=True)
        print(f"-> Commodity: {data['commodity']} | Mandi: {data['mandi']} | Variety: {data['variety']}", flush=True)
        print(f"-> Forecast Modal Price: Rs. {data['forecast_modal_price']} /{data['price_unit']} on {data['forecast_date']}", flush=True)
        print(f"-> Latest Observed Price: Rs. {data['observed_market_price']} on {data['observation_date']}", flush=True)
        print(f"-> Movement: Rs. {data['expected_change']} ({data['expected_change_pct']}%) | Trend: {data['trend_direction']}", flush=True)
        print(f"-> Data Source: {data['data_source']}", flush=True)
        print(f"-> Live Feed Status: {data['live_feed_status']} | Stale: {data['is_stale']}", flush=True)
        print(f"-> Retrieved At: {data['retrieved_at']}", flush=True)
        print(f"-> Approximate Uncertainty: Rs. {data['confidence_band']['lower_bound']} to Rs. {data['confidence_band']['upper_bound']} (MAE: ±Rs. {data['confidence_band']['mae']}/Q)", flush=True)
        print(f"-> Methodology: {data['confidence_band']['uncertainty_methodology']}", flush=True)
        print(f"-> 7-Day Trajectory: {len(data['forecast_trajectory'])} daily steps:", flush=True)
        for step in data['forecast_trajectory']:
            print(f"     Day {step['day_offset']} ({step['date']}): Rs. {step['forecast_modal_price']}", flush=True)

        # Verification of hybrid schema requirements
        assert data["price_unit"] == "Rs./Quintal"
        assert data["observation_date"] is not None
        assert data["retrieved_at"] is not None
        assert len(data["forecast_trajectory"]) == 7
        assert data["confidence_band"]["lower_bound"] > 0
        assert "uncertainty_methodology" in data["confidence_band"]
        assert data["primary_forecast_method"] == "persistence"
        assert data["forecast_modal_price"] == data["observed_market_price"]
        assert data["seasonal_model_estimate"] > 0
        print(f"-> Primary Forecast Method: {data['primary_forecast_method']} ({data['forecast_method_label']})", flush=True)
        print(f"-> Seasonal Model Reference: Rs. {data['seasonal_model_estimate']} (Diff: {data['seasonal_difference']} Rs/Q, {data['seasonal_difference_pct']}%)", flush=True)

        # Steps 9-10: Open AI Assistant & Ask: 'Why is the forecast different from today's modal price?'
        print("\nStep 9-10: Asking AI Assistant: 'Why is the forecast different from today's modal price?' (English)...", flush=True)
        chat_payload_en = {
            "message": "Why is the forecast different from today's modal price?",
            "language": "en",
            "screen_context": {
                "screen_id": "market",
                "screen_title": "Market Price Insights",
                "displayed_data": {
                    "commodity": data["commodity"],
                    "mandi": data["mandi"],
                    "forecast_modal_price": data["forecast_modal_price"],
                    "observed_modal_price": data["observed_market_price"],
                    "expected_change": data["expected_change"],
                    "expected_change_pct": data["expected_change_pct"],
                    "trend_direction": data["trend_direction"]
                }
            }
        }
        chat_resp_en = client.post("/api/v1/chat", headers=headers, json=chat_payload_en)
        assert chat_resp_en.status_code == 200, f"Chat failed: {chat_resp_en.text}"
        chat_data_en = chat_resp_en.json()

        print(f"AI Assistant English Response (Why Different):", flush=True)
        print(f"  Observed:\n    {chat_data_en.get('observed')}", flush=True)
        print(f"  Analysis:\n    {chat_data_en.get('analysis')}", flush=True)
        assert "Persistence" in (chat_data_en.get("analysis") or "") or "persistence" in (chat_data_en.get("analysis") or "").lower()
        assert "LightGBM" in (chat_data_en.get("analysis") or "")

        # Ask Selling vs Waiting Question
        print("\nStep 10b: Asking AI Assistant: 'Should I sell my crop today or wait for a week?' (English)...", flush=True)
        sell_resp = client.post("/api/v1/chat", headers=headers, json={
            "message": "Should I sell my crop today or wait for a week?",
            "language": "en",
            "screen_context": chat_payload_en["screen_context"]
        })
        assert sell_resp.status_code == 200
        sell_data = sell_resp.json()
        print(f"AI Assistant Response (Sell vs Wait):\n    {sell_data.get('analysis')}", flush=True)
        assert "Decision" in (sell_data.get("analysis") or "") or "storage" in (sell_data.get("analysis") or "").lower()

        # Ask Forecasting Method Question
        print("\nStep 10c: Asking AI Assistant: 'Which forecast method is being used?' (English)...", flush=True)
        method_resp = client.post("/api/v1/chat", headers=headers, json={
            "message": "Which forecast method is being used?",
            "language": "en",
            "screen_context": chat_payload_en["screen_context"]
        })
        assert method_resp.status_code == 200
        method_data = method_resp.json()
        print(f"AI Assistant Response (Method):\n    {method_data.get('analysis')}", flush=True)
        assert "Hybrid" in (method_data.get("analysis") or "") or "Persistence" in (method_data.get("analysis") or "")

        # Ask Reliability & Uncertainty Question
        print("\nStep 10d: Asking AI Assistant: 'How reliable is this prediction?' (English)...", flush=True)
        rel_resp = client.post("/api/v1/chat", headers=headers, json={
            "message": "How reliable is this prediction?",
            "language": "en",
            "screen_context": chat_payload_en["screen_context"]
        })
        assert rel_resp.status_code == 200
        rel_data = rel_resp.json()
        print(f"AI Assistant Response (Reliability):\n    {rel_data.get('analysis')}", flush=True)
        assert "MAE" in (rel_data.get("analysis") or "") or "conformal" in (rel_data.get("analysis") or "").lower()

        # Ask Price Comparison Question
        print("\nStep 10e: Asking AI Assistant: 'Compare the current price with the 7-day estimate' (English)...", flush=True)
        comp_resp = client.post("/api/v1/chat", headers=headers, json={
            "message": "Compare the current price with the 7-day estimate",
            "language": "en",
            "screen_context": chat_payload_en["screen_context"]
        })
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        print(f"AI Assistant Response (Comparison):\n    {comp_data.get('analysis')}", flush=True)
        assert str(int(data["observed_market_price"])) in (comp_data.get("analysis") or "") or "₹" in (comp_data.get("analysis") or "")

        # Steps 11-12: Ask in Telugu: 'నేను పంటను ఈరోజే అమ్మాలా లేదా వేచి ఉండాలా?' (Telugu)
        print("\nStep 11-12: Asking AI Assistant in Telugu: 'నేను పంటను ఈరోజే అమ్మాలా లేదా వేచి ఉండాలా?' (Telugu)...", flush=True)
        chat_payload_te = {
            "message": "నేను పంటను ఈరోజే అమ్మాలా లేదా వేచి ఉండాలా?",
            "language": "te",
            "screen_context": chat_payload_en["screen_context"]
        }
        chat_resp_te = client.post("/api/v1/chat", headers=headers, json=chat_payload_te)
        assert chat_resp_te.status_code == 200, f"Telugu chat failed: {chat_resp_te.text}"
        chat_data_te = chat_resp_te.json()

        print(f"AI Assistant Telugu Response:", flush=True)
        print(f"  Observed (గమనించిన వివరాలు):\n    {chat_data_te.get('observed')}", flush=True)
        print(f"  Analysis (విశ్లేషణ):\n    {chat_data_te.get('analysis')}", flush=True)
        print(f"  Recommendation (సిఫార్సు):\n    {chat_data_te.get('recommendation')}", flush=True)

        assert "LightGBM" in (chat_data_te.get("observed") or "") or "ప్రాథమిక" in (chat_data_te.get("observed") or "")
        assert "నిర్ణయ" in (chat_data_te.get("analysis") or "") or "నిల్వ" in (chat_data_te.get("analysis") or "")

        # Steps 13-14: Change commodity and mandi: Dry Chillies @ Guntur
        print("\nStep 13-14: Changing commodity to 'Dry Chillies' and mandi to 'Guntur'...", flush=True)
        payload_chilli = {
            "commodity": "Dry Chillies",
            "mandi": "Guntur",
            "days_ahead": 7
        }
        resp_chilli = client.post("/api/v1/predictions/market-price", json=payload_chilli, headers=headers)
        assert resp_chilli.status_code == 200, f"Chilli forecast failed: {resp_chilli.text}"
        data_chilli = resp_chilli.json()

        print(f"-> Updated Commodity: {data_chilli['commodity']} | Mandi: {data_chilli['mandi']}", flush=True)
        print(f"-> Updated Modal Price: Rs. {data_chilli['forecast_modal_price']} /{data_chilli['price_unit']}", flush=True)
        print(f"-> Updated Benchmark: Rs. {data_chilli['observed_market_price']} ({data_chilli['live_feed_status']})", flush=True)

        # Ask AI Assistant about updated screen
        chat_payload_chilli = {
            "message": "What is the forecast price and advice for this market?",
            "language": "en",
            "screen_context": {
                "screen_id": "market",
                "screen_title": "Market Price Insights",
                "displayed_data": {
                    "commodity": data_chilli["commodity"],
                    "mandi": data_chilli["mandi"],
                    "forecast_modal_price": data_chilli["forecast_modal_price"],
                    "observed_modal_price": data_chilli["observed_market_price"],
                    "expected_change": data_chilli["expected_change"],
                    "expected_change_pct": data_chilli["expected_change_pct"],
                    "trend_direction": data_chilli["trend_direction"]
                }
            }
        }
        chat_resp_chilli = client.post("/api/v1/chat", headers=headers, json=chat_payload_chilli)
        assert chat_resp_chilli.status_code == 200, f"Updated chat failed: {chat_resp_chilli.text}"
        chat_data_chilli = chat_resp_chilli.json()

        print(f"\nAI Assistant Updated Context Response:", flush=True)
        print(f"  Observed:\n    {chat_data_chilli.get('observed')}", flush=True)
        print(f"  Analysis:\n    {chat_data_chilli.get('analysis')}", flush=True)

        assert "Dry Chillies" in (chat_data_chilli.get("observed") or "") or "Guntur" in (chat_data_chilli.get("observed") or "") or "Dry Chillies" in (chat_data_chilli.get("reply") or "")
        assert "Guntur" in (chat_data_chilli.get("reply") or "") or "Dry Chillies" in (chat_data_chilli.get("reply") or "")

        print("\n" + "=" * 80, flush=True)
        print("ALL 14 STEPS OF BROWSER END-TO-END VERIFICATION COMPLETED WITH 100% SUCCESS!", flush=True)
        print("=" * 80, flush=True)

if __name__ == '__main__':
    main()
