from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    english = "en"
    telugu = "te"


class SoilMeasurements(BaseModel):
    nitrogen_kg_ha: Annotated[float | None, Field(ge=0, le=1000)] = None
    phosphorus_kg_ha: Annotated[float | None, Field(ge=0, le=1000)] = None
    potassium_kg_ha: Annotated[float | None, Field(ge=0, le=1000)] = None
    ph: Annotated[float | None, Field(ge=0, le=14)] = None


class WeatherObservations(BaseModel):
    temperature_c: Annotated[float | None, Field(ge=-10, le=60)] = None
    humidity_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    rainfall_mm: Annotated[float | None, Field(ge=0, le=5000)] = None


class FarmAssessmentRequest(BaseModel):
    farm_name: Annotated[str, Field(min_length=2, max_length=100)]
    district: Annotated[str, Field(min_length=2, max_length=100)]
    state: Annotated[str, Field(min_length=2, max_length=100)]
    acreage: Annotated[float, Field(gt=0, le=100_000)]
    irrigation_type: Annotated[str, Field(min_length=2, max_length=80)]
    water_availability: Annotated[str, Field(min_length=2, max_length=80)]
    season: Annotated[str, Field(min_length=2, max_length=40)]
    soil: SoilMeasurements
    weather: WeatherObservations | None = None
    previous_crops: list[Annotated[str, Field(min_length=2, max_length=80)]] = Field(default_factory=list, max_length=10)
    planting_preferences: Annotated[str | None, Field(max_length=500)] = None
    language: Language = Language.english

    @field_validator("district", "state", "irrigation_type", "water_availability", "season")
    @classmethod
    def no_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class CropCandidate(BaseModel):
    crop: str
    crop_te: str
    confidence: float


class CropPredictionDetail(BaseModel):
    recommended_crop: str
    recommended_crop_te: str
    confidence: float
    top_candidates: list[CropCandidate] = Field(default_factory=list)
    features_used: dict[str, float] = Field(default_factory=dict)
    model_id: str = "crop-recommendation-v1"
    algorithm: str = "RandomForestClassifier (200 estimators)"
    artifact_name: str = "crop_recommendation_model.pkl"


class ModelResult(BaseModel):
    model_id: str
    status: str
    message: str
    missing_inputs: list[str] = Field(default_factory=list)
    prediction: CropPredictionDetail | None = None
    contract_note: str | None = None


class AdvisorRecommendation(BaseModel):
    mode: str
    provider_note: str
    summary: str
    summary_te: str
    soil_health_assessment: dict[str, Any]
    crop_guidance: dict[str, Any]
    water_and_irrigation: dict[str, Any]
    seasonal_risk_management: list[str]
    seasonal_risk_management_te: list[str]
    disclaimer: str


class ReportPreview(BaseModel):
    assessment_id: str
    farm_name: str
    location: str
    acreage: float
    season: str
    soil: dict[str, float | None]
    weather: dict[str, float | None]
    recommended_crop: str | None = None
    confidence: float | None = None
    model_id: str = "crop-recommendation-v1"
    confirmation_prompt: str
    confirmation_prompt_te: str
    disclaimer: str


class AssessmentResponse(BaseModel):
    assessment_id: str
    created_at: datetime
    input: FarmAssessmentRequest
    weather_source: str = "not_provided"
    results: list[ModelResult]
    advisor: AdvisorRecommendation | None = None
    assumptions: list[str]
    limitations: list[str]
    storage: str = "in_memory"
