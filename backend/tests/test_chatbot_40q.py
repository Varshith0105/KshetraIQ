"""
Comprehensive 40-Question Evaluation Test Suite for KshetraIQ Agricultural Intelligence Chatbot.
Validates end-to-end intelligence across all 10 application dimensions:
1. Farm & Dashboard Overview
2. Soil Health & Diagnostics (ICAR 5-band)
3. Live Weather & Agro-Meteorology
4. Crop Recommendation & Alternatives
5. Yield Prediction & Production Economics
6. Precision Irrigation & Water Management
7. Market Intelligence & Forecasting (LightGBM)
8. Plant Disease Identification (ResNet50)
9. Telugu Bilingual Fluency & Script Integrity
10. Model Registry, PDF Reports & Multi-Agent Orchestration
"""

import pytest
from app.services.context_engine import context_engine
from app.services.langgraph_orchestrator import langgraph_orchestrator
from app.schemas.chat import ScreenContextPayload


def _has_telugu(text: str) -> bool:
    """Return True if text contains Telugu Unicode characters (0x0C00 - 0x0C7F)."""
    return any(0x0C00 <= ord(c) <= 0x0C7F for c in text)


# ══════════════════════════════════════════════════════════════
# CATEGORY 1: Farm & Dashboard Overview
# ══════════════════════════════════════════════════════════════

