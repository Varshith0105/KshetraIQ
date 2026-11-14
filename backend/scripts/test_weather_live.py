import httpx

headers = {"User-Agent": "KshetraIQ-AgriPlatform/1.0 (https://kshetraiq.in; contact@kshetraiq.in)"}

with httpx.Client(timeout=10.0, headers=headers) as client:
    geo_resp = client.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": "Guntur", "count": 10, "language": "en", "format": "json"},
    )
    print("Geocoding status:", geo_resp.status_code)
    geo_data = geo_resp.json()
    results = geo_data.get("results", [])
    print("Found results:", len(results))
    
    # Filter India and Andhra Pradesh
    target = next((r for r in results if r.get("country_code") == "IN" and "andhra" in r.get("admin1", "").lower()), results[0])
    print("Target:", target.get("name"), target.get("admin1"), target.get("latitude"), target.get("longitude"))

    weather_resp = client.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": target.get("latitude"),
            "longitude": target.get("longitude"),
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "Asia/Kolkata",
            "forecast_days": 7,
        },
    )
    print("Weather status:", weather_resp.status_code)
    if weather_resp.status_code == 200:
        w = weather_resp.json()
        print("Current:", w.get("current"))
        print("Daily times:", w.get("daily", {}).get("time"))
        print("Daily max:", w.get("daily", {}).get("temperature_2m_max"))
        print("Daily precip:", w.get("daily", {}).get("precipitation_sum"))
    else:
        print("Weather error:", weather_resp.text)
