import json
from pathlib import Path
import pytest
from app.core.config import get_settings
from app.services.crop_recommender import CropRecommender, CROP_NAMES_TE


@pytest.fixture(scope="module")
def crop_recommender():
    settings = get_settings()
    recommender = CropRecommender(settings.resolved_model_directory)
    assert recommender.is_available, f"Crop recommendation model failed to load: {recommender.load_error}"
    return recommender


@pytest.fixture(scope="module")
def fixture_cases():
    fixture_path = Path(__file__).parent / "fixtures" / "crop_recommendation_cases.json"
    assert fixture_path.exists(), f"Crop recommendation test fixtures missing at {fixture_path}"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def test_crop_recommender_classes_count(crop_recommender):
    """Verify that the model has all 22 expected agricultural crop classes."""
    assert len(crop_recommender._classes) == 22
    assert "rice" in crop_recommender._classes
    assert "coffee" in crop_recommender._classes
    assert "maize" in crop_recommender._classes
    assert "cotton" in crop_recommender._classes


def test_all_22_fixture_cases(crop_recommender, fixture_cases):
    """Execute real loaded model against all 22 diverse agronomic test cases."""
    assert len(fixture_cases) >= 20, "Must contain at least 20 diverse test cases"
    
    unique_crops_recommended = set()

    for case in fixture_cases:
        inputs = case["inputs"]
        result = crop_recommender.predict(
            n=inputs["N"],
            p=inputs["P"],
            k=inputs["K"],
            temperature=inputs["temperature"],
            humidity=inputs["humidity"],
            ph=inputs["ph"],
            rainfall=inputs["rainfall"],
        )

        assert result.recommended_crop == case["expected_crop"], (
            f"Case {case['id']} expected {case['expected_crop']} but got {result.recommended_crop}"
        )
        assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence {result.confidence}"
        assert abs(result.confidence - case["model_confidence"]) < 0.05
        assert len(result.top_candidates) >= 1
        assert result.top_candidates[0].crop == result.recommended_crop
        assert result.recommended_crop_te != ""
        unique_crops_recommended.add(result.recommended_crop)

    # Confirm that recommendations are diverse across the suite and not stuck on one crop
    assert len(unique_crops_recommended) == len(fixture_cases)
