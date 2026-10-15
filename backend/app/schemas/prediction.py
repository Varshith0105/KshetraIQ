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
    is_supported_crop: bool = True
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
    disclaimer: str = "Simulated agro-climatic stress projections based on historical crop sensitivity models, not guaranteed future yield outcomes."


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
    score_type: str = "Rule-based Agronomic Index (Empirical scoring, not a trained ML model)"
    fertilizer_score: float
    pesticide_score: float
    production_efficiency_score: float
    weights: dict[str, float]
    advisory_notes: list[str]
    disclaimer: str = "This score is an empirical rule-based index calculating input intensity vs. yield efficiency, not an ISO/GHG protocol certified carbon credit audit."


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
    status: str  # READY | DEGRADED | BLOCKED | UNAVAILABLE
    artifact_name: str
    artifact_found: bool
    runtime_ready: bool
    smoke_test_passed: bool = True
    required_inputs: list[str]
    notes: str
    limitations: str | None = None
    endpoint: str | None = None


# ── Market Price Forecasting ──
class MarketPriceRequest(BaseModel):
    commodity: str = Field(default="Wheat", description="Agricultural commodity name")
    mandi: str = Field(default="Varanasi(Grain)", description="APMC Market Mandi")
    target_date: str | None = Field(default=None, description="ISO target forecast date (YYYY-MM-DD)")
    days_ahead: int = Field(default=7, ge=1, le=90, description="Forecast horizon in days")


class MarketPriceResponse(BaseModel):
    model_id: str = "market-price-v1"
    algorithm: str
    commodity: str
    mandi: str
    forecast_date: str
    forecast_modal_price: float
    trend_component: float
    residual_adjustment: float
    unit: str
    observed_market_price: float
    observation_timestamp: str
    data_source: str
    live_feed_status: str | None = None
    adapter_note: str | None = None
    confidence_band: dict[str, float]
    limitations: str


# ── Plant Disease Screening ──
class PlantDiseaseCandidate(BaseModel):
    class_name: str
    label_te: str
    confidence: float
    mitigation: str


class PlantDiseaseResponse(BaseModel):
    model_id: str = "plant-disease-v1"
    model_architecture: str
    predicted_class: str
    label_te: str
    confidence_pct: float
    is_healthy: bool
    is_low_confidence: bool = False
    warning: str | None = None
    recommended_mitigation: str
    top_candidates: list[PlantDiseaseCandidate]
    supported_crops: list[str] = ["Apple", "Corn (Maize)", "Bell Pepper", "Potato", "Tomato"]
    filename: str
    disclaimer: str


# ── Irrigation Advisory ──
class IrrigationRequest(BaseModel):
    crop: str = Field(default="Rice", description="Cultivated crop name")
    crop_days: int = Field(default=45, ge=1, le=365, description="Crop age in days")
    soil_moisture: float = Field(default=320.0, ge=0.0, le=1000.0, description="Soil moisture level (0-1000)")
    soil_type: str = Field(default="Loam", description="Soil texture type (Loam, Clay, Sandy, Black)")
    temperature: float = Field(default=28.0, ge=-10.0, le=55.0, description="Ambient temperature in °C")
    rainfall_forecast_mm: float = Field(default=0.0, ge=0.0, le=500.0, description="Forecasted 3-day precipitation")
    area_acres: float = Field(default=2.5, gt=0.0, le=10000.0, description="Farm acreage")


class IrrigationResponse(BaseModel):
    model_id: str = "irrigation-deterministic-icar-v1"
    advisory_type: str
    crop: str
    crop_days: int
    growth_stage: str
    soil_moisture_level: float
    soil_type: str
    action: str
    action_te: str
    reason: str
    recommended_water_depth_mm: float
    liters_per_acre: int
    total_farm_liters: int
    area_acres: float
    schedule_interval_days: int
    recommended_method: str
    recommended_method_te: str
    rl_status_note: str

