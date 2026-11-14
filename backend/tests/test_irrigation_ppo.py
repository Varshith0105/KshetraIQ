"""Comprehensive verification and regression test suite for RL Irrigation PPO integration.

Covers:
1. Model loading & artifact format detection.
2. Observation contract, shapes, dtypes, feature ordering.
3. Genuine inference smoke test on real loaded artifact.
4. Output bounds, discrete action interpretation, confidence scores.
5. Crop support routing (Paddy/Rice and Groundnut via PPO; other crops via ICAR fallback).
6. Missing/invalid input handling and physical input sanitization.
7. Corrupt/missing artifact handling with transparent fallback.
8. Force deterministic override flag.
9. Regression verification of ICAR water budget calculations.
10. Model registry status and health diagnostic reporting.
"""

from __future__ import annotations

import io
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.models.registry import get_model_health, MODEL_REGISTRY
from app.schemas.prediction import IrrigationRequest, IrrigationResponse
from app.services.irrigation_service import (
    IrrigationService,
    IrrigationRLAgent,
    _extract_torch_weights_from_pickle,
    irrigation_service,
)


def test_artifact_format_and_loading() -> None:
    """Verify that the real artifact final_rl_irrigation_ppo_model.pkl is detected and loaded."""
    assert irrigation_service.is_rl_available, f"RL failed to load: {irrigation_service.rl_load_error}"
    artifact = irrigation_service.rl_artifact_path
    assert artifact is not None and artifact.is_file(), f"Artifact path invalid: {artifact}"
    assert artifact.name == "final_rl_irrigation_ppo_model.pkl"
    assert artifact.stat().st_size == 128011, f"Unexpected file size: {artifact.stat().st_size}"


def test_weights_extraction_and_shapes() -> None:
    """Verify that all policy network weight matrices match the SB3 MlpPolicy contract."""
    artifact = irrigation_service.rl_artifact_path
    assert artifact is not None
    weights = _extract_torch_weights_from_pickle(artifact)

    expected_layers = {
        "mlp_extractor.policy_net.0.weight": (64, 6),
        "mlp_extractor.policy_net.0.bias": (64,),
        "mlp_extractor.policy_net.2.weight": (64, 64),
        "mlp_extractor.policy_net.2.bias": (64,),
        "action_net.weight": (2, 64),
        "action_net.bias": (2,),
    }

    for name, expected_shape in expected_layers.items():
        assert name in weights, f"Missing layer {name}"
        assert weights[name].shape == expected_shape, f"Layer {name} shape mismatch: {weights[name].shape} vs {expected_shape}"
        assert weights[name].dtype == np.float32, f"Layer {name} dtype is not float32"


def test_genuine_rl_inference_dry_soil() -> None:
    """Smoke test: severely dry soil must trigger IRRIGATION_NEEDED with high confidence."""
    res = irrigation_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=140.0,
        soil_type="Loam",
        temperature=28.0,
        rainfall_forecast_mm=0.0,
        area_acres=2.5,
        soil_temperature=24.0,
        humidity=62.0,
    )

    assert res["model_id"] == "irrigation-rl-ppo-v1"
    assert res["method_used"] == "ppo_reinforcement_learning"
    assert res["action"] == "IRRIGATION_NEEDED"
    assert res["policy_action"] == 1
    assert res["policy_confidence"] > 0.90
    assert res["recommended_water_depth_mm"] > 0
    assert res["total_farm_liters"] > 0
    assert res["normalized_observation"] is not None
    assert len(res["normalized_observation"]) == 6


def test_genuine_rl_inference_wet_soil() -> None:
    """Smoke test: high moisture soil must trigger NO_IRRIGATION."""
    res = irrigation_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=720.0,
        soil_type="Loam",
        temperature=28.0,
        rainfall_forecast_mm=0.0,
        area_acres=2.5,
        soil_temperature=18.0,
        humidity=63.0,
    )

    assert res["model_id"] == "irrigation-rl-ppo-v1"
    assert res["method_used"] == "ppo_reinforcement_learning"
    assert res["action"] == "NO_IRRIGATION"
    assert res["policy_action"] == 0
    assert res["recommended_water_depth_mm"] == 0.0
    assert res["total_farm_liters"] == 0


