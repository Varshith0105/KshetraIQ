import pytest
from app.services.weather_service import WeatherService


def test_weather_geocoding_and_observations_live():
    """Verify live Open-Meteo observations for Guntur, Andhra Pradesh."""
    ws = WeatherService()
    obs, source = ws.fetch_weather_for_location("Guntur", "Andhra Pradesh", "kharif")
    assert obs is not None, "Weather observations should not be None for Guntur"
    assert obs.temperature_c is not None and -10.0 < obs.temperature_c < 60.0
    assert obs.humidity_percent is not None and 0.0 <= obs.humidity_percent <= 100.0
    assert obs.rainfall_mm is not None and obs.rainfall_mm >= 0.0
    assert "open_meteo" in source


def test_weather_7day_forecast_live():
    """Verify 7-day forecast retrieval for Warangal, Telangana."""
    ws = WeatherService()
    fc = ws.fetch_7day_forecast("Warangal", "Telangana")
    assert fc is not None, "Forecast should be retrieved"
    assert "current" in fc
    assert "daily" in fc
    daily = fc["daily"]
    assert "temperature_2m_max" in daily
    assert len(daily.get("time", [])) >= 7


def test_unsupported_or_fake_location_graceful_handling():
    """Verify unknown location does not invent fake coordinates."""
    ws = WeatherService()
    obs, source = ws.fetch_weather_for_location("AtlantisFictionalDistrict", "AtlantisState", "kharif")
    assert obs is None
    assert source in ("location_not_found", "rate_limited")

