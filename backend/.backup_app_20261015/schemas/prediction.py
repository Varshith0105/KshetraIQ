"""Pydantic schemas for individual ML inference and diagnostic endpoints."""

from pydantic import BaseModel, Field


# ── Crop Yield Prediction ──
class CropYieldRequest(BaseModel):
    crop: str = Field(min_length=2, max_length=50, description="Crop name (e.g. Rice, Maize, Cotton)")
    season: str = Field(default="Kharif", description="Agricultural season (Kharif, Rabi, Summer, Whole Year)")
    state: str = Field(default="Andhra Pradesh", description="Indian State")
    crop_year: int = Field(default=2024, ge=1990, le=2050, description="Crop harvest calendar year")
    area_hectares: float = Field(gt=0, le=100000, description="Cultivated land area in hectares")
    annual_rainfall_mm: float = Field(ge=0, le=10000, description="Annual/seasonal cumulative rainfall in mm")
    fertilizer_kg: float = Field(ge=0, le=10000000, description="Total fertilizer applied in kg")
    pesticide_kg: float = Field(ge=0, le=500000, description="Total pesticide applied in kg")


class CropYieldResponse(BaseModel):
    model_id: str = "crop-yield-v1"
    status: str = "success"
    predicted_yield_tonnes_per_hectare: float
    predicted_total_production_tonnes: float
    algorithm: str = "Random Forest Regressor (R² = 0.9802)"
    features_used: dict[str, str | float | int]
    disclaimer: str = "Yield prediction is calibrated against historic agricultural state survey data."


# ── Climate Change Scenario Analysis ──
class ClimateScenarioRequest(BaseModel):
    crop: str = Field(default="Rice", min_length=2, max_length=50)
    crop_year: int = Field(default=2024, ge=1990, le=2050)
    season: str = Field(default="Kharif")
    state: str = Field(default="Andhra Pradesh")
    baseline_rainfall_mm: float = Field(gt=0, le=10000, description="Baseline expected rainfall in mm")


class ClimateScenarioResponse(BaseModel):
    model_id: str = "climate-scenario-v1"
    crop: str
    baseline_rainfall_mm: float
    baseline_yield_tonnes_per_ha: float
    moderate_shock_yield_tonnes_per_ha: float  # -10% rainfall
    moderate_change_percent: float
    severe_shock_yield_tonnes_per_ha: float  # -25% rainfall
    severe_change_percent: float
    vulnerability_tier: str
    recommendation: str
    algorithm: str = "Random Forest Scenario Engine"


# ── Sustainability & Carbon Footprint Score ──
class SustainabilityRequest(BaseModel):
    area_hectares: float = Field(gt=0, le=100000, description="Land area in hectares")
    fertilizer_kg: float = Field(ge=0, le=10000000, description="Total fertilizer in kg")
    pesticide_kg: float = Field(ge=0, le=500000, description="Total pesticide in kg")
    yield_tonnes_per_ha: float = Field(ge=0, le=500, description="Crop yield in tonnes/ha")


class SustainabilityResponse(BaseModel):
    model_id: str = "sustainability-v1"
    score: float = Field(ge=0, le=100, description="Overall Sustainability Score (0-100)")
    category: str  # High Sustainability | Moderate Sustainability | Low Sustainability
    fertilizer_score: float
    pesticide_score: float
    production_efficiency_score: float
    weights: dict[str, float]
    advisory_notes: list[str]


# ── Weather Risk Prediction ──
class WeatherRiskRequest(BaseModel):
    month: int = Field(ge=1, le=12, description="Month of year (1-12)")
    season: str = Field(default="Kharif")
    state: str = Field(default="Andhra Pradesh")
    avg_temp_c: float = Field(ge=-20, le=60)
    min_temp_c: float | None = None
    max_temp_c: float | None = None
    wind_speed_kmh: float = Field(default=12.0, ge=0, le=200)
    air_pressure_hpa: float = Field(default=1010.0, ge=800, le=1100)
    rainfall_mm: float = Field(default=0.0, ge=0, le=5000)


class WeatherRiskResponse(BaseModel):
    model_id: str = "weather-risk-v1"
    status: str = "success"
    predicted_risk_level: str  # Low | Moderate | High | Extreme
    confidence: float
    class_probabilities: dict[str, float]
    algorithm: str = "XGBoost Multi-Class Classifier"
    advisory: str


# ── Model Health Schema ──
class ModelHealthResponse(BaseModel):
    model_id: str
    display_name: str
    status: str  # verified | blocked | unavailable
    artifact_name: str
    artifact_found: bool
    runtime_ready: bool
    required_inputs: list[str]
    notes: str
    endpoint: str | None = None
