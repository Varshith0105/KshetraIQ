import urllib.request
import urllib.error
import json

urls = [
    ("Health", "http://127.0.0.1:8000/health"),
    ("Weather Lookup (Guntur)", "http://127.0.0.1:8000/api/v1/weather/lookup?district=Guntur&state=Andhra%20Pradesh&season=kharif"),
    ("Weather Lookup (Palnadu)", "http://127.0.0.1:8000/api/v1/weather/lookup?district=Palnadu&state=Andhra%20Pradesh&season=kharif"),
    ("Weather 7-Day Forecast", "http://127.0.0.1:8000/api/v1/weather/forecast?district=Guntur&state=Andhra%20Pradesh"),
    ("Google Auth URL", "http://127.0.0.1:8000/api/v1/auth/google/url"),
    ("Locations States", "http://127.0.0.1:8000/api/v1/locations/states"),
    ("Frontend Landing", "http://127.0.0.1:3000/"),
    ("Frontend Dashboard", "http://127.0.0.1:3000/dashboard"),
    ("Frontend Login", "http://127.0.0.1:3000/login"),
]

for label, url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmokeTest"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read().decode("utf-8")
            extra = ""
            if "weather" in url or "google" in url:
                try:
                    js = json.loads(data)
                    if "status" in js:
                        extra = f" [status={js.get('status')}, temp={js.get('temperature_c')}C, rain={js.get('rainfall_mm')}mm]"
                    elif "configured" in js:
                        extra = f" [configured={js.get('configured')}, redirect_uri in url={'127.0.0.1%3A3000' in js.get('url', '')}]"
                except Exception:
                    pass
            print(f"[PASS] {resp.status} - {label}{extra}")
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] - {label}: {url}")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
