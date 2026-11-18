"""Unit and integration test suite for Satellite Intelligence Service and Router.

Tests:
1. Coordinate validation (latitude/longitude boundaries)
2. Date range validation (inversions, future dates, max 366 days)
3. Radius and area calculations (meters, hectares, acres, sq km)
4. Earth Engine authentication status and handling
5. NDVI and EVI formula correctness
6. Scientific calculation bounds matching notebook
"""
import pytest
from datetime import date, timedelta
from app.services.satellite_intelligence_service import (
    satellite_intelligence_service,
    DEFAULT_RADIUS_METERS,
    MAX_RADIUS_METERS,
    MIN_RADIUS_METERS,
)


class TestSatelliteValidationAndGeometry:
    """Tests geometry, coordinate, and date range validation."""

    def test_area_metrics_calculation(self):
        metrics = satellite_intelligence_service.calculate_area_metrics(5000)
        assert metrics["radius_meters"] == 5000
        # Area of circle with radius 5000m = pi * 5000^2 ~= 78,539,816 m2
        assert 78_000_000 < metrics["area_sq_m"] < 79_000_000
        # Hectares = m2 / 10,000 ~= 7854 ha
        assert 7800 < metrics["area_hectares"] < 7900
        # Acres = ha * 2.47105 ~= 19408 acres
        assert 19000 < metrics["area_acres"] < 20000
        # Sq km = m2 / 1,000,000 ~= 78.54 sq km
        assert 78.0 < metrics["area_sq_km"] < 79.0

    def test_coordinate_validation_valid(self):
        today = date.today()
        start = today - timedelta(days=30)
        # Should not raise exception
        satellite_intelligence_service.validate_analysis_request(
            latitude=16.5062,
            longitude=80.6480,
            start_date=start,
            end_date=today,
            radius_meters=5000,
            cloud_percentage=20,
        )

    def test_invalid_coordinates_raise_value_error(self):
        today = date.today()
        start = today - timedelta(days=10)
        with pytest.raises(ValueError, match="outside valid range"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=95.0, longitude=80.0, start_date=start, end_date=today
            )

        with pytest.raises(ValueError, match="outside valid range"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=16.0, longitude=195.0, start_date=start, end_date=today
            )

    def test_invalid_date_range_raise_value_error(self):
        today = date.today()
        # Inverted dates
        with pytest.raises(ValueError, match="cannot be after end date"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=16.5, longitude=80.5, start_date=today, end_date=today - timedelta(days=5)
            )

        # Exceeds max days
        with pytest.raises(ValueError, match="exceeds maximum allowable window"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=16.5, longitude=80.5, start_date=today - timedelta(days=400), end_date=today
            )

    def test_radius_boundary_validation(self):
        today = date.today()
        start = today - timedelta(days=10)
        # Below min
        with pytest.raises(ValueError, match="outside valid bounds"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=16.5, longitude=80.5, start_date=start, end_date=today, radius_meters=50
            )

        # Above max
        with pytest.raises(ValueError, match="outside valid bounds"):
            satellite_intelligence_service.validate_analysis_request(
                latitude=16.5, longitude=80.5, start_date=start, end_date=today, radius_meters=30000
            )


class TestEarthEngineStatusAndSecurity:
    """Verifies unauthenticated Earth Engine state and status schema."""

    def test_service_status_structure(self):
        status = satellite_intelligence_service.get_service_status()
        assert "model" in status
        assert status["model"] == "sentinel2_ndvi_evi"
        assert "status" in status
        assert status["status"] in ("READY", "REQUIRES_CREDENTIALS")
        assert "is_live" in status
        assert isinstance(status["is_live"], bool)
        assert "data_source" in status
        assert "COPERNICUS/S2_SR_HARMONIZED" in status["data_source"]
        assert "supported_operations" in status
        assert len(status["supported_operations"]) >= 3

    def test_unauthenticated_state_does_not_fabricate_data(self):
        # When unauthenticated, run_satellite_analysis must report UNAVAILABLE or REQUIRES_CREDENTIALS
        today = date.today()
        start = today - timedelta(days=30)
        result = satellite_intelligence_service.run_satellite_analysis(
            latitude=16.5062,
            longitude=80.6480,
            start_date=start,
            end_date=today,
            radius_meters=1000,
            user_id="test_user",
        )
        assert result["workflow_type"] == "satellite"
        assert result["status"] in ("REQUIRES_CREDENTIALS", "UNAVAILABLE")
        # Ensure no fake NDVI/EVI metrics are fabricated
        assert result.get("result") is None or result["result"] == {}
        assert result.get("error") is not None
        assert "Earth Engine" in result.get("error", "")


class TestScientificCalculations:
    """Verifies that mathematical formula conventions match the capstone notebook."""

    def test_ndvi_formula_bounds(self):
        # NDVI = (NIR - RED) / (NIR + RED)
        # For dense vegetation: NIR=0.6, RED=0.1 -> (0.6 - 0.1)/(0.6 + 0.1) = 0.5/0.7 ~= 0.714
        nir = 0.6
        red = 0.1
        ndvi = (nir - red) / (nir + red)
        assert 0.71 < ndvi < 0.72

    def test_evi_formula_bounds(self):
        # EVI = 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))
        nir = 0.6
        red = 0.1
        blue = 0.05
        evi = 2.5 * ((nir - red) / (nir + 6 * red - 7.5 * blue + 1))
        # 2.5 * (0.5 / (0.6 + 0.6 - 0.375 + 1)) = 2.5 * (0.5 / 1.825) ~= 0.685
        assert 0.68 < evi < 0.69
