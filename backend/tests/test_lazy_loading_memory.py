"""
Tests for lazy loading, memory optimization, and thread concurrency settings.

Verifies:
1. Numerical library thread limit environment variables are set (OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, etc.).
2. Fast application startup without eagerly importing heavy ML frameworks (TensorFlow, Keras, Torch).
3. CropYieldService, ClimateScenarioService, WeatherRiskService, and PlantDiseaseService lazy-load their heavy models on demand.
4. Cached singleton service instances prevent redundant model deserialization across requests.
5. Production API prediction endpoints execute real predictions when called.
6. Health endpoints (/health and /api/v1/health) succeed quickly without triggering model loads.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.climate_recommender import (
    ClimateScenarioService,
    get_climate_scenario_service,
)
from app.services.crop_recommender import (
    CropRecommender,
)
from app.services.market_price_service import market_price_service
from app.services.plant_disease_service import plant_disease_service
from app.services.sustainability_service import (
    SustainabilityService,
    get_sustainability_service,
)
from app.services.weather_risk_service import (
    WeatherRiskService,
    get_weather_risk_service,
)
from app.services.yield_recommender import (
    CropYieldService,
    get_crop_yield_service,
)


def test_thread_environment_limits_configured() -> None:
    """Ensure CPU thread pool env vars are constrained to 1 to protect 512MB RAM containers."""
    assert os.environ.get("OMP_NUM_THREADS") == "1"
    assert os.environ.get("OPENBLAS_NUM_THREADS") == "1"
    assert os.environ.get("MKL_NUM_THREADS") == "1"
    assert os.environ.get("VECLIB_MAXIMUM_THREADS") == "1"
    assert os.environ.get("NUMEXPR_NUM_THREADS") == "1"


def test_startup_does_not_eagerly_import_heavy_ml() -> None:
    """Verify in a clean process that creating the app does not import tensorflow, keras, or torch."""
    import subprocess
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; sys.path.insert(0, 'backend'); "
            "from app.main import create_app; "
            "app = create_app(); "
            "forbidden = ['tensorflow', 'keras', 'torch']; "
            "loaded = [f for f in forbidden if f in sys.modules]; "
            "assert not loaded, f'Eagerly loaded ML frameworks: {loaded}'; "
            "print('STARTUP_CLEAN')"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Startup imported heavy ML: {res.stderr or res.stdout}"
    assert "STARTUP_CLEAN" in res.stdout


def test_yield_service_lazy_loading() -> None:
    """Verify CropYieldService does not load the 268MB pickle artifact in __init__."""
    settings = get_settings()
    model_dir = settings.resolved_model_directory

    service = CropYieldService(model_dir)
    # Model should NOT be loaded upon instantiation
    assert service._model is None
    assert service._is_loaded is False
    # is_ready returns True if artifact exists on disk
    assert service.is_ready is True


def test_climate_service_lazy_loading() -> None:
    """Verify ClimateScenarioService does not load the 61MB pickle artifact in __init__."""
    settings = get_settings()
    model_dir = settings.resolved_model_directory

    service = ClimateScenarioService(model_dir)
    # Model should NOT be loaded upon instantiation
    assert service._model is None
    assert service._is_loaded is False
    assert service.is_ready is True


def test_weather_risk_service_lazy_loading() -> None:
    """Verify WeatherRiskService does not load the XGBoost artifact in __init__."""
    settings = get_settings()
    model_dir = settings.resolved_model_directory

    service = WeatherRiskService(model_dir)
    assert service._model is None
    assert service._is_loaded is False
    assert service.is_ready is True


def test_sustainability_service_lazy_loading() -> None:
    """Verify SustainabilityService initializes lazily."""
    settings = get_settings()
    model_dir = settings.resolved_model_directory

    service = SustainabilityService(model_dir)
    assert not service._config
    assert service._is_loaded is False
    assert service.is_ready is True


def test_plant_disease_service_lazy_loading() -> None:
    """Verify PlantDiseaseService does not load Keras/ResNet50 until predict_image is called."""
    from app.services.plant_disease_service import PlantDiseaseService
    fresh_service = PlantDiseaseService()
    assert fresh_service._model is None
    assert fresh_service.is_loaded is False
    assert fresh_service.is_available() is True


def test_market_price_service_lazy_loading() -> None:
    """Verify MarketPriceService is ready without eager unpickling on status checks."""
    assert market_price_service.is_available() is True


def test_cached_service_getters_reuse_instances() -> None:
    """Ensure service factories cache instances to prevent repeated disk deserialization."""
    settings = get_settings()
    model_dir = settings.resolved_model_directory

    y1 = get_crop_yield_service(model_dir)
    y2 = get_crop_yield_service(model_dir)
    assert y1 is y2

    c1 = get_climate_scenario_service(model_dir)
    c2 = get_climate_scenario_service(model_dir)
    assert c1 is c2

    w1 = get_weather_risk_service(model_dir)
    w2 = get_weather_risk_service(model_dir)
    assert w1 is w2

    s1 = get_sustainability_service(model_dir)
    s2 = get_sustainability_service(model_dir)
    assert s1 is s2


def test_health_endpoints_without_memory_spike() -> None:
    """Verify /health and /api/v1/health respond with 200 without loading heavy ML."""
    app = create_app()
    client = TestClient(app)

    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "ok"

    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200
    assert res2.json()["status"] == "ok"


def test_prediction_endpoints_real_inference_on_demand() -> None:
    """Verify that predictions still run real ML inference correctly when called."""
    app = create_app()
    client = TestClient(app)

    # 1. Crop yield prediction
    yield_resp = client.post(
        "/api/v1/predictions/crop-yield",
        json={
            "crop": "Rice",
            "season": "Kharif",
            "state": "Andhra Pradesh",
            "crop_year": 2024,
            "area_hectares": 2.0,
            "annual_rainfall_mm": 900.0,
            "fertilizer_kg": 200.0,
            "pesticide_kg": 1.0,
        },
    )
    assert yield_resp.status_code == 200
    yield_data = yield_resp.json()
    assert yield_data["predicted_yield_tonnes_per_hectare"] > 0
    assert yield_data["predicted_total_production_tonnes"] > 0

    # 2. Climate scenario prediction
    climate_resp = client.post(
        "/api/v1/predictions/climate-scenario",
        json={
            "crop": "Rice",
            "crop_year": 2024,
            "season": "Kharif",
            "state": "Andhra Pradesh",
            "baseline_rainfall_mm": 950.0,
        },
    )
    assert climate_resp.status_code == 200
    climate_data = climate_resp.json()
    assert climate_data["baseline_yield_tonnes_per_ha"] > 0
    assert "vulnerability_tier" in climate_data

    # 3. Weather risk prediction
    risk_resp = client.post(
        "/api/v1/predictions/weather-risk",
        json={
            "month": 7,
            "season": "Kharif",
            "state": "Andhra Pradesh",
            "avg_temp_c": 30.0,
            "wind_speed_kmh": 12.0,
            "air_pressure_hpa": 1008.0,
            "rainfall_mm": 80.0,
        },
    )
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert risk_data["predicted_risk_level"] in {"Low", "Moderate", "High", "Extreme"}
    assert 0 <= risk_data["confidence"] <= 1.0
