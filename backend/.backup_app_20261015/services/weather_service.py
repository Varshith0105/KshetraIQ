import logging
from typing import Any

import httpx

from app.schemas.assessment import WeatherObservations

logger = logging.getLogger(__name__)

# Typical seasonal rainfall normalizers by season in mm if daily forecast doesn't cover seasonal scale
SEASONAL_RAINFALL_DEFAULTS: dict[str, float] = {
    "kharif": 650.0,
    "rabi": 180.0,
    "summer": 90.0,
}


class WeatherService:
    """Service to fetch verified weather observations from Open-Meteo with fallback."""

    def __init__(self, timeout_seconds: float = 4.0) -> None:
        self.timeout = timeout_seconds

    def fetch_weather_for_location(
        self,
        district: str,
        state: str,
        season: str = "kharif",
    ) -> tuple[WeatherObservations | None, str]:
        """Fetch temperature, relative humidity, and rainfall estimate for a district."""
        query = f"{district.strip()}, {state.strip()}, India"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                geo_resp = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": district.strip(), "count": 1, "language": "en", "format": "json"},
                )
                if geo_resp.status_code != 200:
                    logger.warning("Geocoding failed for %s with status %d", query, geo_resp.status_code)
                    return None, "geocoding_failed"

                geo_data = geo_resp.json()
                results = geo_data.get("results")
                if not results:
                    return None, "location_not_found"

                lat = results[0]["latitude"]
                lon = results[0]["longitude"]

                weather_resp = client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,precipitation",
                        "daily": "precipitation_sum",
                        "timezone": "auto",
                        "forecast_days": 7,
                    },
                )
                if weather_resp.status_code != 200:
                    return None, "weather_api_error"

                weather_data = weather_resp.json()
                current = weather_data.get("current", {})
                temp = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")

                daily = weather_data.get("daily", {})
                precip_sums = daily.get("precipitation_sum", [])
                forecast_rain = sum(precip_sums) if precip_sums else 0.0

                # Crop recommendation was trained on seasonal rainfall values (mm),
                # so if only 7-day forecast is returned, combine with typical seasonal reference
                season_key = season.lower().strip()
                seasonal_ref = SEASONAL_RAINFALL_DEFAULTS.get(season_key, 200.0)
                # Weighted combination: 80% seasonal benchmark + 20% observed weekly tendency * scale
                combined_rainfall = round(seasonal_ref * 0.75 + (forecast_rain * 4.0), 1)

                if temp is not None and humidity is not None:
                    return WeatherObservations(
                        temperature_c=round(float(temp), 1),
                        humidity_percent=round(float(humidity), 1),
                        rainfall_mm=float(combined_rainfall),
                    ), "open_meteo_live"

                return None, "incomplete_weather_data"

        except Exception as exc:
            logger.info("Open-Meteo weather fetch skipped or failed (%s): %s", query, exc)
            return None, f"network_error: {exc}"
