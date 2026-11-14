import datetime
import sys
from pathlib import Path

backend_path = Path("E:/KshetraIQ/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pypdf
from app.schemas.assessment import (
    AdvisorRecommendation,
    AssessmentResponse,
    CropCandidate,
    CropPredictionDetail,
    FarmAssessmentRequest,
    ModelResult,
    SoilMeasurements,
    WeatherObservations,
)
from app.services.report_service import ReportService

svc = ReportService()
req = FarmAssessmentRequest(
    farm_name="Sri Venkateswara Rythu Kshetram",
    district="Guntur",
    state="Andhra Pradesh",
    acreage=2.5,
    irrigation_type="Drip",
    water_availability="Borewell",
    season="Kharif",
    soil=SoilMeasurements(nitrogen_kg_ha=140.0, phosphorus_kg_ha=35.0, potassium_kg_ha=220.0, ph=6.8),
    weather=WeatherObservations(temperature_c=29.5, humidity_percent=72.0, rainfall_mm=650.0),
    previous_crops=["cotton", "chilli"],
    language="en",
)
res = AssessmentResponse(
    assessment_id="TEST-ASSESS-8877",
    created_at=datetime.datetime.now(),
    weather_source="open_meteo_live",
    input=req,
    assumptions=["Assumes certified seed and standard agronomic crop calendar."],
    limitations=["Actual yields depend on micro-climate and pest management."],
    results=[
        ModelResult(
            model_id="crop-recommendation-v1",
            status="predicted",
            prediction=CropPredictionDetail(
                recommended_crop="cotton",
                recommended_crop_te="పత్తి",
                confidence=0.88,
                model_id="crop-recommendation-v1",
                algorithm="RandomForestClassifier",
                top_candidates=[
                    CropCandidate(crop="cotton", crop_te="పత్తి", confidence=0.88),
                    CropCandidate(crop="rice", crop_te="వరి", confidence=0.08),
                ],
            ),
            message="Optimal agro-climatic match.",
        )
    ],
    advisor=AdvisorRecommendation(
        mode="deterministic_rules",
        provider_note="ICAR/ANGRAU Agronomic Synthesis",
        summary="Farm soil shows ideal neutral pH and high potassium reserves.",
        summary_te="పొలం నేల తటస్థ pH మరియు అధిక పొటాష్ నిల్వలను కలిగి ఉంది.",
        soil_health_assessment={"ph_note": "Soil pH 6.8 is neutral; optimal for nutrient assimilation."},
        crop_guidance={"best_practices": "Follow 90x60 cm plant geometry for Bt cotton hybrids."},
        water_and_irrigation={"recommendation": "Irrigate via drip every 7-10 days depending on pan evaporation."},
        seasonal_risk_management=["Scout for pink bollworm at 45-60 DAS using pheromone traps."],
        seasonal_risk_management_te=["45-60 రోజులలో గులాబీ రంగు పురుగు కోసం ఫెరమోన్ బుట్టలను ఏర్పాటు చేయండి."],
        disclaimer="ICAR extension advisory protocol.",
    ),
)

pdf_bytes = svc.generate_pdf(res)
out_path = Path("E:/KshetraIQ/backend/.tmp/verified_farmer_dossier.pdf")
out_path.write_bytes(pdf_bytes)

reader = pypdf.PdfReader(str(out_path))
text = "\n".join([page.extract_text() for page in reader.pages])

print("=" * 60)
print(f"PDF Generated: {len(pdf_bytes)} bytes across {len(reader.pages)} page(s).")
print(f"Contains BLOCKED: {'BLOCKED' in text}")
print(f"Contains ARTIFACT: {'ARTIFACT' in text}")
print(f"Contains Cotton: {'Cotton' in text or 'cotton' in text}")
print(f"Contains Harvest Yield: {'tonnes' in text.lower()}")
print(f"Contains Drought Stress: {'drought' in text.lower()}")
print(f"Contains Precision Water: {'water' in text.lower() or 'litres' in text.lower()}")
print(f"Contains Advisory Plan: {'Advisory' in text or 'Guidance' in text}")
print("=" * 60)