def test_q01_dashboard_overall_performance():
    ctx = context_engine.build_context(
        user_id=None,
        query="How is my farm performing overall?",
        screen_context_payload={"screen_id": "dashboard", "displayed_data": {"farm_name": "Krishna Valley", "district": "Guntur"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 20
    assert "Krishna Valley" in res.reply or "Guntur" in res.reply


def test_q02_dashboard_screen_explanation():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is shown on my dashboard screen?",
        screen_context_payload={"screen_id": "dashboard", "screen_title": "Farm Intelligence Dashboard"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 20
    assert res.screen_context_used is True
    assert "dashboard" in res.reply.lower() or "farm" in res.reply.lower()


def test_q03_farm_acreage_and_location():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my farm acreage and location?",
        screen_context_payload={"screen_id": "dashboard", "displayed_data": {"acreage": 4.5, "district": "Warangal"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 15
    assert "acres" in res.reply.lower() or "farm" in res.reply.lower()


def test_q04_farm_statistics_summary():
    ctx = context_engine.build_context(
        user_id=None,
        query="Summarize my active farm indicators",
        screen_context_payload={"screen_id": "dashboard", "displayed_data": {"health_score": 82}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 20


# ══════════════════════════════════════════════════════════════
# CATEGORY 2: Soil Health & Diagnostics
# ══════════════════════════════════════════════════════════════

def test_q05_soil_health_score_calculation():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my soil health score?",
        screen_context_payload={"screen_id": "soil", "displayed_data": {"soil_health_score": 78, "soil_health_category": "Good"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "78" in res.reply
    assert "good" in res.reply.lower() or "score" in res.reply.lower()


def test_q06_soil_nitrogen_evaluation():
    ctx = context_engine.build_context(
        user_id=None,
        query="My soil nitrogen is 140 kg/ha. Is that deficient or optimal?",
        screen_context_payload={"screen_id": "soil", "displayed_data": {"nitrogen": 140.0}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "140" in res.reply
    assert len(res.reply) > 30


def test_q07_soil_acidic_ph_amendment():
    ctx = context_engine.build_context(
        user_id=None,
        query="My soil pH is 5.2. What amendment should I apply?",
        screen_context_payload={"screen_id": "soil", "displayed_data": {"ph": 5.2}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "5.2" in res.reply
    assert "lime" in res.reply.lower() or "caco3" in res.reply.lower() or "acidic" in res.reply.lower()


def test_q08_soil_alkaline_ph_amendment():
    ctx = context_engine.build_context(
        user_id=None,
        query="My soil pH is 8.4. How should I treat it?",
        screen_context_payload={"screen_id": "soil", "displayed_data": {"ph": 8.4}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "8.4" in res.reply
    assert "gypsum" in res.reply.lower() or "alkaline" in res.reply.lower()


# ══════════════════════════════════════════════════════════════
# CATEGORY 3: Live Weather & Agro-Meteorology
# ══════════════════════════════════════════════════════════════

def test_q09_weather_current_temperature():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the current temperature and humidity?",
        screen_context_payload={"screen_id": "weather", "displayed_data": {"temp": 29.5, "humidity": 68.0, "district": "Guntur"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "29.5" in res.reply or "68" in res.reply or "Guntur" in res.reply


def test_q10_weather_pesticide_spraying_advisory():
    ctx = context_engine.build_context(
        user_id=None,
        query="Is it safe to spray pesticides today with this wind and rain?",
        screen_context_payload={"screen_id": "weather", "displayed_data": {"wind_speed": 18.0, "rainfall": 25.0}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 25
    assert "spray" in res.reply.lower() or "wind" in res.reply.lower() or "rain" in res.reply.lower()


def test_q11_weather_7day_rainfall_forecast():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my 7-day rainfall forecast?",
        screen_context_payload={"screen_id": "weather", "displayed_data": {"forecast_rainfall_7d": 42.0}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 25


def test_q12_weather_risk_assessment():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my agro-climatic weather risk level?",
        screen_context_payload={"screen_id": "weather", "displayed_data": {"predicted_risk_level": "Moderate", "confidence": 0.65}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 20


# ══════════════════════════════════════════════════════════════
# CATEGORY 4: Crop Recommendation & Alternatives
# ══════════════════════════════════════════════════════════════

def test_q13_crop_recommendation_identity():
    ctx = context_engine.build_context(
        user_id=None,
        query="What crop did the AI recommend for my farm?",
        screen_context_payload={"screen_id": "crop_recommendation", "displayed_data": {"recommended_crop": "Rice", "confidence": 0.94}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "rice" in res.reply.lower()


def test_q14_crop_recommendation_justification():
    ctx = context_engine.build_context(
        user_id=None,
        query="Why did the model recommend rice?",
        screen_context_payload={"screen_id": "crop_recommendation", "displayed_data": {"recommended_crop": "Rice", "nitrogen": 90, "rainfall": 200}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "rice" in res.reply.lower()
    assert len(res.reply) > 40


def test_q15_crop_alternative_options():
    ctx = context_engine.build_context(
        user_id=None,
        query="What alternative crops can I consider if I don't plant rice?",
        screen_context_payload={"screen_id": "crop_recommendation", "displayed_data": {"recommended_crop": "Rice", "alternatives": ["Maize", "Jute"]}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "rice" in res.reply.lower() or "maize" in res.reply.lower()


def test_q16_crop_recommendation_confidence():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the confidence score of this crop recommendation?",
        screen_context_payload={"screen_id": "crop_recommendation", "displayed_data": {"recommended_crop": "Cotton", "confidence": 0.88}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "88" in res.reply or "cotton" in res.reply.lower()


# ══════════════════════════════════════════════════════════════
# CATEGORY 5: Yield Prediction & Production Economics
# ══════════════════════════════════════════════════════════════

def test_q17_predicted_yield_rate():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my predicted yield per hectare?",
        screen_context_payload={"screen_id": "yield", "displayed_data": {"predicted_yield_t_ha": 3.45, "crop": "Rice"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "3.45" in res.reply or "yield" in res.reply.lower()


def test_q18_total_harvest_production():
    ctx = context_engine.build_context(
        user_id=None,
        query="How much total harvest can I expect from 3.5 acres?",
        screen_context_payload={"screen_id": "yield", "displayed_data": {"total_production_tonnes": 4.88, "acreage": 3.5}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "4.88" in res.reply or "total" in res.reply.lower()


def test_q19_climate_drought_impact():
    ctx = context_engine.build_context(
        user_id=None,
        query="How will a 20% drought affect my crop yield?",
        screen_context_payload={"screen_id": "yield", "displayed_data": {"drought_sensitivity": "Moderate", "crop": "Maize"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30


def test_q20_sustainability_rating():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is my farm sustainability score?",
        screen_context_payload={"screen_id": "dashboard", "displayed_data": {"sustainability_score": 42.5}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "42" in res.reply or "sustainability" in res.reply.lower()


# ══════════════════════════════════════════════════════════════
# CATEGORY 6: Precision Irrigation & Water Management
# ══════════════════════════════════════════════════════════════

def test_q21_irrigation_depth_requirement():
    ctx = context_engine.build_context(
        user_id=None,
        query="How much irrigation water does my crop require today?",
        screen_context_payload={"screen_id": "irrigation", "displayed_data": {"irrigation_depth_mm": 18.0, "crop": "Groundnut"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "18" in res.reply or "water" in res.reply.lower()


def test_q22_irrigation_total_liters():
    ctx = context_engine.build_context(
        user_id=None,
        query="How many liters of water should I pump for my field?",
        screen_context_payload={"screen_id": "irrigation", "displayed_data": {"water_volume_liters": 182109, "crop": "Groundnut"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "182" in res.reply or "liter" in res.reply.lower() or "water" in res.reply.lower()


def test_q23_irrigation_method_protocol():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the recommended irrigation method?",
        screen_context_payload={"screen_id": "irrigation", "displayed_data": {"irrigation_type": "Drip"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "drip" in res.reply.lower() or "irrigation" in res.reply.lower()


def test_q24_irrigation_soil_moisture_interaction():
    ctx = context_engine.build_context(
        user_id=None,
        query="My soil moisture is high at 80%. Should I irrigate?",
        screen_context_payload={"screen_id": "irrigation", "displayed_data": {"soil_moisture_pct": 80.0}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 25


# ══════════════════════════════════════════════════════════════
# CATEGORY 7: Market Intelligence & Price Forecasting
# ══════════════════════════════════════════════════════════════

def test_q25_market_tomato_tenali_price():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the forecast market price of Tomato in Tenali?",
        screen_context_payload={"screen_id": "market", "selected_crop": "Tomato"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "tomato" in res.reply.lower() or "tenali" in res.reply.lower()
    assert "₹" in res.reply


def test_q26_market_wheat_varanasi_price():
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the forecast market price of Wheat in Varanasi?",
        screen_context_payload={"screen_id": "market", "selected_crop": "Wheat"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "wheat" in res.reply.lower() or "varanasi" in res.reply.lower()
    assert "₹" in res.reply


def test_q27_market_observed_vs_predicted():
    ctx = context_engine.build_context(
        user_id=None,
        query="Explain the difference between observed price and predicted price",
        screen_context_payload={"screen_id": "market", "displayed_data": {"observed_market_price": 7180, "forecast_modal_price": 7240}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30


def test_q28_market_timing_advice():
    ctx = context_engine.build_context(
        user_id=None,
        query="Should I sell my harvest this week or wait for higher prices?",
        screen_context_payload={"screen_id": "market", "displayed_data": {"trend_direction": "UPWARD", "expected_change_pct": 3.2}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30


# ══════════════════════════════════════════════════════════════
# CATEGORY 8: Plant Disease Identification
# ══════════════════════════════════════════════════════════════

def test_q29_disease_diagnosed_condition():
    ctx = context_engine.build_context(
        user_id=None,
        query="What disease was identified on my tomato plant?",
        screen_context_payload={"screen_id": "disease", "displayed_data": {"predicted_class": "Tomato_Late_blight", "confidence_pct": 99.8}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "late blight" in res.reply.lower() or "tomato" in res.reply.lower()


def test_q30_disease_treatment_recommendation():
    ctx = context_engine.build_context(
        user_id=None,
        query="What fungicide should I use to treat Late Blight?",
        screen_context_payload={"screen_id": "disease", "displayed_data": {"predicted_class": "Tomato_Late_blight"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "fungicide" in res.reply.lower() or "metalaxyl" in res.reply.lower() or "spray" in res.reply.lower() or "blight" in res.reply.lower()


def test_q31_disease_confidence_level():
    ctx = context_engine.build_context(
        user_id=None,
        query="How reliable is this disease diagnosis?",
        screen_context_payload={"screen_id": "disease", "displayed_data": {"predicted_class": "Tomato_Late_blight", "confidence_pct": 99.8}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert "99" in res.reply or "confidence" in res.reply.lower() or "resnet50" in res.reply.lower()


def test_q32_disease_prevention_measures():
    ctx = context_engine.build_context(
        user_id=None,
        query="How can I prevent fungal disease from spreading in my field?",
        screen_context_payload={"screen_id": "disease", "displayed_data": {"crop": "Tomato"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30


# ══════════════════════════════════════════════════════════════
# CATEGORY 9: Telugu Language Support (తెలుగు)
# ══════════════════════════════════════════════════════════════

def test_q33_telugu_soil_health():
    ctx = context_engine.build_context(
        user_id=None,
        query="నా నేల ఆరోగ్యం ఎలా ఉంది?",
        screen_context_payload={"screen_id": "soil", "displayed_data": {"soil_health_score": 82, "soil_health_category": "Good"}},
        language="te",
    )
    res = langgraph_orchestrator.run(ctx)
    assert _has_telugu(res.reply), "Response must contain Telugu script"
    assert "82" in res.reply or "ఆరోగ్య" in res.reply


def test_q34_telugu_crop_recommendation():
    ctx = context_engine.build_context(
        user_id=None,
        query="నా పొలానికి ఏ పంట సిఫార్సు చేయబడింది?",
        screen_context_payload={"screen_id": "crop_recommendation", "displayed_data": {"recommended_crop": "Rice"}},
        language="te",
    )
    res = langgraph_orchestrator.run(ctx)
    assert _has_telugu(res.reply), "Response must contain Telugu script"
    assert "వరి" in res.reply or "rice" in res.reply.lower() or "పంట" in res.reply


def test_q35_telugu_market_price():
    ctx = context_engine.build_context(
        user_id=None,
        query="గోధుమ మార్కెట్ ధర అంచనా ఎంత?",
        screen_context_payload={"screen_id": "market", "selected_crop": "Wheat"},
        language="te",
    )
    res = langgraph_orchestrator.run(ctx)
    assert _has_telugu(res.reply), "Response must contain Telugu script"
    assert "₹" in res.reply


def test_q36_telugu_irrigation_requirement():
    ctx = context_engine.build_context(
        user_id=None,
        query="నా పంటకు ఎంత నీరు అవసరం?",
        screen_context_payload={"screen_id": "irrigation", "displayed_data": {"irrigation_depth_mm": 18.0, "water_volume_liters": 182109}},
        language="te",
    )
    res = langgraph_orchestrator.run(ctx)
    assert _has_telugu(res.reply), "Response must contain Telugu script"
    assert "18" in res.reply or "నీరు" in res.reply or "లీటర్" in res.reply


# ══════════════════════════════════════════════════════════════
# CATEGORY 10: Model Registry, PDF Reports & Multi-Agent
# ══════════════════════════════════════════════════════════════

def test_q37_model_registry_verification_status():
    ctx = context_engine.build_context(
        user_id=None,
        query="Which AI models are verified in KshetraIQ?",
        screen_context_payload={"screen_id": "registry"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30
    assert "model" in res.reply.lower() or "verified" in res.reply.lower()


def test_q38_pdf_report_contents():
    ctx = context_engine.build_context(
        user_id=None,
        query="What information is included in the generated PDF report?",
        screen_context_payload={"screen_id": "reports"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 30
    assert "report" in res.reply.lower() or "pdf" in res.reply.lower() or "soil" in res.reply.lower()


def test_q39_multi_agent_crop_and_market_synthesis():
    ctx = context_engine.build_context(
        user_id=None,
        query="What crop should I grow and what market price can I expect?",
        screen_context_payload={"screen_id": "dashboard", "displayed_data": {"recommended_crop": "Tomato", "mandi": "Tenali"}},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 40
    assert len(res.agents_used) >= 1


def test_q40_unknown_or_ambiguous_query_graceful_handling():
    ctx = context_engine.build_context(
        user_id=None,
        query="xyzabc123 qwerty random nonsense query",
        screen_context_payload={"screen_id": "dashboard"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)
    assert len(res.reply) > 10
    # Must never invent a fake price or hallucinated data
    assert "₹2,500" not in res.reply
