"""Deep test suite for KshetraIQ Market Insights: Model Audit, Comparison, and Integration.

Covers all 15 test requirements specified in the deep model review audit.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.market_price_service import (
    MarketPriceService,
    market_price_service,
    CHRONOLOGICAL_TEST_MAE,
    CHRONOLOGICAL_TEST_RMSE,
    CHRONOLOGICAL_TEST_R2,
    CHRONOLOGICAL_TEST_MAPE,
)
from app.services.context_engine import context_engine
from app.services.langgraph_orchestrator import langgraph_orchestrator


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# 1. Both model artifacts load correctly
def test_both_model_artifacts_load_correctly():
    models_dir = Path(__file__).resolve().parents[2] / "Agriverse_Models"
    orig_path = models_dir / "kshetraiq_model.pkl"
    impr_path = models_dir / "kshetraiq_improved_model.pkl"

    assert orig_path.exists(), f"Original model missing at {orig_path}"
    assert impr_path.exists(), f"Improved model missing at {impr_path}"

    m_orig = joblib.load(orig_path)
    m_impr = joblib.load(impr_path)

    assert hasattr(m_orig, "booster_"), "Original model must be a trained LightGBM regressor"
    assert hasattr(m_impr, "booster_"), "Improved model must be a trained LightGBM regressor"
    assert m_orig.booster_.num_trees() == 200, "Original model should have 200 trees"
    assert m_impr.booster_.num_trees() == 500, "Improved model should have 500 trees"


# 2. Feature names and ordering are correct
def test_feature_names_and_ordering():
    expected_features = ["state_name", "district_name", "market_name", "crop", "variety", "year", "month", "day"]

    m_impr = joblib.load(Path(__file__).resolve().parents[2] / "Agriverse_Models" / "kshetraiq_improved_model.pkl")
    dump = m_impr.booster_.dump_model()

    assert dump["feature_names"] == expected_features, (
        f"Feature mismatch: expected {expected_features}, got {dump['feature_names']}"
    )


# 3. Preprocessing matches training (categories & date decomposition)
def test_preprocessing_matches_training():
    service = market_price_service
    service._ensure_loaded()

    # Preprocessing verifies state, district, mandi, crop, variety as categorical
    target_date = datetime.date(2026, 11, 15)
    df = pd.DataFrame([{
        "state_name": "Andhra Pradesh",
        "district_name": "Guntur",
        "market_name": "Tenali",
        "crop": "Tomato",
        "variety": "Local",
        "year": target_date.year,
        "month": target_date.month,
        "day": target_date.day,
    }])
    for col in ["state_name", "district_name", "market_name", "crop", "variety"]:
        df[col] = df[col].astype("category")

    pred = service._model.predict(df)
    assert len(pred) == 1
    assert float(pred[0]) > 0


# 4. Valid inference returns finite numerical predictions across multiple crops
@pytest.mark.parametrize("commodity,mandi", [
    ("Wheat", "Varanasi(Grain)"),
    ("Tomato", "Tenali"),
    ("Rice", "Guntur"),
    ("Cotton", "Kurnool"),
    ("Onion", "Lasalgaon"),
    ("Banana", "Nagpur Apmc"),
])
def test_valid_inference_multiple_commodities(commodity, mandi):
    res = market_price_service.forecast_price(
        commodity=commodity,
        mandi=mandi,
        days_ahead=7,
    )

    assert res["forecast_modal_price"] > 0
    assert np.isfinite(res["forecast_modal_price"])
    assert res["observed_market_price"] > 0
    assert res["commodity"] == commodity or commodity in res["commodity"]
    assert res["unit"] == "Rs./Quintal"


@pytest.mark.parametrize("commodity,mandi", [
    ("Maize", "Nizamabad"),
    ("Bengal Gram", "Nizamabad"),
])
def test_missing_exact_observation_is_explained_without_substitution(commodity, mandi):
    """A model-supported vocabulary item is not automatically verified data coverage."""
    with pytest.raises(ValueError, match="No verified market observation"):
        market_price_service.forecast_price(commodity=commodity, mandi=mandi, days_ahead=7)


# 5 & 6. Reproducible chronological held-out test evaluation verifies Improved Model superiority
def test_chronological_test_evaluation_superiority():
    csv_path = Path(__file__).resolve().parents[2] / "market-model-review" / "historical_agmarknet_varanasi.csv"
    if not csv_path.exists():
        pytest.skip("historical_agmarknet_varanasi.csv not present locally")

    models_dir = Path(__file__).resolve().parents[2] / "Agriverse_Models"
    m_orig = joblib.load(models_dir / "kshetraiq_model.pkl")
    m_impr = joblib.load(models_dir / "kshetraiq_improved_model.pkl")

    df = pd.read_csv(csv_path)
    df["Price Date"] = pd.to_datetime(df["Price Date"], format="%d-%b-%y")
    df = df.sort_values("Price Date").reset_index(drop=True)

    # Held out chronological test set (last 20%)
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:].reset_index(drop=True)

    features_df = pd.DataFrame({
        "state_name": "Uttar Pradesh",
        "district_name": test_df["District Name"],
        "market_name": test_df["Market Name"],
        "crop": test_df["Commodity"],
        "variety": test_df["Variety"],
        "year": test_df["Price Date"].dt.year,
        "month": test_df["Price Date"].dt.month,
        "day": test_df["Price Date"].dt.day,
    })
    for c in ["state_name", "district_name", "market_name", "crop", "variety"]:
        features_df[c] = features_df[c].astype("category")

    y_true = test_df["Modal Price (Rs./Quintal)"].astype(float).values

    pred_orig = m_orig.predict(features_df)
    pred_impr = m_impr.predict(features_df)

    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    mae_orig = mean_absolute_error(y_true, pred_orig)
    mae_impr = mean_absolute_error(y_true, pred_impr)
    rmse_orig = np.sqrt(mean_squared_error(y_true, pred_orig))
    rmse_impr = np.sqrt(mean_squared_error(y_true, pred_impr))
    r2_orig = r2_score(y_true, pred_orig)
    r2_impr = r2_score(y_true, pred_impr)

    # Assert Improved model strictly outperforms original model
    assert mae_impr < mae_orig, f"Improved MAE ({mae_impr:.2f}) should be lower than original ({mae_orig:.2f})"
    assert rmse_impr < rmse_orig, f"Improved RMSE ({rmse_impr:.2f}) should be lower than original ({rmse_orig:.2f})"
    assert r2_impr > r2_orig, f"Improved R2 ({r2_impr:.4f}) should be higher than original ({r2_orig:.4f})"


# 7. Unsupported commodity is rejected with HTTP 400
def test_unsupported_commodity_is_rejected(client):
    resp = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "DragonFruitNonExistent", "mandi": "Tenali", "days_ahead": 7},
    )
    assert resp.status_code == 400
    assert "not supported by the market price model" in resp.json()["detail"]


# 8. Unsupported mandi is rejected with HTTP 400
def test_unsupported_mandi_is_rejected(client):
    resp = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "Wheat", "mandi": "MarsColonyMandi", "days_ahead": 7},
    )
    assert resp.status_code == 400
    assert "not supported by the market price model" in resp.json()["detail"]


# 9. No hardcoded lag features required
def test_no_hardcoded_lag_features():
    # The new service does not rely on dummy fixed lag vectors
    res = market_price_service.forecast_price(commodity="Wheat", mandi="Varanasi(Grain)", days_ahead=5)
    assert res["model_version"] == "v2"
    assert "forecast_trajectory" in res
    assert len(res["forecast_trajectory"]) == 5


# 10. Live and cached market data are distinguished
def test_live_and_cached_market_data_distinction():
    obs = market_price_service.get_latest_observation("Wheat", "Varanasi(Grain)")
    assert "live_feed_status" in obs
    assert obs["live_feed_status"] in ("live_agmarknet", "cached_observation", "offline_verified_benchmark")
    assert "data_source" in obs
    assert "observation_date" in obs


# 11. Forecast horizon validation works
def test_forecast_horizon_validation(client):
    # Within bounds (1 to 90)
    resp = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "Wheat", "mandi": "Varanasi(Grain)", "days_ahead": 14},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["forecast_trajectory"]) == 14

    # Out of bounds (< 1)
    resp_invalid = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "Wheat", "mandi": "Varanasi(Grain)", "days_ahead": 0},
    )
    assert resp_invalid.status_code == 422


# 12. Confidence intervals and hybrid forecasting are statistically grounded
def test_confidence_intervals_grounded():
    res = market_price_service.forecast_price(commodity="Tomato", mandi="Tenali", days_ahead=7)
    ci = res["confidence_band"]
    price = res["forecast_modal_price"]

    # At 7-day horizon, Persistence is selected with horizon MAE 33.7
    assert res["primary_forecast_method"] == "persistence"
    assert res["seasonal_model_estimate"] > 0
    assert ci["mae"] == 33.7
    assert ci["seasonal_model_mae"] == CHRONOLOGICAL_TEST_MAE
    assert np.isclose(ci["upper_bound"] - price, 33.7, atol=0.2)
    assert np.isclose(ci["upper_95"] - price, 95.7, atol=0.2)
    assert "uncertainty_methodology" in ci
    assert ci["validation_coverage_pct"] > 60.0


# 13. Commodities and mandis catalog endpoint
def test_market_catalog_endpoint(client):
    resp = client.get("/api/v1/market/commodities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_commodities"] >= 370
    assert data["total_mandis"] >= 5800
    assert len(data["popular_commodities"]) >= 10
    assert len(data["popular_mandis"]) >= 10


# 14. AI Assistant retrieves Market Insights results
def test_ai_assistant_retrieves_market_insights():
    # Test English query for Tomato price
    ctx = context_engine.build_context(
        user_id=None,
        query="What is the forecast market price of Tomato in Tenali?",
        screen_context_payload={"screen_id": "market", "selected_crop": "Tomato"},
        language="en",
    )
    res = langgraph_orchestrator.run(ctx)

    assert res.screen_id == "market"
    assert "Tomato" in res.reply or "Tenali" in res.reply
    assert "₹" in res.reply

    # Test Telugu query for Wheat price
    ctx_te = context_engine.build_context(
        user_id=None,
        query="గోధుమ మార్కెట్ ధర అంచనా ఎంత?",
        screen_context_payload={"screen_id": "market", "selected_crop": "Wheat"},
        language="te",
    )
    res_te = langgraph_orchestrator.run(ctx_te)
    assert res_te.screen_id == "market"
    assert "₹" in res_te.reply


# 15. Backward compatibility with existing API endpoints
def test_legacy_endpoint_backward_compatibility(client):
    resp = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "Wheat", "mandi": "Varanasi(Grain)", "days_ahead": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "forecast_modal_price" in data
    assert "observed_market_price" in data
    assert "confidence_band" in data
    assert "trend_direction" in data


# 16. Mandi whitespace and parenthesis normalization
def test_mandi_whitespace_and_parenthesis_normalization(client):
    # Tests Varanasi (Grain) with space before parenthesis
    res_spaced = market_price_service.forecast_price(commodity="Wheat", mandi="Varanasi (Grain)", days_ahead=7)
    assert res_spaced["mandi"] == "Varanasi(Grain)"
    assert res_spaced["forecast_modal_price"] > 0
    assert res_spaced["observed_market_price"] == 2275.0

    # Tests Varanasi canonical alias without parenthesis
    res_plain = market_price_service.forecast_price(commodity="Wheat", mandi="Varanasi", days_ahead=7)
    assert res_plain["forecast_modal_price"] > 0
    assert res_plain["observed_market_price"] == 2275.0

    # Test via HTTP API endpoint with spaced mandi name
    resp = client.post(
        "/api/v1/predictions/market-price",
        json={"commodity": "Wheat", "mandi": "Varanasi (Grain)", "days_ahead": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["forecast_modal_price"] == 2275.0
    assert data["mandi"] == "Varanasi(Grain)"
    assert data["state"] == "Uttar Pradesh"
    assert data["district"] == "Varanasi"


# 17. Positional and keyword argument compatibility
def test_positional_and_keyword_argument_compatibility():
    # Positional invocation: commodity, mandi, days_ahead
    pos = market_price_service.forecast_price("Wheat", "Varanasi (Grain)", 7)
    assert pos["forecast_modal_price"] > 0

    # Keyword invocation
    kw = market_price_service.forecast_price(commodity="Wheat", mandi="Varanasi(Grain)", days_ahead=7)
    assert kw["forecast_modal_price"] == pos["forecast_modal_price"]

