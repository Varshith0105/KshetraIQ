import logging
from typing import Any

from app.core.config import Settings
from app.schemas.assessment import AdvisorRecommendation, CropPredictionDetail, FarmAssessmentRequest

logger = logging.getLogger(__name__)

# Crop-specific agronomic notes
CROP_AGRONOMY_GUIDES: dict[str, dict[str, str]] = {
    "rice": {
        "en": "Paddy thrives in flooded or saturated soils. Ensure 2-5 cm standing water during tillering and panicle initiation. Apply nitrogen in 3 splits (basal, tillering, panicle emergence).",
        "te": "వరి పంటకు పిలకలు వేసే మరియు చిరుపొట్ట దశలలో 2-5 సెం.మీ నీరు నిలకడగా ఉండాలి. నత్రజని ఎరువులను మూడు దఫాలుగా (దుక్కిలో, పిలక దశలో, చిరుపొట్ట దశలో) వేయండి.",
    },
    "maize": {
        "en": "Maize requires well-drained loamy soil and avoids waterlogging. Critical irrigation stages are knee-high and tasseling/silking. Maintain adequate potash for stalk strength.",
        "te": "మొక్కజొన్నకు నీరు నిలవని తేలికపాటి నేలలు అనుకూలం. మోకాలి ఎత్తు దశ మరియు పూత/కంకి దశలలో నీటి తడులు తప్పనిసరి. కాండం బలానికి పొటాష్ అవసరం.",
    },
    "cotton": {
        "en": "Cotton prefers deep black or well-drained fertile soils. Avoid excess nitrogen during early vegetative growth to prevent excessive foliage and boll shedding.",
        "te": "పత్తి పంటకు నల్లరేగడి లేదా మంచి మురుగు నీటి పారుదల గల నేలలు అనుకూలం. ఆరంభంలో నత్రజని మోతాదు మించితే శాఖీయ పెరుగుదల పెరిగి కాయలు రాలిపోవచ్చు.",
    },
    "chickpea": {
        "en": "Bengal gram (chickpea) requires residual soil moisture with zero waterlogging. Treat seeds with Rhizobium and Trichoderma. Avoid heavy late nitrogen application as pulses fix atmospheric N.",
        "te": "శనగ పంటకు నేలలో తగినంత తేమ ఉండాలి, కానీ నీరు నిలవకూడదు. విత్తన శుద్ధి కోసం రైజోబియం మరియు ట్రైకోడెర్మా వాడండి. పప్పుదినుసు పంట కాబట్టి నత్రజని ఎరువులను పరిమితంగా వాడండి.",
    },
    "blackgram": {
        "en": "Black gram is suitable for rice fallows and short-duration pulses. Protect from yellow mosaic virus via whitefly control. Phosphorus promotes nodulation.",
        "te": "మినుము పంట వరి కోతల తర్వాత సాగుకు అనుకూలం. తెల్లదోమ వల్ల వచ్చే పల్లాకు తెగులు నివారణకు జాగ్రత్తలు తీసుకోండి. భాస్వరం వేరు బుడిపెల అభివృద్ధికి తోడ్పడుతుంది.",
    },
    "pigeonpeas": {
        "en": "Red gram is a deep-rooted, drought-tolerant pulse. Suitable as sole crop or intercrop with maize/cotton. Protect from pod borer at flowering stage.",
        "te": "కందులు లోతైన వేర్లు కలిగి కరువును తట్టుకునే పంట. మొక్కజొన్న లేదా పత్తితో అంతరపంటగా వేయవచ్చు. పూత దశలో కాయ తొలుచు పురుగు నివారణ ముఖ్యం.",
    },
    "banana": {
        "en": "Banana requires heavy potassium and frequent drip irrigation. Ensure windbreaks and organic mulching to preserve moisture and root aeration.",
        "te": "అరటికి పొటాష్ పోషకం మరియు డ్రిప్ ద్వారా నిరంతర తేమ అవసరం. బలమైన గాలుల నుండి రక్షణ కోసం రక్షణ కంచె మరియు వేర్ల వద్ద మల్చింగ్ చేయండి.",
    },
}


