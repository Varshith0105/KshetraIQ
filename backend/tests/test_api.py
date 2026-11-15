from fastapi.testclient import TestClient

import secrets

import pytest
from app.core.config import Settings
from app.main import create_app

client: TestClient
test_settings: Settings


@pytest.fixture(scope="module", autouse=True)
def isolated_application(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Keep API checks away from the configured persistent SQLite database."""
    global client, test_settings
    db_path = tmp_path_factory.mktemp("api-db") / "kshetraiq-test.db"
    test_settings = Settings(environment="test", sqlite_db_path=db_path, _env_file=None)
    with TestClient(create_app(test_settings)) as test_client:
        client = test_client
        yield


@pytest.fixture(autouse=True)
def authenticated_client() -> None:
    """Saved farm data and uploads are private; seed a fresh browser session."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"api_test_{secrets.token_hex(8)}@kshetraiq.test",
            "full_name": "API Test Farmer",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201
    yield
    client.post("/api/v1/auth/logout")


def valid_payload_with_weather() -> dict:
    return {
        "farm_name": "Rythu Farm",
        "district": "Guntur",
        "state": "Andhra Pradesh",
        "acreage": 2.5,
        "irrigation_type": "Drip",
        "water_availability": "Borewell",
        "season": "Kharif",
        "soil": {
            "nitrogen_kg_ha": 90,
            "phosphorus_kg_ha": 42,
            "potassium_kg_ha": 43,
            "ph": 6.5,
        },
        "weather": {
            "temperature_c": 21.0,
            "humidity_percent": 82.0,
            "rainfall_mm": 200.0,
        },
        "previous_crops": ["paddy"],
        "language": "en",
    }


def test_health() -> None:
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["service"] == "kshetraiq-api"
    assert "supabase_configured" in data


def test_models_catalog_endpoint() -> None:
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 3

    ids = [m["model_id"] for m in catalog]
    # Active production models must all be present
    for required_id in ("crop-recommendation-v1", "market-price-v2", "plant-disease-v1", "irrigation-rl-v1"):
        assert required_id in ids, f"{required_id} missing from active registry"

    # Legacy rollback must NOT appear in active production listing
    assert "market-price-v1" not in ids, "market-price-v1 (rollback) must not appear in active model listing"

    crop_m = next(m for m in catalog if m["model_id"] == "crop-recommendation-v1")
    assert crop_m["contract_status"] in ("verified", "READY")

    # Verify new dual-status fields are present
    mkt_m = next(m for m in catalog if m["model_id"] == "market-price-v2")
    assert mkt_m["readiness_status"] == "VERIFIED", f"market-price-v2 readiness not VERIFIED: {mkt_m}"
    assert mkt_m["prediction_status"] == "AWAITING INPUT"
    assert mkt_m["smoke_test_passed"] is True

    disease_m = next(m for m in catalog if m["model_id"] == "plant-disease-v1")
    assert disease_m["readiness_status"] == "VERIFIED", f"plant-disease-v1 readiness not VERIFIED: {disease_m}"
    assert disease_m["prediction_status"] == "AWAITING INPUT"
    assert disease_m["smoke_test_passed"] is True


def test_missing_soil_never_fabricates_prediction() -> None:
    payload = valid_payload_with_weather()
    payload["soil"]["nitrogen_kg_ha"] = None
    response = client.post("/api/v1/assessments", json=payload)
    assert response.status_code == 201
    body = response.json()
    crop_res = next(r for r in body["results"] if r["model_id"] == "crop-recommendation-v1")
    assert crop_res["status"] == "needs_input"
    assert crop_res.get("prediction") is None
    assert "soil.nitrogen_kg_ha" in crop_res["missing_inputs"]


def test_verified_models_awaiting_input_not_blocked() -> None:
    """market-price-v2 and plant-disease-v1 must be AWAITING INPUT, never BLOCKED.
    They are runtime-verified; they simply need user-provided mandi/image input."""
    response = client.post("/api/v1/assessments", json=valid_payload_with_weather())
    assert response.status_code == 201
    body = response.json()

    market_res = next(r for r in body["results"] if r["model_id"] == "market-price-v2")
    assert market_res["status"] in ("awaiting_input",), (
        f"Expected 'awaiting_input' for market-price-v2, got: {market_res['status']}"
    )
    assert market_res["readiness_status"] == "VERIFIED"
    assert market_res["prediction_status"] == "AWAITING INPUT"
    assert market_res.get("prediction") is None
    assert "market-price-v1" not in [r["model_id"] for r in body["results"]], (
        "market-price-v1 (legacy rollback) must NOT appear in active assessment results"
    )

    disease_res = next(r for r in body["results"] if r["model_id"] == "plant-disease-v1")
    assert disease_res["status"] in ("awaiting_input",), (
        f"Expected 'awaiting_input' for plant-disease-v1, got: {disease_res['status']}"
    )
    assert disease_res["readiness_status"] == "VERIFIED"
    assert disease_res["prediction_status"] == "AWAITING INPUT"
    assert disease_res.get("prediction") is None


def test_verified_crop_recommendation_inference() -> None:
    response = client.post("/api/v1/assessments", json=valid_payload_with_weather())
    assert response.status_code == 201
    body = response.json()
    crop_res = next(r for r in body["results"] if r["model_id"] == "crop-recommendation-v1")
    assert crop_res["status"] == "predicted"
    pred = crop_res["prediction"]
    assert pred is not None
    assert pred["recommended_crop"] == "rice"
    assert pred["confidence"] > 0.5
    assert len(pred["top_candidates"]) >= 2
    assert pred["features_used"]["N"] == 90.0


def test_rejects_invalid_ph() -> None:
    payload = valid_payload_with_weather()
    payload["soil"]["ph"] = 16
    assert client.post("/api/v1/assessments", json=payload).status_code == 422


def test_advisor_deterministic_guidance() -> None:
    response = client.post("/api/v1/assessments", json=valid_payload_with_weather())
    assert response.status_code == 201
    body = response.json()
    advisor = body["advisor"]
    assert advisor is not None
    assert advisor["mode"] == "deterministic_rules"
    assert "summary" in advisor
    assert "summary_te" in advisor
    assert "rice" in advisor["summary"].lower()


def test_two_step_pdf_report_flow() -> None:
    # 1. Create assessment
    create_resp = client.post("/api/v1/assessments", json=valid_payload_with_weather())
    assert create_resp.status_code == 201
    assessment_id = create_resp.json()["assessment_id"]

    # 2. Preview report (asks for explicit confirmation)
    preview_resp = client.get(f"/api/v1/assessments/{assessment_id}/report/preview")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["farm_name"] == "Rythu Farm"
    assert "confirmation_prompt" in preview_data
    assert "confirmation_prompt_te" in preview_data

    # 3. Confirm and generate PDF
    confirm_resp = client.post(f"/api/v1/assessments/{assessment_id}/report/confirm")
    assert confirm_resp.status_code == 200
    assert confirm_resp.headers["content-type"] == "application/pdf"
    assert len(confirm_resp.content) > 1000
    assert confirm_resp.content.startswith(b"%PDF")

    # 4. Fallback test: Missing assessment ID on server can be fulfilled via client payload body
    missing_id = "00000000-0000-0000-0000-000000000000"
    missing_preview_get = client.get(f"/api/v1/assessments/{missing_id}/report/preview")
    assert missing_preview_get.status_code == 404

    # Supplying client assessment payload in POST recovers preview and generates PDF
    client_body = create_resp.json()
    client_body["assessment_id"] = missing_id
    fallback_preview = client.post(f"/api/v1/assessments/{missing_id}/report/preview", json=client_body)
    assert fallback_preview.status_code == 200
    assert fallback_preview.json()["farm_name"] == "Rythu Farm"

    fallback_pdf = client.post(f"/api/v1/assessments/{missing_id}/report/confirm", json=client_body)
    assert fallback_pdf.status_code == 200
    assert fallback_pdf.headers["content-type"] == "application/pdf"
    assert fallback_pdf.content.startswith(b"%PDF")


def test_cors_preflight_for_network_ip() -> None:
    headers = {
        "Origin": "http://172.20.34.119:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    resp = client.options("/api/v1/assessments", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://172.20.34.119:3000"
    assert "POST" in resp.headers["access-control-allow-methods"]


def test_cors_preflight_for_localhost() -> None:
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    resp = client.options("/api/v1/assessments", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_untrusted_origin() -> None:
    headers = {
        "Origin": "https://malicious-phishing-site.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    resp = client.options("/api/v1/assessments", headers=headers)
    assert resp.status_code == 400
    assert "Disallowed CORS origin" in resp.text


def test_browser_post_with_cors_origin() -> None:
    headers = {
        "Origin": "http://172.20.34.119:3000",
        "Content-Type": "application/json",
    }
    resp = client.post("/api/v1/assessments", json=valid_payload_with_weather(), headers=headers)
    assert resp.status_code == 201
    assert resp.headers["access-control-allow-origin"] == "http://172.20.34.119:3000"


def test_cors_preflight_with_private_network_header() -> None:
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
        "Access-Control-Request-Private-Network": "true",
    }
    resp = client.options("/api/v1/assessments", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-private-network") == "true"


# -- Chatbot Tests --


def test_chat_without_assessment() -> None:
    resp = client.post('/api/v1/chat', json={'message': 'help me get started', 'language': 'en'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['mode'] == 'rule_based'
    assert len(body['reply']) > 10
    assert 'disclaimer' in body


def test_chat_with_assessment_context() -> None:
    client.post('/api/v1/assessments', json=valid_payload_with_weather())
    resp = client.post('/api/v1/chat', json={'message': 'what crop do you recommend?', 'language': 'en'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['assessment_context_used'] is True
    assert 'rice' in body['reply'].lower()


def test_chat_telugu_response() -> None:
    resp = client.post('/api/v1/chat', json={'message': 'help', 'language': 'te'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['mode'] == 'rule_based'
    assert len(body['reply']) > 10


def test_chat_soil_topic() -> None:
    client.post('/api/v1/assessments', json=valid_payload_with_weather())
    resp = client.post('/api/v1/chat', json={'message': 'tell me about my soil pH', 'language': 'en'})
    assert resp.status_code == 200
    body = resp.json()
    assert 'ph' in body['reply'].lower()


# -- Assessment Listing Tests --


def test_list_assessments() -> None:
    resp = client.get('/api/v1/assessments')
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


# -- Upload Tests --


def test_upload_valid_image() -> None:
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB\x60\x82'
    )
    resp = client.post(
        '/api/v1/uploads/field_photo',
        files={'file': ('test_field.png', png_data, 'image/png')},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['category'] == 'field_photo'
    assert body['storage'] == 'local_temp'
    assert body['size_bytes'] > 0


def test_upload_rejects_invalid_type() -> None:
    resp = client.post(
        '/api/v1/uploads/field_photo',
        files={'file': ('malware.exe', b'MZ executable content', 'application/octet-stream')},
    )
    assert resp.status_code == 400
    assert 'not allowed' in resp.json()['detail'].lower()


def test_upload_rejects_invalid_category() -> None:
    resp = client.post(
        '/api/v1/uploads/secret_data',
        files={'file': ('test.png', b'\x89PNG', 'image/png')},
    )
    assert resp.status_code == 400


def test_delete_uploaded_file() -> None:
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 50
    resp = client.post(
        '/api/v1/uploads/crop_photo',
        files={'file': ('crop.png', png_data, 'image/png')},
    )
    if resp.status_code == 200:
        file_id = resp.json()['file_id']
        del_resp = client.delete(f'/api/v1/uploads/{file_id}')
        assert del_resp.status_code == 200
        assert del_resp.json()['status'] == 'deleted'


# -- Model Health & Prediction Endpoint Tests --


def test_model_health_endpoint() -> None:
    resp = client.get('/api/v1/models/crop-recommendation-v1/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'crop-recommendation-v1'
    assert data['status'] in ('verified', 'READY')
    assert data['artifact_found'] is True
    assert data['runtime_ready'] is True
    # Verify new dual-status fields
    assert data['readiness_status'] == 'VERIFIED'
    assert data['prediction_status'] in ('AWAITING INPUT', 'NOT RUN', 'PREDICTED')
    assert 'last_verified_at' in data
    assert 'runtime_verification_result' in data

    # Verify market-price-v2 health (must be VERIFIED, not blocked)
    resp_mkt = client.get('/api/v1/models/market-price-v2/health')
    assert resp_mkt.status_code == 200
    data_mkt = resp_mkt.json()
    assert data_mkt['model_id'] == 'market-price-v2'
    assert data_mkt['readiness_status'] == 'VERIFIED', f"market-price-v2 must be VERIFIED, got: {data_mkt['readiness_status']}"
    assert data_mkt['prediction_status'] == 'AWAITING INPUT'
    assert data_mkt['smoke_test_passed'] is True

    # Verify plant-disease-v1 health (must be VERIFIED, not blocked)
    resp_pd = client.get('/api/v1/models/plant-disease-v1/health')
    assert resp_pd.status_code == 200
    data_pd = resp_pd.json()
    assert data_pd['model_id'] == 'plant-disease-v1'
    assert data_pd['readiness_status'] == 'VERIFIED', f"plant-disease-v1 must be VERIFIED, got: {data_pd['readiness_status']}"
    assert data_pd['prediction_status'] == 'AWAITING INPUT'
    assert data_pd['smoke_test_passed'] is True

    # Check irrigation-rl-v1 model health
    resp_irr = client.get('/api/v1/models/irrigation-rl-v1/health')
    assert resp_irr.status_code == 200
    data_irr = resp_irr.json()
    assert data_irr['model_id'] == 'irrigation-rl-v1'
    assert data_irr['status'] == 'READY'
    assert data_irr['artifact_found'] is True
    assert data_irr['runtime_ready'] is True
    assert data_irr['smoke_test_passed'] is True

    # Check non-existent model
    not_found = client.get('/api/v1/models/non-existent-model/health')
    assert not_found.status_code == 404


def test_crop_yield_prediction_endpoint() -> None:
    payload = {
        'crop': 'Rice',
        'season': 'Kharif',
        'state': 'Andhra Pradesh',
        'crop_year': 2024,
        'area_hectares': 2.5,
        'annual_rainfall_mm': 950.0,
        'fertilizer_kg': 250.0,
        'pesticide_kg': 0.5,
    }
    resp = client.post('/api/v1/predictions/crop-yield', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'crop-yield-v1'
    assert data['status'] == 'success'
    assert data['predicted_yield_tonnes_per_hectare'] > 0
    assert data['predicted_total_production_tonnes'] > 0


def test_climate_scenario_prediction_endpoint() -> None:
    payload = {
        'crop': 'Rice',
        'crop_year': 2024,
        'season': 'Kharif',
        'state': 'Andhra Pradesh',
        'baseline_rainfall_mm': 1100.0,
    }
    resp = client.post('/api/v1/predictions/climate-scenario', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'climate-scenario-v1'
    assert data['baseline_yield_tonnes_per_ha'] > 0
    assert 'vulnerability_tier' in data


def test_sustainability_calculation_endpoint() -> None:
    payload = {
        'area_hectares': 2.5,
        'fertilizer_kg': 200.0,
        'pesticide_kg': 0.3,
        'yield_tonnes_per_ha': 3.2,
    }
    resp = client.post('/api/v1/predictions/sustainability', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'sustainability-v1'
    assert 0 <= data['score'] <= 100
    assert data['category'] in {'High Sustainability', 'Moderate Sustainability', 'Low Sustainability'}


def test_weather_risk_prediction_endpoint() -> None:
    payload = {
        'month': 7,
        'season': 'Kharif',
        'state': 'Andhra Pradesh',
        'avg_temp_c': 31.0,
        'wind_speed_kmh': 14.0,
        'air_pressure_hpa': 1008.0,
        'rainfall_mm': 25.0,
    }
    resp = client.post('/api/v1/predictions/weather-risk', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'weather-risk-v1'
    assert data['predicted_risk_level'] in {'Low', 'Moderate', 'High', 'Extreme'}
    assert 0.0 <= data['confidence'] <= 1.0


def test_market_price_prediction_endpoint() -> None:
    resp = client.post('/api/v1/predictions/market-price', json={'commodity': 'Wheat', 'mandi': 'Varanasi(Grain)', 'days_ahead': 7})
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'market-price-v2', f"Expected market-price-v2, got {data['model_id']}"
    assert data['commodity'] == 'Wheat'
    assert data['forecast_modal_price'] > 0
    assert 'observed_market_price' in data
    assert 'confidence_band' in data

    obs_resp = client.get('/api/v1/market/prices')
    assert obs_resp.status_code == 200
    obs_data = obs_resp.json()
    assert obs_data['commodity'] == 'Wheat'
    assert obs_data['observed_modal_price'] > 0


def test_plant_disease_prediction_endpoint() -> None:
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (160, 160), color=(34, 139, 34)).save(buf, format="JPEG")
    jpeg_data = buf.getvalue()
    resp = client.post(
        "/api/v1/predictions/plant-disease",
        files={"file": ("leaf_sample.jpg", jpeg_data, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "plant-disease-v1"
    assert "predicted_class" in data
    assert data["confidence_pct"] >= 0.0
    assert len(data["top_candidates"]) == 3
    assert "disclaimer" in data


def test_plant_disease_rejects_non_image() -> None:
    resp = client.post(
        '/api/v1/predictions/plant-disease',
        files={'file': ('not_an_image.txt', b'hello world text file', 'text/plain')},
    )
    assert resp.status_code == 400


def test_irrigation_prediction_endpoint() -> None:
    payload = {
        'crop': 'Rice',
        'crop_days': 45,
        'soil_moisture': 210.0,
        'soil_type': 'Loam',
        'temperature': 30.0,
        'rainfall_forecast_mm': 0.0,
        'area_acres': 2.5,
    }
    resp = client.post('/api/v1/predictions/irrigation', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] in ('irrigation-rl-ppo-v1', 'irrigation-deterministic-icar-v1')
    assert data['action'] == 'IRRIGATION_NEEDED'
    assert data['total_farm_liters'] > 0
    assert 'rl_status_note' in data

    # Verify explicit deterministic fallback execution
    payload_det = dict(payload)
    payload_det['force_deterministic'] = True
    resp_det = client.post('/api/v1/predictions/irrigation', json=payload_det)
    assert resp_det.status_code == 200
    data_det = resp_det.json()
    assert data_det['model_id'] == 'irrigation-deterministic-icar-v1'
    assert data_det['method_used'] == 'icar_angrau_deterministic'


def test_auth_registration_login_and_user_isolation() -> None:
    import secrets
    unique_email = f'farmer_{secrets.token_hex(4)}@kshetraiq.in'
    reg_payload = {
        'email': unique_email,
        'full_name': 'Ramesh Kumar',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!',
    }

    reg_resp = client.post('/api/v1/auth/register', json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    token = reg_data['token']
    user_id = reg_data['user']['user_id']
    assert reg_data['user']['email'] == unique_email

    dup_resp = client.post('/api/v1/auth/register', json=reg_payload)
    assert dup_resp.status_code == 400

    me_resp = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me_resp.status_code == 200
    assert me_resp.json()['user_id'] == user_id

    login_resp = client.post('/api/v1/auth/login', json={'email': unique_email, 'password': 'SecurePassword123!'})
    assert login_resp.status_code == 200
    assert login_resp.json()['user']['user_id'] == user_id

    bad_login = client.post('/api/v1/auth/login', json={'email': unique_email, 'password': 'WrongPassword'})
    assert bad_login.status_code == 401

    assess_resp = client.post(
        '/api/v1/assessments',
        json=valid_payload_with_weather(),
        headers={'Authorization': f'Bearer {token}'},
    )
    assert assess_resp.status_code == 201
    assess_id = assess_resp.json()['assessment_id']

    other_email = f'other_{secrets.token_hex(4)}@kshetraiq.in'
    other_reg = client.post(
        '/api/v1/auth/register',
        json={
            'email': other_email,
            'full_name': 'Suresh Patel',
            'password': 'Password456!',
            'confirm_password': 'Password456!',
        },
    )
    other_token = other_reg.json()['token']

    forbidden_resp = client.get(
        f'/api/v1/assessments/{assess_id}',
        headers={'Authorization': f'Bearer {other_token}'},
    )
    assert forbidden_resp.status_code == 404

    logout_resp = client.post('/api/v1/auth/logout', headers={'Authorization': f'Bearer {token}'})
    assert logout_resp.status_code == 200

    me_after = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me_after.status_code == 401


def test_sqlite_persistence_survives_reload() -> None:
    create_resp = client.post('/api/v1/assessments', json=valid_payload_with_weather())
    assert create_resp.status_code == 201
    created_id = create_resp.json()['assessment_id']

    from app.main import create_app
    reloaded_app = create_app(test_settings)
    reloaded_client = TestClient(reloaded_app)

    session = client.cookies.get("kshetraiq_session")
    get_resp = reloaded_client.get(
        f'/api/v1/assessments/{created_id}',
        headers={'Cookie': f'kshetraiq_session={session}'},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()['assessment_id'] == created_id


def test_market_commodities_catalog_endpoint() -> None:
    res = client.get("/api/v1/market/commodities")
    assert res.status_code == 200
    data = res.json()
    assert "popular_commodities" in data
    assert "popular_mandis" in data
    assert len(data["popular_commodities"]) >= 20
    assert len(data["popular_mandis"]) >= 16

    names = [c["name"] for c in data["popular_commodities"]]
    for expected in ["Rice", "Turmeric", "Sugarcane", "Coriander(Leaves)", "Garlic", "Ginger(Dry)", "Castor Seed"]:
        assert expected in names


def test_assessment_summary_endpoint() -> None:
    res = client.get("/api/v1/assessments/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total" in summary
    assert "completed" in summary
    assert "incomplete" in summary


def test_prediction_history_endpoints() -> None:
    res_hist = client.get("/api/v1/predictions/history")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)

    res_sum = client.get("/api/v1/predictions/summary")
    assert res_sum.status_code == 200
    assert isinstance(res_sum.json(), dict)