def test_groundnut_crop_supported_by_ppo() -> None:
    """Groundnut (CropType=2 in training notebook) should run via PPO policy."""
    res = irrigation_service.calculate_irrigation(
        crop="Groundnut",
        crop_days=50,
        soil_moisture=220.0,
        soil_type="Sandy",
        temperature=32.0,
        rainfall_forecast_mm=0.0,
        area_acres=3.0,
    )

    assert res["model_id"] == "irrigation-rl-ppo-v1"
    assert res["method_used"] == "ppo_reinforcement_learning"
    assert res["policy_action"] in (0, 1)
    assert res["normalized_observation"][0] == 1.0  # CropType 2.0 / 2.0 = 1.0


def test_unsupported_crop_graceful_fallback() -> None:
    """Crops not in PPO training set (e.g. Cotton, Maize) must gracefully fall back to ICAR."""
    res = irrigation_service.calculate_irrigation(
        crop="Cotton",
        crop_days=60,
        soil_moisture=220.0,
        soil_type="Black",
        temperature=34.0,
        rainfall_forecast_mm=0.0,
        area_acres=4.0,
    )

    assert res["model_id"] == "irrigation-deterministic-icar-v1"
    assert res["method_used"] == "icar_angrau_deterministic"
    assert res["action"] == "IRRIGATION_NEEDED"
    assert "not in PPO training set" in res["rl_status_note"]
    assert res["policy_action"] is None


def test_force_deterministic_override() -> None:
    """When force_deterministic=True, PPO must be bypassed even for supported crops."""
    res = irrigation_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=210.0,
        soil_type="Loam",
        temperature=30.0,
        rainfall_forecast_mm=0.0,
        area_acres=2.5,
        force_deterministic=True,
    )

    assert res["model_id"] == "irrigation-deterministic-icar-v1"
    assert res["method_used"] == "icar_angrau_deterministic"
    assert res["policy_action"] is None


def test_fallback_when_artifact_missing(tmp_path: Path) -> None:
    """Service initialized with non-existent artifact path must cleanly fall back to ICAR."""
    ghost_service = IrrigationService(custom_model_path=tmp_path / "non_existent.pkl")
    assert not ghost_service.is_rl_available

    res = ghost_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=210.0,
        soil_type="Loam",
        temperature=30.0,
        area_acres=2.5,
    )

    assert res["model_id"] == "irrigation-deterministic-icar-v1"
    assert res["method_used"] == "icar_angrau_deterministic"
    assert res["model_status"] == "DEGRADED"


def test_corrupt_artifact_handling(tmp_path: Path) -> None:
    """Service initialized with corrupt pickle must report error and fall back."""
    bad_pkl = tmp_path / "corrupt_model.pkl"
    bad_pkl.write_bytes(b"NOT_A_VALID_PICKLE_STREAM")

    corrupt_service = IrrigationService(custom_model_path=bad_pkl)
    assert not corrupt_service.is_rl_available
    assert corrupt_service.rl_load_error is not None

    res = corrupt_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=210.0,
        soil_type="Loam",
        temperature=30.0,
        area_acres=2.5,
    )

    assert res["model_id"] == "irrigation-deterministic-icar-v1"
    assert res["method_used"] == "icar_angrau_deterministic"


def test_input_sanitization_and_bounds() -> None:
    """Extreme inputs must be clamped to physically sound bounds without crashing."""
    res = irrigation_service.calculate_irrigation(
        crop="Rice",
        crop_days=-50,          # Out of bounds -> clamped to 1
        soil_moisture=2500.0,   # Out of bounds -> clamped to 1000
        temperature=-50.0,      # Out of bounds -> clamped to -10
        rainfall_forecast_mm=-10.0, # Negative -> clamped to 0
        area_acres=-5.0,        # Out of bounds -> clamped to 0.05
    )

    assert res["crop_days"] == 1
    assert res["soil_moisture_level"] == 1000.0
    assert res["area_acres"] == 0.05
    assert res["recommended_water_depth_mm"] >= 0.0