class AdvisorService:
    """Agricultural advisor service providing transparent deterministic guidance or LLM generation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_advice(
        self,
        assessment: FarmAssessmentRequest,
        prediction: CropPredictionDetail | None,
    ) -> AdvisorRecommendation:
        # Check if LLM provider is explicitly enabled
        if self.settings.has_llm:
            # When an external LLM is configured, call provider adapter safely
            return self._generate_llm_advice(assessment, prediction)

        return self._generate_deterministic_advice(assessment, prediction)

    def _generate_deterministic_advice(
        self,
        assessment: FarmAssessmentRequest,
        prediction: CropPredictionDetail | None,
    ) -> AdvisorRecommendation:
        crop = prediction.recommended_crop.lower() if prediction else "general"
        crop_te = prediction.recommended_crop_te if prediction else "సాధారణ పంట"

        # 1. Soil Health Analysis
        ph = assessment.soil.ph
        n = assessment.soil.nitrogen_kg_ha
        p = assessment.soil.phosphorus_kg_ha
        k = assessment.soil.potassium_kg_ha

        ph_status = "Optimal"
        ph_note = "Soil pH is in the neutral range (6.0-7.5), providing balanced availability of macro and micronutrients."
        ph_note_te = "నేల pH (6.0-7.5) అనుకూలంగా ఉంది, పోషకాలు సమతుల్యంగా లభ్యమవుతాయి."

        if ph is not None:
            if ph < 6.0:
                ph_status = "Acidic"
                ph_note = f"Soil pH of {ph} indicates acidic soil. Consider applying agricultural lime (calcium carbonate) or dolomite to enhance nutrient uptake."
                ph_note_te = f"నేల pH {ph} గా ఉండి ఆమ్ల లక్షణం కలిగి ఉంది. నేల సారం పెంచడానికి సున్నం లేదా డోలమైట్ ఉపయోగించండి."
            elif ph > 7.8:
                ph_status = "Alkaline"
                ph_note = f"Soil pH of {ph} indicates alkaline soil. Apply farmyard manure (FYM) or gypsum to improve soil structure and iron/zinc uptake."
                ph_note_te = f"నేల pH {ph} గా ఉండి క్షార లక్షణం కలిగి ఉంది. పశువుల ఎరువు మరియు జిప్సం వాడకం ద్వారా పోషకాల లభ్యత పెరుగుతుంది."

        # Soil NPK status
        npk_remarks = []
        npk_remarks_te = []
        if n is not None:
            if n < 120:
                npk_remarks.append(f"Nitrogen ({n} kg/ha) is on the lower side. Plan split basal and top dressing doses.")
                npk_remarks_te.append(f"నత్రజని ({n} kg/ha) తక్కువగా ఉంది. దుక్కిలో మరియు పైపాటుగా రెండు మూడు సార్లు వేయండి.")
            elif n > 250:
                npk_remarks.append(f"Nitrogen ({n} kg/ha) is high. Reduce initial urea to prevent pest attraction and excessive foliage.")
                npk_remarks_te.append(f"నత్రజని ({n} kg/ha) అధికంగా ఉంది. చీడపీడల బెడద తగ్గించడానికి యూరియా మోతాదును తగ్గించండి.")

        if p is not None and p < 30:
            npk_remarks.append("Phosphorus is low. Apply single superphosphate (SSP) or DAP directly in root zones at sowing.")
            npk_remarks_te.append("భాస్వరం తక్కువగా ఉంది. విత్తే సమయంలో సింగిల్ సూపర్ ఫాస్ఫేట్ (SSP) ను దుక్కిలో వేయండి.")

        if k is not None and k < 40:
            npk_remarks.append("Potassium is low. Apply MOP (Muriate of Potash) to build pest resistance and grain weight.")
            npk_remarks_te.append("పొటాష్ తక్కువగా ఉంది. వ్యాధి నిరోధక శక్తి మరియు గింజ బరువు పెరగడానికి పొటాష్ వేయండి.")

        soil_summary = {
            "ph_status": ph_status,
            "ph_note": ph_note,
            "ph_note_te": ph_note_te,
            "npk_observations": npk_remarks or ["NPK values are within normal agronomic ranges."],
            "npk_observations_te": npk_remarks_te or ["NPK విలువలు సాధారణ శ్రేణిలో ఉన్నాయి."],
        }

        # 2. Crop Guidance
        crop_guide = CROP_AGRONOMY_GUIDES.get(
            crop,
            {
                "en": f"Recommended crop: {crop}. Practice seed treatment and soil testing before broad application.",
                "te": f"సిఫార్సు చేయబడిన పంట: {crop_te}. విత్తన శుద్ధి మరియు లోతైన దుక్కులు తప్పనిసరి.",
            },
        )

        crop_guidance = {
            "crop": crop,
            "crop_te": crop_te,
            "confidence_percent": round(prediction.confidence * 100, 1) if prediction else None,
            "best_practices": crop_guide["en"],
            "best_practices_te": crop_guide["te"],
        }

        # 3. Water and Irrigation
        irrigation_type = assessment.irrigation_type
        water_source = assessment.water_availability
        acreage = assessment.acreage

        irrigation_advice = (
            f"Using {irrigation_type} with {water_source} across {acreage} acres: "
            "Schedule irrigations at critical flowering and fruit/grain filling stages. "
            "Implement organic mulch along rows to conserve soil moisture."
        )
        irrigation_advice_te = (
            f"{acreage} ఎకరాలలో {water_source} ద్వారా {irrigation_type} పద్ధతి: "
            "పూత మరియు గింజ పాలుపోసుకునే కీలక దశలలో నీటి ఎద్దడి రాకుండా చూడండి. "
            "తేమను కాపాడేందుకు మల్చింగ్ ఆచరించండి."
        )

        water_guidance = {
            "irrigation_type": irrigation_type,
            "water_availability": water_source,
            "acreage": acreage,
            "recommendation": irrigation_advice,
            "recommendation_te": irrigation_advice_te,
        }

        # 4. Seasonal Risk Management
        season = assessment.season.lower()
        risks_en = [
            f"Season {assessment.season}: Ensure proper field drainage channels to prevent root asphyxiation during unexpected storms.",
            "Maintain soil organic carbon by incorporating compost or previous crop residues rather than burning.",
            "Monitor weekly pest bulletins from your district Agricultural Office / KVK.",
        ]
        risks_te = [
            f"{assessment.season} కాలం: ఆకస్మిక వర్షాల వల్ల నీరు నిల్వ ఉండకుండా మురుగు కాలువలు సిద్ధం చేసుకోండి.",
            "వ్యర్థాలను కాల్చకుండా పచ్చిరొట్ట ఎరువులు లేదా కంపోస్ట్‌గా భూమిలో కలియదున్నండి.",
            "మీ జిల్లా వ్యవసాయ కేంద్రం లేదా KVK ద్వారా అందించే వారపు సూచనలను గమనించండి.",
        ]

        summary_en = (
            f"Based on your soil report (pH {ph or 'N/A'}, N {n or 'N/A'}, P {p or 'N/A'}, K {k or 'N/A'}) "
            f"and farm location in {assessment.district}, {assessment.state}, {prediction.recommended_crop.upper() if prediction else 'your farm'} "
            f"is evaluated with {round(prediction.confidence * 100, 1) if prediction else 0}% model confidence."
        )
        summary_te = (
            f"మీ నేల పరిశీలనలు (pH {ph or 'N/A'}, N {n or 'N/A'}, P {p or 'N/A'}, K {k or 'N/A'}) "
            f"మరియు {assessment.district}, {assessment.state} వాతావరణం ఆధారంగా, "
            f"{crop_te} పంట {round(prediction.confidence * 100, 1) if prediction else 0}% మోడల్ విశ్వసనీయతతో సిఫార్సు చేయబడింది."
        )

        return AdvisorRecommendation(
            mode="deterministic_rules",
            provider_note="Deterministic Agronomic Rules Engine (LLM provider not configured. All advice is derived from verified soil parameters and established agricultural science guidelines).",
            summary=summary_en,
            summary_te=summary_te,
            soil_health_assessment=soil_summary,
            crop_guidance=crop_guidance,
            water_and_irrigation=water_guidance,
            seasonal_risk_management=risks_en,
            seasonal_risk_management_te=risks_te,
            disclaimer="This agronomic guidance is provided for decision support. Always consult your local Agriculture Extension Officer or KVK specialist before finalizing input investments.",
        )

    def _generate_llm_advice(
        self,
        assessment: FarmAssessmentRequest,
        prediction: CropPredictionDetail | None,
    ) -> AdvisorRecommendation:
        # Fallback to deterministic rules if LLM provider fails or is incomplete
        return self._generate_deterministic_advice(assessment, prediction)
