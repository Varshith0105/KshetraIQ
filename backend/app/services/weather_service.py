"""
Weather Service — improvements:
1. Add User-Agent header (Open-Meteo ToS request)
2. Handle 429 rate limit with graceful unavailable response
3. Improve geocoding for new merged districts (search by state when district not found)
4. Add 7-day forecast endpoint (WeatherView in dashboard)
5. Cache last successful response per location to survive short rate-limit windows
"""
import logging
from typing import Any

import httpx

from app.schemas.assessment import WeatherObservations

logger = logging.getLogger(__name__)

# Typical seasonal rainfall normalizers by season in mm if daily forecast doesn't cover seasonal scale
SEASONAL_RAINFALL_DEFAULTS: dict[str, float] = {
    "kharif": 650.0,
    "rabi": 180.0,
    "zaid": 90.0,
    "summer": 90.0,
    "perennial": 400.0,
}

# District name → known headquarters town used for geocoding when the district
# itself is not indexed by Open-Meteo (typically post-2022 bifurcated districts)
DISTRICT_GEOCODING_OVERRIDES: dict[str, str] = {
    # Andhra Pradesh new districts
    "Alluri Sitharama Raju": "Paderu",
    "Anakapalli": "Anakapalle",
    "Annamayya": "Rajampet",
    "Dr. B.R. Ambedkar Konaseema": "Amalapuram",
    "Bapatla": "Bapatla",
    "Eluru": "Eluru",
    "Nandyal": "Nandyal",
    "NTR": "Vijayawada",
    "Palnadu": "Narasaraopet",
    "Sri Sathya Sai": "Puttaparthi",
    "Sri Balaji": "Tirupati",
    "Tirupati": "Tirupati",
    # Telangana new districts
    "Sangareddy": "Sangareddy",
    "Vikarabad": "Vikarabad",
    "Medchal Malkajgiri": "Medchal",
    "Yadadri Bhongir": "Bhongir",
    "Yadadri Bhuvanagiri": "Bhongir",
    "Rangareddy": "Hyderabad",
    "Mulugu": "Mulugu",
    "Narayanpet": "Mahabubnagar",
    # Other common issues
    "S.P.S. Nellore": "Nellore",
    "Y.S.R.": "Kadapa",
}

_HEADERS = {
    "User-Agent": "KshetraIQ-AgriPlatform/1.0 (https://kshetraiq.in; contact@kshetraiq.in)"
}


def _normalise_place(value: str) -> str:
    return " ".join(value.replace("-", " ").split()).casefold()


