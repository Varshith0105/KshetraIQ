from types import SimpleNamespace

import pytest

from app.services.market_price_service import MarketPriceService
from app.services.soil_health_service import SoilHealthService


def test_market_never_returns_generic_2500_baseline(tmp_path):
    service = MarketPriceService(db_path=tmp_path / "market.db")
    service._ensure_loaded()
    crop = next(iter(service._crop_lookup.values()))
    mandi = next(iter(service._mandi_lookup.values()))
    # No live/cache/curated benchmark for this synthetic pair must be explicit,
    # rather than returning the legacy 2500 / 2024-01-01 fabricated observation.
    with pytest.raises(ValueError, match="No verified market observation"):
        service.get_latest_observation(crop, mandi)


def test_soil_score_excludes_missing_measurements():
    soil = SimpleNamespace(nitrogen_kg_ha=280, phosphorus_kg_ha=None, potassium_kg_ha=None, ph=7.0, soil_moisture_percent=None)
    outcome = SoilHealthService().assess(soil)
    assert outcome["score"] == 100.0
    assert outcome["is_provisional"] is True
    assert outcome["parameters"]["phosphorus_kg_ha"]["score"] is None


def test_soil_score_reports_parameter_deficiency():
    soil = SimpleNamespace(nitrogen_kg_ha=100, phosphorus_kg_ha=15, potassium_kg_ha=200, ph=7.0, soil_moisture_percent=40)
    outcome = SoilHealthService().assess(soil)
    assert "Nitrogen" in outcome["deficiencies"]
    assert outcome["score"] is not None
