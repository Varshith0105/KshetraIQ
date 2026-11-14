from types import SimpleNamespace
from app.services.soil_health_service import SoilHealthService


def test_soil_health_five_bands():
    service = SoilHealthService()

    # 1. Excellent (all within optimal ranges)
    # N: 280-560 (e.g. 400), P: 10-25 (e.g. 18), K: 120-280 (e.g. 200), pH: 6.5-7.5 (e.g. 7.0)
    excellent_soil = {"nitrogen": 400, "phosphorus": 18, "potassium": 200, "ph": 7.0}
    res_exc = service.assess(excellent_soil)
    assert res_exc["score"] == 100.0
    assert res_exc["category"] == "Excellent"
    assert res_exc["badge_color"] == "green"
    assert len(res_exc["deficiencies"]) == 0
    assert len(res_exc["excesses"]) == 0

    # 2. Good (60 - 79)
    # Slight deficit in N: width=280, distance=56 -> 100*(1 - 56/280) = 80
    # Slight deficit in P: width=15, distance=4.5 -> 100*(1 - 4.5/15) = 70
    # K: optimal (100) -> average: (80 + 70 + 100 + 100) / 4 = 87.5
    # Let's test moderate N deficit: N=140 (distance=140/280=0.5 -> score 50), P=15 (100), K=200 (100), pH=7.0 (100)
    # Average: (50 + 100 + 100 + 100) / 4 = 87.5 -> Still excellent.
    # To get 70: N=70 (score 25), P=15 (100), K=120 (100), pH=6.0 (width 1.0, distance 0.5 -> score 50)
    # Average: (25 + 100 + 100 + 50) / 4 = 68.75 -> Good
    good_soil = {"nitrogen": 70, "phosphorus": 15, "potassium": 120, "ph": 6.0}
    res_good = service.assess(good_soil)
    assert 60 <= res_good["score"] < 80
    assert res_good["category"] == "Good"
    assert res_good["badge_color"] == "teal"

    # 3. Moderate (40 - 59)
    # N=0 (score 0), P=5 (width 15, distance 5 -> score 66.7), K=60 (width 160, distance 60 -> score 62.5), pH=5.8 (score 30)
    # Average: (0 + 66.7 + 62.5 + 30) / 4 = 39.8 -> let's tune for 45-55
    # N=70 (25), P=7 (80), K=60 (62.5), pH=5.8 (30) -> (25 + 80 + 62.5 + 30)/4 = 49.375 -> Moderate
    mod_soil = {"nitrogen": 70, "phosphorus": 7, "potassium": 60, "ph": 5.8}
    res_mod = service.assess(mod_soil)
    assert 40 <= res_mod["score"] < 60
    assert res_mod["category"] == "Moderate"
    assert res_mod["badge_color"] == "amber"

    # 4. Poor (20 - 39)
    # N=0 (0), P=2 (width 15, dist 8 -> score 46.7), K=20 (width 160, dist 100 -> score 37.5), pH=5.5 (0)
    # Average: (0 + 46.7 + 37.5 + 0)/4 = 21.05 -> Poor
    poor_soil = {"nitrogen": 0, "phosphorus": 2, "potassium": 20, "ph": 5.5}
    res_poor = service.assess(poor_soil)
    assert 20 <= res_poor["score"] < 40
    assert res_poor["category"] == "Poor"
    assert res_poor["badge_color"] == "orange"

    # 5. Critical (0 - 19)
    # N=0 (0), P=0 (0), K=0 (0), pH=4.0 (0)
    critical_soil = {"nitrogen": 0, "phosphorus": 0, "potassium": 0, "ph": 4.0}
    res_crit = service.assess(critical_soil)
    assert 0 <= res_crit["score"] < 20
    assert res_crit["category"] == "Critical"
    assert res_crit["badge_color"] == "red"


def test_recommendations_and_telugu_support():
    service = SoilHealthService()
    soil = {"nitrogen": 100, "phosphorus": 5, "potassium": 50, "ph": 5.2}
    res = service.assess(soil)
    assert len(res["recommendations"]) > 0
    assert len(res["recommendations_te"]) > 0
    assert "Nitrogen is deficient" in res["recommendations"][0]
    assert "నత్రజని లోపం ఉంది" in res["recommendations_te"][0]
    assert any("pH is acidic" in r for r in res["recommendations"])