def test_pydantic_schema_validation() -> None:
    """Verify that IrrigationResponse schema fully validates the returned dictionary."""
    res = irrigation_service.calculate_irrigation(
        crop="Rice",
        crop_days=45,
        soil_moisture=210.0,
        soil_type="Loam",
        temperature=30.0,
        rainfall_forecast_mm=0.0,
        area_acres=2.5,
    )

    validated = IrrigationResponse.model_validate(res)
    assert validated.model_id == "irrigation-rl-ppo-v1"
    assert validated.method_used == "ppo_reinforcement_learning"
    assert validated.policy_action == 1
    assert validated.action == "IRRIGATION_NEEDED"
    assert validated.total_farm_liters > 0


def test_model_registry_health_reporting() -> None:
    """Verify that model registry reports irrigation-rl-v1 as READY with valid smoke test."""
    models_dir = Path("Agriverse_Models")
    health = get_model_health("irrigation-rl-v1", models_dir)
    assert health is not None
    assert health.model_id == "irrigation-rl-v1"
    assert health.status == "READY"
    assert health.artifact_found is True
    assert health.runtime_ready is True
    assert health.smoke_test_passed is True
    assert "PPO RL policy validated" in health.limitations


def test_regression_deterministic_icar_calculation() -> None:
    """Verify that the ICAR deterministic water budget formulas produce exact results."""
    res = irrigation_service._compute_icar_water_budget(
        crop="Rice",
        crop_days=45,
        soil_moisture=210.0,
        soil_type="Loam",
        temperature=30.0,
        rainfall_forecast_mm=0.0,
        area_acres=2.5,
    )

    # 45 days is Vegetative stage (stage_factor = 1.0)
    # ET0 = max(2.5, 0.15 * 30.0) = 4.5 mm/day
    # daily_water_req_mm = 4.5 * 1.0 = 4.5 mm/day
    # Net daily need = 4.5 mm
    # soil_moisture (210) < 250 -> interval_days = 4 (Loam)
    # water_depth_mm = round(4.5 * 4, 1) = 18.0 mm
    # Exact net liters per acre = round(18.0 * 4046.8564224) = 72843
    # Exact net total farm liters (2.5 ac) = round(18.0 * 4046.8564224 * 2.5) = 182109
    assert res["growth_stage"] == "Vegetative"
    assert res["action"] == "IRRIGATION_NEEDED"
    assert res["recommended_water_depth_mm"] == 18.0
    assert res["liters_per_acre"] == 72843
    assert res["total_farm_liters"] == 182109
    assert res["gross_farm_liters"] == round(182109 / 0.70)  # 70% efficiency for controlled shallow ponding
    assert res["application_efficiency_pct"] == 70.0
    assert "Controlled Shallow Ponding" in res["recommended_method"]


def test_exact_water_volume_arithmetic_1_acre_2_5_acres_5_acres() -> None:
    """Audit water volume conversions for 18.0 mm depth across 1.0, 2.5, and 5.0 acres."""
    # Constant: 1 acre = 4,046.8564224 m², 1 mm depth = 4,046.8564224 liters/acre
    depth_mm = 18.0
    constant = 4046.8564224

    # 1.0 acre: 18.0 * 4046.8564224 * 1.0 = 72843.4156 -> 72,843 L
    res_1ac = irrigation_service.calculate_irrigation(
        crop="Rice", crop_days=45, soil_moisture=210.0, soil_type="Loam",
        temperature=30.0, area_acres=1.0,
    )
    assert res_1ac["recommended_water_depth_mm"] == depth_mm
    assert res_1ac["liters_per_acre"] == round(depth_mm * constant) == 72843
    assert res_1ac["total_farm_liters"] == round(depth_mm * constant * 1.0) == 72843

    # 2.5 acres: 18.0 * 4046.8564224 * 2.5 = 182108.539 -> 182,109 L
    res_2_5ac = irrigation_service.calculate_irrigation(
        crop="Rice", crop_days=45, soil_moisture=210.0, soil_type="Loam",
        temperature=30.0, area_acres=2.5,
    )
    assert res_2_5ac["recommended_water_depth_mm"] == depth_mm
    assert res_2_5ac["liters_per_acre"] == 72843
    assert res_2_5ac["total_farm_liters"] == round(depth_mm * constant * 2.5) == 182109

    # 5.0 acres: 18.0 * 4046.8564224 * 5.0 = 364217.078 -> 364,217 L
    res_5ac = irrigation_service.calculate_irrigation(
        crop="Rice", crop_days=45, soil_moisture=210.0, soil_type="Loam",
        temperature=30.0, area_acres=5.0,
    )
    assert res_5ac["recommended_water_depth_mm"] == depth_mm
    assert res_5ac["liters_per_acre"] == 72843
    assert res_5ac["total_farm_liters"] == round(depth_mm * constant * 5.0) == 364217


