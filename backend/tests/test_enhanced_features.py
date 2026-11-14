import io
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.main import create_app
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatResponse

client = TestClient(create_app())


def auth_headers() -> dict:
    import secrets
    pw = "SecurePassword123!"
    resp = client.post("/api/v1/auth/register", json={
        "email": f"tester_{secrets.token_hex(6)}@kshetraiq.in",
        "full_name": "QA Specialist",
        "password": pw,
        "confirm_password": pw,
    })
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_soil_report_pdf_extraction() -> None:
    """Verify digital PDF parsing extracts N, P, K, pH and metadata."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "GOVERNMENT SOIL TESTING LABORATORY")
    p.drawString(100, 730, "Soil Health Card / Test Report")
    p.drawString(100, 700, "Farmer: Ramu Naidu   District: Guntur")
    p.drawString(100, 670, "Available Nitrogen (N): 140.5 kg/ha")
    p.drawString(100, 650, "Available Phosphorus (P): 35.0 kg/ha")
    p.drawString(100, 630, "Available Potassium (K): 220.0 kg/ha")
    p.drawString(100, 610, "Soil Reaction (pH): 6.8")
    p.drawString(100, 590, "Electrical Conductivity (EC): 0.45 dS/m")
    p.drawString(100, 570, "Organic Carbon (OC): 0.65 %")
    p.drawString(100, 550, "Soil Type: Black Clay Loam")
    p.save()
    pdf_bytes = buffer.getvalue()

    h = auth_headers()
    files = {"file": ("soil_health_card.pdf", pdf_bytes, "application/pdf")}
    resp = client.post("/api/v1/uploads/soil_report/extract", files=files, headers=h)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "extracted"
    params = data["parameters"]
    assert params["nitrogen"]["value"] == 140.5
    assert params["phosphorus"]["value"] == 35.0
    assert params["potassium"]["value"] == 220.0
    assert params["ph"]["value"] == 6.8
    assert params["ec"]["value"] == 0.45
    assert params["organic_carbon"]["value"] == 0.65


def test_soil_report_image_rejection_guidance() -> None:
    """Verify raw photo uploads are rejected with honest guidance."""
    h = auth_headers()
    fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 200
    files = {"file": ("soil_photo.jpg", fake_jpg, "image/jpeg")}
    resp = client.post("/api/v1/uploads/soil_report/extract", files=files, headers=h)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "requires_certified_report"
    assert "photograph" in data["message"].lower() or "laboratory" in data["message"].lower()


def test_chat_service_reasoning_scenarios() -> None:
    """Verify domain-specific agricultural reasoning in ChatService."""
    svc = ChatService()

    # 1. Coffee on plains
    req1 = ChatRequest(
        message="Can I grow coffee in the plains of Guntur?",
        language="en",
    )
    ans1 = svc.respond(req1)
    assert "altitude" in ans1.reply.lower() or "cooler" in ans1.reply.lower() or "shade" in ans1.reply.lower()

    # 2. Why recommended with farm context
    req2 = ChatRequest(
        message="Why was rice recommended for my farm?",
        language="en",
        farm_context={
            "recommended_crop": "rice",
            "soil": {"nitrogen_kg_ha": 90, "phosphorus_kg_ha": 42, "potassium_kg_ha": 43, "ph": 6.5},
            "weather": {"temperature_c": 24, "humidity_percent": 80, "rainfall_mm": 220},
        },
    )
    ans2 = svc.respond(req2)
    assert "rice" in ans2.reply.lower()
    assert "water" in ans2.reply.lower() or "rainfall" in ans2.reply.lower() or "standing" in ans2.reply.lower()

    # 3. Nitrogen low remedies
    req3 = ChatRequest(
        message="My soil test says nitrogen is low. How do I improve it?",
        language="en",
    )
    ans3 = svc.respond(req3)
    assert "urea" in ans3.reply.lower() or "manure" in ans3.reply.lower() or "compost" in ans3.reply.lower()

    # 4. Telugu language response
    req4 = ChatRequest(
        message="వరి పంటలో ఎరువుల యాజమాన్యం ఎలా ఉండాలి?",
        language="te",
    )
    ans4 = svc.respond(req4)
    assert any("\u0c00" <= char <= "\u0c7f" for char in ans4.reply)
    assert len(ans4.reply) > 20


def test_report_generation_with_xml_special_characters() -> None:
    """Ensure farm names with XML chars (<, >, &, \", ') do not crash ReportLab."""
    h = auth_headers()
    payload = {
        "farm_name": "Ramu <Green & Organic> Farms 'East' & Sons",
        "district": "Guntur & Krishna <Border>",
        "state": "Andhra Pradesh",
        "acreage": 3.0,
        "irrigation_type": "Drip & Canal",
        "water_availability": "Borewell <High>",
        "season": "Kharif",
        "soil": {
            "nitrogen_kg_ha": 95,
            "phosphorus_kg_ha": 45,
            "potassium_kg_ha": 45,
            "ph": 6.5,
        },
        "weather": {
            "temperature_c": 26.0,
            "humidity_percent": 80.0,
            "rainfall_mm": 210.0,
        },
        "previous_crops": ["paddy <early>", "cotton & chilli"],
        "planting_preferences": "Focus on high yield & pest resistance <Bt>",
        "language": "en",
    }
    resp = client.post("/api/v1/assessments", json=payload, headers=h)
    assert resp.status_code == 201
    aid = resp.json()["assessment_id"]

    # Preview
    preview_resp = client.get(f"/api/v1/assessments/{aid}/report/preview", headers=h)
    assert preview_resp.status_code == 200

    # Confirm & Generate PDF
    pdf_resp = client.post(f"/api/v1/assessments/{aid}/report/confirm", headers=h)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")


def test_market_price_prediction_finite_bounds() -> None:
    """Verify market price prediction returns finite, non-NaN confidence bands."""
    h = auth_headers()
    payload = {
        "commodity": "Wheat",
        "mandi": "Varanasi(Grain)",
        "days_ahead": 7,
    }
    resp = client.post("/api/v1/predictions/market-price", json=payload, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecast_modal_price" in data
    assert isinstance(data["forecast_modal_price"], (int, float))
    assert "confidence_band" in data
    cb = data["confidence_band"]
    assert "lower_bound" in cb
    assert "upper_bound" in cb
    assert "lower_95" in cb
    assert "upper_95" in cb
    assert isinstance(cb["lower_bound"], (int, float))
    assert isinstance(cb["upper_bound"], (int, float))
    assert cb["lower_bound"] <= cb["upper_bound"]
