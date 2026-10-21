from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def auth_headers() -> dict:
    """Register a fresh farmer account and return its bearer auth header."""
    import secrets
    pw = 'SecurePassword123!'
    resp = client.post('/api/v1/auth/register', json={
        'email': f'test_{secrets.token_hex(6)}@kshetraiq.in',
        'full_name': 'Test Farmer',
        'password': pw,
        'confirm_password': pw,
    })
    assert resp.status_code == 201
    return {'Authorization': f"Bearer {resp.json()['token']}"}


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
    crop_m = next(m for m in catalog if m["model_id"] == "crop-recommendation-v1")
    assert crop_m["contract_status"] in ("verified", "READY")


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


def test_blocked_models_never_fabricate_predictions() -> None:
    response = client.post("/api/v1/assessments", json=valid_payload_with_weather())
    assert response.status_code == 201
    body = response.json()
    market_res = next(r for r in body["results"] if r["model_id"] == "market-price-v1")
    assert market_res["status"] == "blocked"
    assert market_res.get("prediction") is None

    disease_res = next(r for r in body["results"] if r["model_id"] == "plant-disease-v1")
    assert disease_res["status"] == "blocked"
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
    h = auth_headers()
    # 1. Create assessment
    create_resp = client.post("/api/v1/assessments", json=valid_payload_with_weather(), headers=h)
    assert create_resp.status_code == 201
    assessment_id = create_resp.json()["assessment_id"]

    # 2. Preview report (asks for explicit confirmation)
    preview_resp = client.get(f"/api/v1/assessments/{assessment_id}/report/preview", headers=h)
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["farm_name"] == "Rythu Farm"
    assert "confirmation_prompt" in preview_data
    assert "confirmation_prompt_te" in preview_data

    # 3. Confirm and generate PDF
    confirm_resp = client.post(f"/api/v1/assessments/{assessment_id}/report/confirm", headers=h)
    assert confirm_resp.status_code == 200
    assert confirm_resp.headers["content-type"] == "application/pdf"
    assert len(confirm_resp.content) > 1000
    assert confirm_resp.content.startswith(b"%PDF")


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
    h = auth_headers()
    client.post('/api/v1/assessments', json=valid_payload_with_weather(), headers=h)
    resp = client.post('/api/v1/chat', json={'message': 'what crop do you recommend?', 'language': 'en'}, headers=h)
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
    h = auth_headers()
    client.post('/api/v1/assessments', json=valid_payload_with_weather(), headers=h)
    resp = client.post('/api/v1/chat', json={'message': 'tell me about my soil pH', 'language': 'en'}, headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert 'ph' in body['reply'].lower()


# -- Assessment Listing Tests --


def test_list_assessments() -> None:
    resp = client.get('/api/v1/assessments', headers=auth_headers())
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
        headers=auth_headers(),
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
        headers=auth_headers(),
    )
    assert resp.status_code == 400
    assert 'not allowed' in resp.json()['detail'].lower()


def test_upload_rejects_invalid_category() -> None:
    resp = client.post(
        '/api/v1/uploads/secret_data',
        files={'file': ('test.png', b'\x89PNG', 'image/png')},
        headers=auth_headers(),
    )
    assert resp.status_code == 400


def test_delete_uploaded_file() -> None:
    h = auth_headers()
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 50
    resp = client.post(
        '/api/v1/uploads/crop_photo',
        files={'file': ('crop.png', png_data, 'image/png')},
        headers=h,
    )
    assert resp.status_code == 200
    file_id = resp.json()['file_id']
    # another user cannot delete it
    assert client.delete(f'/api/v1/uploads/{file_id}', headers=auth_headers()).status_code == 404
    del_resp = client.delete(f'/api/v1/uploads/{file_id}', headers=h)
    assert del_resp.status_code == 200
    assert del_resp.json()['status'] == 'deleted'


def test_upload_rejects_spoofed_content() -> None:
    resp = client.post(
        '/api/v1/uploads/field_photo',
        files={'file': ('fake.png', b'MZ this is not really a png', 'image/png')},
        headers=auth_headers(),
    )
    assert resp.status_code == 400


def test_upload_rejects_oversized_file() -> None:
    from app.core.config import get_settings
    big = b'\x89PNG\r\n\x1a\n' + b'\x00' * (get_settings().max_upload_bytes + 1)
    resp = client.post(
        '/api/v1/uploads/field_photo',
        files={'file': ('big.png', big, 'image/png')},
        headers=auth_headers(),
    )
    assert resp.status_code == 413


def test_uploads_require_auth_and_persist_across_restart() -> None:
    anon_client = TestClient(create_app())  # fresh client: no session cookie from earlier registrations
    assert anon_client.get('/api/v1/uploads').status_code == 401
    h = auth_headers()
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
    up = client.post('/api/v1/uploads/field_photo', files={'file': ('p.png', png, 'image/png')}, headers=h)
    assert up.status_code == 200
    reloaded = TestClient(create_app())
    ids = [f['file_id'] for f in reloaded.get('/api/v1/uploads', headers=h).json()]
    assert up.json()['file_id'] in ids


def test_saved_records_require_auth() -> None:
    anon_client = TestClient(create_app())  # fresh client: no session cookie
    assert anon_client.get('/api/v1/assessments').status_code == 401
    anon = anon_client.post('/api/v1/assessments', json=valid_payload_with_weather())
    assert anon.status_code == 201
    anon_id = anon.json()['assessment_id']
    # anonymous (unowned) results are never readable back, even by signed-in users
    assert anon_client.get(f'/api/v1/assessments/{anon_id}').status_code == 401
    assert client.get(f'/api/v1/assessments/{anon_id}', headers=auth_headers()).status_code == 404
    assert anon_client.get(f'/api/v1/assessments/{anon_id}/report/preview').status_code == 401



# -- Model Health & Prediction Endpoint Tests --


def test_model_health_endpoint() -> None:
    resp = client.get('/api/v1/models/crop-recommendation-v1/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['model_id'] == 'crop-recommendation-v1'
    assert data['status'] in ('verified', 'READY')  # status was updated to use clearer runtime labels
    assert data['artifact_found'] is True
    assert data['runtime_ready'] is True

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
    assert data['model_id'] == 'market-price-v1'
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
    assert data['model_id'] == 'irrigation-deterministic-icar-v1'
    assert data['action'] == 'IRRIGATION_NEEDED'
    assert data['total_farm_liters'] > 0
    assert 'rl_status_note' in data


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
    h = auth_headers()
    create_resp = client.post('/api/v1/assessments', json=valid_payload_with_weather(), headers=h)
    assert create_resp.status_code == 201
    created_id = create_resp.json()['assessment_id']

    from app.core.config import get_settings
    from app.main import create_app
    reloaded_app = create_app(get_settings())
    reloaded_client = TestClient(reloaded_app)

    get_resp = reloaded_client.get(f'/api/v1/assessments/{created_id}', headers=h)
    assert get_resp.status_code == 200
    assert get_resp.json()['assessment_id'] == created_id