def test_investigate_previous_182115_liters_discrepancy() -> None:
    """Explain and verify why the previous report stated 182,115 liters instead of 364,217 liters."""
    # The previous report evaluated area_acres = 2.5 with a rounded constant (4047.0) and intermediate rounding:
    depth_mm = 18.0
    coarse_liters_per_acre = round(depth_mm * 4047.0)  # 72846
    coarse_total_for_2_5_acres = round(coarse_liters_per_acre * 2.5)  # 182115
    assert coarse_total_for_2_5_acres == 182115, "Confirmed: 182,115 was calculated for 2.5 acres with coarse 4047.0 rounding"

    # For 5.0 acres with mathematically exact constant:
    exact_total_for_5_acres = round(depth_mm * 4046.8564224 * 5.0)
    assert exact_total_for_5_acres == 364217, "True 5-acre volume is 364,217 liters"


def test_pytorch_cpu_forward_pass_parity() -> None:
    """Verify bitwise/numerical parity between pure-NumPy IrrigationRLAgent and PyTorch CPU module."""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        pytest.skip("PyTorch not installed in this environment; pure NumPy deserializer verified separately.")

    artifact = irrigation_service.rl_artifact_path
    assert artifact is not None
    weights = _extract_torch_weights_from_pickle(artifact)

    class PyTorchPPOPolicy(nn.Module):
        def __init__(self, w: dict[str, np.ndarray]) -> None:
            super().__init__()
            self.fc1 = nn.Linear(6, 64)
            self.fc2 = nn.Linear(64, 64)
            self.action_net = nn.Linear(64, 2)
            self.tanh = nn.Tanh()

            self.fc1.weight.data = torch.from_numpy(w["mlp_extractor.policy_net.0.weight"])
            self.fc1.bias.data = torch.from_numpy(w["mlp_extractor.policy_net.0.bias"])
            self.fc2.weight.data = torch.from_numpy(w["mlp_extractor.policy_net.2.weight"])
            self.fc2.bias.data = torch.from_numpy(w["mlp_extractor.policy_net.2.bias"])
            self.action_net.weight.data = torch.from_numpy(w["action_net.weight"])
            self.action_net.bias.data = torch.from_numpy(w["action_net.bias"])

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.tanh(self.fc1(x))
            x = self.tanh(self.fc2(x))
            return self.action_net(x)

    torch_model = PyTorchPPOPolicy(weights).eval()
    numpy_agent = IrrigationRLAgent(weights, artifact)

    rng = np.random.default_rng(seed=42)
    for _ in range(50):
        obs = rng.uniform(0.0, 1.0, size=(6,)).astype(np.float32)

        # PyTorch CPU inference
        with torch.no_grad():
            t_logits = torch_model(torch.from_numpy(obs)).numpy()
            t_probs = torch.softmax(torch.from_numpy(t_logits), dim=-1).numpy()
            t_action = int(np.argmax(t_logits))

        # Pure NumPy inference
        n_action, n_probs, n_logits = numpy_agent.predict(obs)

        assert n_action == t_action, f"Action mismatch on obs {obs}: np={n_action}, pt={t_action}"
        np.testing.assert_allclose(n_logits, t_logits, rtol=1e-5, atol=1e-5)
        np.testing.assert_allclose(n_probs, t_probs, rtol=1e-5, atol=1e-5)


