"""
Tests for PredictionHistoryService and ML prediction persistence.
"""

import pytest
from app.services.prediction_history_service import PredictionHistoryService


def test_prediction_history_lifecycle(tmp_path):
    from app.core.config import Settings
    s = Settings(sqlite_db_path=str(tmp_path / "test_pred.db"))
    svc = PredictionHistoryService(settings=s)

    # 1. Record prediction
    rec = svc.record_prediction(
        model_id="market-price-v2",
        input_features={"commodity": "Wheat", "mandi": "Varanasi(Grain)"},
        prediction_output={"forecast_modal_price": 2500, "trend": "BULLISH"},
        user_id="user_test_123",
        model_version="v2",
        units="INR/quintal",
        prediction_methodology="LightGBM + Linear Trend",
    )
    assert rec.prediction_id.startswith("pred_")
    assert rec.model_id == "market-price-v2"
    assert rec.user_id == "user_test_123"

    # 2. Get prediction
    fetched = svc.get_prediction(rec.prediction_id, user_id="user_test_123")
    assert fetched is not None
    assert fetched.input_features["commodity"] == "Wheat"
    assert fetched.prediction_output["forecast_modal_price"] == 2500

    # User isolation check
    fetched_wrong_user = svc.get_prediction(rec.prediction_id, user_id="user_wrong")
    assert fetched_wrong_user is None

    # 3. List predictions with user filter
    preds = svc.list_predictions(user_id="user_test_123")
    assert len(preds) == 1
    assert preds[0].prediction_id == rec.prediction_id

    preds_other = svc.list_predictions(user_id="user_other")
    assert len(preds_other) == 0

    # 4. Summary
    summary = svc.get_user_model_summary(user_id="user_test_123")
    assert "market-price-v2" in summary
    assert summary["market-price-v2"]["count"] == 1