class WeatherService:
    """Service to fetch verified weather observations from Open-Meteo with fallback."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.timeout = timeout_seconds
        # Simple in-memory cache: key → (WeatherObservations, source_str)
        self._cache: dict[str, tuple[WeatherObservations, str]] = {}
        # In-memory cache for full 7-day forecast responses
        self._forecast_cache: dict[str, dict[str, Any]] = {}

    def _geocode(self, client: httpx.Client, district: str, state: str) -> tuple[float, float] | None:
        """
        Geocode a district name to (lat, lon). Tries:
        1. Direct district name lookup filtered to India + matching state
        2. Known override (district headquarters town)
        """
        search_names = [district]
        override = next(
            (
                value
                for key, value in DISTRICT_GEOCODING_OVERRIDES.items()
                if _normalise_place(key) == _normalise_place(district)
            ),
            None,
        )
        if override:
            search_names.append(override)

        requested_state = _normalise_place(state)

        for search_name in search_names:
            try:
                geo_resp = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": search_name, "count": 10, "language": "en", "format": "json"},
                )
                if geo_resp.status_code != 200:
                    logger.warning("Geocoding HTTP %d for %r", geo_resp.status_code, search_name)
                    continue

                geo_data = geo_resp.json()
                results = geo_data.get("results") or []
                india_results = [r for r in results if r.get("country_code") == "IN"]
                if not india_results:
                    india_results = results  # fallback if country_code not tagged

                if not india_results:
                    continue

                # Never use a result from another state: same-named places are
                # common, and a wrong location is worse than unavailable data.
                location = next(
                    (
                        r
                        for r in india_results
                        if _normalise_place(str(r.get("admin1", ""))) == requested_state
                    ),
                    None,
                )
                if location is None:
                    continue
                lat = location.get("latitude")
                lon = location.get("longitude")
                if lat is not None and lon is not None:
                    return float(lat), float(lon)
            except Exception as exc:
                logger.warning("Geocode attempt %r failed: %s", search_name, exc)

        return None

    def fetch_weather_for_location(
        self,
        district: str,
        state: str,
        season: str = "kharif",
    ) -> tuple[WeatherObservations | None, str]:
        """Fetch temperature, relative humidity, and rainfall estimate for a district."""
        cache_key = f"{district.lower()}|{state.lower()}|{season.lower()}"

        try:
            with httpx.Client(timeout=self.timeout, headers=_HEADERS) as client:
                coords = self._geocode(client, district, state)
                if coords is None:
                    logger.info("Geocoding found no result for %s, %s", district, state)
                    return self._cache.get(cache_key, (None, "location_not_found"))

                lat, lon = coords

                weather_resp = client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 7,
                    },
                )

                if weather_resp.status_code == 429:
                    logger.warning("Open-Meteo rate limit hit for %s, %s (429). Returning cached data if available.", district, state)
                    if cache_key in self._cache:
                        obs, src = self._cache[cache_key]
                        return obs, f"{src}_cached"
                    return None, "rate_limited"

                if weather_resp.status_code != 200:
                    logger.warning("Open-Meteo forecast HTTP %d for %s, %s", weather_resp.status_code, district, state)
                    return self._cache.get(cache_key, (None, "weather_api_error"))

                weather_data = weather_resp.json()
                current = weather_data.get("current", {})
                temp = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")
                wind_speed = current.get("wind_speed_10m")
                weather_code = current.get("weather_code")

                daily = weather_data.get("daily", {})
                precip_sums = daily.get("precipitation_sum") or []
                forecast_rain = sum(x for x in precip_sums if x is not None)

                season_key = season.lower().strip()
                seasonal_ref = SEASONAL_RAINFALL_DEFAULTS.get(season_key, 200.0)
                # Weighted combination: 75% seasonal benchmark + 25% observed weekly tendency scaled
                combined_rainfall = round(seasonal_ref * 0.75 + (forecast_rain * 4.0), 1)

                if temp is not None and humidity is not None:
                    obs = WeatherObservations(
                        temperature_c=round(float(temp), 1),
                        humidity_percent=round(float(humidity), 1),
                        rainfall_mm=float(combined_rainfall),
                    )
                    self._cache[cache_key] = (obs, "open_meteo_current_plus_7_day_forecast")
                    forecast_key = f"{district.lower()}|{state.lower()}|forecast7"
                    self._forecast_cache[forecast_key] = {
                        "latitude": lat,
                        "longitude": lon,
                        "current": current,
                        "daily": daily,
                        "timezone": weather_data.get("timezone", "Asia/Kolkata"),
                        "location_name": district,
                        "state": state,
                        "source": "open_meteo_live",
                    }
                    return obs, "open_meteo_current_plus_7_day_forecast"

                return None, "incomplete_weather_data"

        except Exception as exc:
            logger.info("Open-Meteo weather fetch skipped or failed (%s, %s): %s", district, state, exc)
            if cache_key in self._cache:
                obs, src = self._cache[cache_key]
                return obs, f"{src}_cached"
            return None, f"network_error: {exc}"

    def fetch_7day_forecast(
        self,
        district: str,
        state: str,
    ) -> dict[str, Any] | None:
        """Return a 7-day daily forecast dict for the WeatherView panel with cache fallback."""
        forecast_key = f"{district.lower()}|{state.lower()}|forecast7"
        if forecast_key in self._forecast_cache:
            return self._forecast_cache[forecast_key]

        try:
            with httpx.Client(timeout=self.timeout, headers=_HEADERS) as client:
                coords = self._geocode(client, district, state)
                if coords is None:
                    return None

                lat, lon = coords
                weather_resp = client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 7,
                    },
                )

                if weather_resp.status_code == 429:
                    if forecast_key in self._forecast_cache:
                        cached = dict(self._forecast_cache[forecast_key])
                        cached["source"] = "open_meteo_cached"
                        return cached
                    return None
                if weather_resp.status_code != 200:
                    if forecast_key in self._forecast_cache:
                        return self._forecast_cache[forecast_key]
                    return None

                data = weather_resp.json()
                res = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": data.get("current"),
                    "daily": data.get("daily"),
                    "timezone": data.get("timezone", "Asia/Kolkata"),
                    "location_name": district,
                    "state": state,
                    "source": "open_meteo_live",
                }
                self._forecast_cache[forecast_key] = res
                return res
        except Exception as exc:
            logger.info("7-day forecast failed (%s, %s): %s", district, state, exc)
            return self._forecast_cache.get(forecast_key)


weather_service = WeatherService()

