"""
KshetraIQ Farm Assistant — Deterministic, Context-Aware Agricultural Chatbot Service.

This chatbot uses real application data (assessments, model results, weather, advisor)
and never fabricates predictions, chemical rates, or disease diagnoses.
"""

import logging
from typing import Any

from app.core.config import Settings
from app.schemas.assessment import AssessmentResponse
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

# Topic keyword → handler mapping patterns
TOPIC_KEYWORDS_EN = {
    "soil": ["soil", "ph", "nitrogen", "phosphorus", "potassium", "npk", "n-p-k", "nutrient", "fertility"],
    "crop": ["crop", "recommendation", "recommend", "rice", "maize", "cotton", "wheat", "paddy", "which crop", "best crop", "what to grow", "what should i grow"],
    "weather": ["weather", "temperature", "rainfall", "humidity", "rain", "monsoon", "climate", "open-meteo"],
    "model": ["model", "registry", "random forest", "machine learning", "ai", "ml", "algorithm", "predict"],
    "report": ["report", "pdf", "download", "export", "dossier", "document"],
    "irrigation": ["irrigation", "water", "drip", "sprinkler", "canal", "borewell", "rainfed"],
    "assessment": ["assessment", "assess", "evaluate", "farm assessment", "submit", "analysis"],
    "disease": ["disease", "pest", "insect", "blight", "wilt", "fungus", "virus"],
    "market": ["market", "price", "mandi", "msp", "apmc", "sell"],
    "help": ["help", "how", "what", "guide", "start", "explain", "use", "feature"],
}

TOPIC_KEYWORDS_TE = {
    "soil": ["నేల", "ph", "నత్రజని", "భాస్వరం", "పొటాష్", "సారం", "పోషకాలు"],
    "crop": ["పంట", "సిఫార్సు", "వరి", "మొక్కజొన్న", "పత్తి", "ఏ పంట", "ఏమి వేయాలి"],
    "weather": ["వాతావరణం", "ఉష్ణోగ్రత", "వర్షపాతం", "తేమ", "వర్షం"],
    "model": ["మోడల్", "రిజిస్ట్రీ", "యంత్ర అభ్యాసం", "ai"],
    "report": ["నివేదిక", "pdf", "డౌన్‌లోడ్"],
    "irrigation": ["నీటి పారుదల", "నీరు", "డ్రిప్", "బోరు"],
    "assessment": ["అంచనా", "విశ్లేషణ", "సమీక్ష"],
    "disease": ["తెగులు", "పురుగు", "వ్యాధి"],
    "market": ["మార్కెట్", "ధర", "మండీ"],
    "help": ["సహాయం", "ఎలా", "ఏమి", "వివరించండి"],
}


def _detect_topic(message: str, language: str) -> str:
    """Detect the topic from the user message."""
    msg_lower = message.lower()
    keywords = TOPIC_KEYWORDS_TE if language == "te" else TOPIC_KEYWORDS_EN
    scores: dict[str, int] = {}
    for topic, words in keywords.items():
        score = sum(1 for w in words if w in msg_lower)
        if score > 0:
            scores[topic] = score
    if scores:
        return max(scores, key=scores.get)  # type: ignore[arg-type]
    return "general"


class ChatService:
    """Context-aware agricultural chatbot that uses real assessment data."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def respond(
        self,
        request: ChatRequest,
        assessment: AssessmentResponse | None,
    ) -> ChatResponse:
        """Generate a context-aware, deterministic response."""
        lang = request.language
        topic = _detect_topic(request.message, lang)

        # Route to topic handler
        handlers: dict[str, Any] = {
            "soil": self._handle_soil,
            "crop": self._handle_crop,
            "weather": self._handle_weather,
            "model": self._handle_model,
            "report": self._handle_report,
            "irrigation": self._handle_irrigation,
            "assessment": self._handle_assessment,
            "disease": self._handle_disease,
            "market": self._handle_market,
            "help": self._handle_help,
        }

        reply: str
        mode = "rule_based"
        provider = "rule_based_icar"

        # Check if a genuine LLM provider is configured
        if self.settings.has_llm:
            llm_result = self._try_llm_response(request, assessment)
            if llm_result:
                reply = llm_result
                mode = "llm"
                provider = self.settings.effective_llm_provider or "llm_custom"
            else:
                # LLM call failed or timed out; fall back to verified agronomic rule engine
                handler = handlers.get(topic, self._handle_general)
                reply = handler(request.message, lang, assessment)
                provider = "rule_based_fallback"
        else:
            handler = handlers.get(topic, self._handle_general)
            reply = handler(request.message, lang, assessment)

        disclaimer = (
            "ఈ సమాచారం సలహా మాత్రమే. ముఖ్యమైన నిర్ణయాలకు మీ స్థానిక వ్యవసాయ అధికారిని లేదా రైతు భరోసా కేంద్రాన్ని (RBK) సంప్రదించండి."
            if lang == "te"
            else "This information is for decision support only. Always verify consequential field actions with local Agricultural Extension Officers (RBK / KVK)."
        )

        source_ctx = None
        if assessment:
            source_ctx = f"Farm: {assessment.input.farm_name} ({assessment.input.district}, {assessment.input.state})"

        return ChatResponse(
            reply=reply,
            answer=reply,
            conversation_id=request.conversation_id,
            mode=mode,
            provider=provider,
            source_context=source_ctx,
            assessment_context_used=assessment is not None,
            disclaimer=disclaimer,
        )

    def _try_llm_response(self, request: ChatRequest, assessment: AssessmentResponse | None) -> str | None:
        """Attempt to call the configured LLM API with strict timeout and farm grounding."""
        provider = self.settings.effective_llm_provider
        api_key = self.settings.effective_llm_api_key
        if not api_key:
            return None

        # Build context-grounded prompt
        context_parts = []
        if assessment:
            inp = assessment.input
            context_parts.append(f"Farm: {inp.farm_name}, {inp.district}, {inp.state}")
            context_parts.append(f"Land Area: {inp.acreage} Acres, Season: {inp.season}, Irrigation: {inp.irrigation_type}")
            context_parts.append(f"Soil NPK: N={inp.soil.nitrogen_kg_ha}, P={inp.soil.phosphorus_kg_ha}, K={inp.soil.potassium_kg_ha}, pH={inp.soil.ph}")
            if inp.weather:
                context_parts.append(f"Weather: {inp.weather.temperature_c}°C, Humidity: {inp.weather.humidity_percent}%, Rain: {inp.weather.rainfall_mm}mm")
            # Verified crop recommendation
            rec = next((r for r in assessment.results if r.model_id == "crop-recommendation-v1"), None)
            if rec and rec.prediction:
                context_parts.append(f"Model-Recommended Crop: {rec.prediction.recommended_crop} ({round(rec.prediction.confidence * 100)}% confidence)")

        context_str = "\n".join(context_parts) if context_parts else "No specific farm assessment on file."
        lang_str = "Telugu (తెలుగు)" if request.language == "te" else "English"

        system_instruction = (
            "You are KshetraIQ Rythu AI, a certified Indian agricultural decision-support assistant specializing in Andhra Pradesh and Telangana farming.\n"
            f"Farmer Language Preference: {lang_str}. Answer fluently in {lang_str}.\n"
            "Ground your answer strictly in ICAR, ANGRAU, and Indian Agronomic standards.\n"
            f"Active Farm Context:\n{context_str}\n"
            "Rules:\n"
            "1. Be practical, respectful, and farmer-friendly.\n"
            "2. Never hallucinate fake chemical dosages or uncalibrated yield figures.\n"
            "3. If referencing soil nutrients, refer to the farmer's NPK and pH readings provided above.\n"
            "4. Remind the farmer to confirm pesticide or seed purchases with their local RBK (Rythu Bharosa Kendram)."
        )

        try:
            import json
            import urllib.request
            import urllib.error

            if provider == "gemini":
                # Google Gemini REST API (gemini-1.5-flash)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": f"{system_instruction}\n\nFarmer's Question: {request.message}"}
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 800}
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()

            elif provider in {"groq", "openai", "custom"}:
                # OpenAI-compatible chat completion
                if provider == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    model = "llama-3.1-8b-instant"
                else:
                    url = "https://api.openai.com/v1/chat/completions"
                    model = "gpt-4o-mini"

                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": request.message}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    choices = res_json.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()

        except Exception as e:
            logger.warning("LLM API call failed: %s. Falling back to deterministic rule engine.", e)
            return None

        return None

    # ──────────────────────── Topic Handlers ────────────────────────

    def _handle_soil(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment and assessment.advisor:
            soil = assessment.advisor.soil_health_assessment
            ph_status = soil.get("ph_status", "Unknown")
            ph_note = soil.get("ph_note_te" if lang == "te" else "ph_note", "")
            npk_obs = soil.get("npk_observations_te" if lang == "te" else "npk_observations", [])
            npk_text = "\n".join(f"• {o}" for o in npk_obs)
            if lang == "te":
                return (
                    f"మీ తాజా అంచనా ఆధారంగా నేల విశ్లేషణ:\n\n"
                    f"**pH స్థితి:** {ph_status}\n{ph_note}\n\n"
                    f"**NPK పరిశీలనలు:**\n{npk_text}\n\n"
                    f"ఈ విలువలు మీ అంచనాలో సమర్పించిన సాయిల్ హెల్త్ కార్డ్ నుండి తీసుకోబడ్డాయి."
                )
            return (
                f"Based on your latest assessment, here is the soil analysis:\n\n"
                f"**pH Status:** {ph_status}\n{ph_note}\n\n"
                f"**NPK Observations:**\n{npk_text}\n\n"
                f"These values were taken from the soil measurements you submitted in your assessment."
            )
        if lang == "te":
            return (
                "నేల విశ్లేషణ చూడాలంటే మొదట పొలం అంచనా పూర్తి చేయండి.\n\n"
                "సాయిల్ హెల్త్ కార్డ్ లేదా ల్యాబ్ నివేదిక నుండి N, P, K మరియు pH విలువలు నమోదు చేయండి.\n"
                "**'పొలం అంచనా'** పేజీకి వెళ్లి నేల విలువలు నమోదు చేయండి."
            )
        return (
            "To view soil analysis, please complete a farm assessment first.\n\n"
            "Enter your N, P, K and pH values from a certified Soil Health Card or lab report.\n"
            "Navigate to **'Farm Assessment'** and complete Step 2 (Soil Chemistry)."
        )

    def _handle_crop(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment:
            crop_result = next(
                (r for r in assessment.results if r.model_id == "crop-recommendation-v1"),
                None,
            )
            if crop_result and crop_result.prediction:
                pred = crop_result.prediction
                conf = round(pred.confidence * 100, 1)
                features = pred.features_used
                crop_name = pred.recommended_crop_te if lang == "te" else pred.recommended_crop
                alts = ", ".join(
                    (c.crop_te if lang == "te" else c.crop) + f" ({round(c.confidence * 100)}%)"
                    for c in pred.top_candidates[1:4]
                )
                if lang == "te":
                    return (
                        f"మీ పొలం అంచనా ఆధారంగా, **{crop_name}** పంట {conf}% మోడల్ నమ్మకంతో సిఫార్సు చేయబడింది.\n\n"
                        f"**ఉపయోగించిన ఇన్‌పుట్‌లు:**\n"
                        f"• N: {features.get('N', 'N/A')} kg/ha\n"
                        f"• P: {features.get('P', 'N/A')} kg/ha\n"
                        f"• K: {features.get('K', 'N/A')} kg/ha\n"
                        f"• pH: {features.get('ph', 'N/A')}\n"
                        f"• ఉష్ణోగ్రత: {features.get('temperature', 'N/A')}°C\n"
                        f"• తేమ: {features.get('humidity', 'N/A')}%\n"
                        f"• వర్షపాతం: {features.get('rainfall', 'N/A')} mm\n\n"
                        f"**ప్రత్యామ్నాయ పంటలు:** {alts or 'లేవు'}\n\n"
                        f"ఈ సిఫార్సు RandomForestClassifier (200 ఎస్టిమేటర్లు) ద్వారా మీరు అందించిన నేల మరియు వాతావరణ డేటా ఆధారంగా రూపొందించబడింది."
                    )
                return (
                    f"Based on your farm assessment, **{crop_name}** is recommended with {conf}% model confidence.\n\n"
                    f"**Input features used:**\n"
                    f"• N: {features.get('N', 'N/A')} kg/ha\n"
                    f"• P: {features.get('P', 'N/A')} kg/ha\n"
                    f"• K: {features.get('K', 'N/A')} kg/ha\n"
                    f"• pH: {features.get('ph', 'N/A')}\n"
                    f"• Temperature: {features.get('temperature', 'N/A')}°C\n"
                    f"• Humidity: {features.get('humidity', 'N/A')}%\n"
                    f"• Rainfall: {features.get('rainfall', 'N/A')} mm\n\n"
                    f"**Alternative crops:** {alts or 'None'}\n\n"
                    f"This recommendation was generated by the RandomForestClassifier (200 estimators) using the soil and weather data you provided."
                )
            elif crop_result and crop_result.status == "needs_input":
                missing = ", ".join(crop_result.missing_inputs)
                if lang == "te":
                    return f"పంట సిఫార్సు ఇవ్వడానికి కొన్ని ఇన్‌పుట్‌లు అవసరం: {missing}\nదయచేసి 'పొలం అంచనా' పేజీలో ఈ విలువలను నమోదు చేయండి."
                return f"The crop recommendation model requires additional inputs: {missing}\nPlease provide these values in the Farm Assessment form."

        if lang == "te":
            return (
                "పంట సిఫార్సులు చూడాలంటే **'పొలం అంచనా'** పేజీలో నేల విలువలు (N, P, K, pH) మరియు వాతావరణ డేటా నమోదు చేయండి.\n"
                "మీ సమర్పిత డేటా ఆధారంగా RandomForest మోడల్ ఖచ్చితమైన పంట సిఫార్సులు అందిస్తుంది."
            )
        return (
            "To get crop recommendations, navigate to **'Farm Assessment'** and enter soil values (N, P, K, pH) and weather data.\n"
            "The RandomForest model will generate precise crop recommendations based on your submitted data."
        )

    def _handle_weather(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment:
            src = assessment.weather_source
            if lang == "te":
                return (
                    f"మీ అంచనాలో వాతావరణ వనరు: **{src}**\n\n"
                    "ఓపెన్-మెటియో ద్వారా జిల్లా వాతావరణ డేటా అందుబాటులో ఉంటుంది.\n"
                    "ప్రత్యక్ష వాతావరణ డేటా కోసం **'వాతావరణం'** పేజీకి వెళ్ళండి."
                )
            return (
                f"Weather source for your assessment: **{src}**\n\n"
                "Live district weather data is sourced from Open-Meteo's free API.\n"
                "Visit the **'Weather'** page for real-time observations, or use the 'Fetch live weather' button in the assessment form."
            )
        if lang == "te":
            return (
                "మీ జిల్లా కోసం ప్రత్యక్ష వాతావరణం చూడాలంటే:\n"
                "1. **'వాతావరణం'** పేజీకి వెళ్ళండి\n"
                "2. 'ప్రత్యక్ష వాతావరణం పొందండి' బటన్ క్లిక్ చేయండి\n\n"
                "లేదా 'పొలం అంచనా' → దశ 3 లో ఓపెన్-మెటియో వాతావరణం ఆటోమేటిక్‌గా పొందవచ్చు."
            )
        return (
            "To view live weather for your district:\n"
            "1. Navigate to the **'Weather'** page\n"
            "2. Click the 'Fetch live district weather' button\n\n"
            "Or in the Farm Assessment form (Step 3), use the Open-Meteo fetch button to auto-fill weather data."
        )

    def _handle_model(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if lang == "te":
            return (
                "KshetraIQ మోడల్ రిజిస్ట్రీ:\n\n"
                "✅ **crop-recommendation-v1** — ధృవీకరించబడింది (RandomForest, 22 పంటలు)\n"
                "🚫 **crop-yield-v1** — నిలిపివేయబడింది (ఫీచర్ మ్యానిఫెస్ట్ లేదు)\n"
                "🚫 **weather-risk-v1** — నిలిపివేయబడింది (27 ఫీచర్లు అవసరం)\n"
                "🚫 **market-price-v1** — నిలిపివేయబడింది (APMC ధరల ధృవీకరణ పెండింగ్)\n"
                "🚫 **plant-disease-v1** — నిలిపివేయబడింది (లేబుల్ మ్యాప్ లేదు)\n\n"
                "ధృవీకరించబడని మోడల్‌లు కల్పిత అంచనాలు ఇవ్వవు — ఇది KshetraIQ భద్రతా విధానం.\n"
                "మోడల్ వివరాలు చూడాలంటే **'మోడల్ రిజిస్ట్రీ'** పేజీకి వెళ్ళండి."
            )
        return (
            "KshetraIQ Model Registry:\n\n"
            "✅ **crop-recommendation-v1** — Verified (RandomForest, 22 crops)\n"
            "🚫 **crop-yield-v1** — Blocked (feature manifest missing)\n"
            "🚫 **weather-risk-v1** — Blocked (requires 27 features)\n"
            "🚫 **market-price-v1** — Blocked (APMC price contracts unverified)\n"
            "🚫 **plant-disease-v1** — Blocked (label map missing)\n\n"
            "Unverified models never produce fabricated predictions — this is KshetraIQ's zero-fabrication safety policy.\n"
            "Visit the **'Model Registry'** page for full model details."
        )

    def _handle_report(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment:
            aid = assessment.assessment_id[:8]
            if lang == "te":
                return (
                    f"మీ అంచనా (ID: {aid}…) కోసం PDF నివేదిక తయారు చేయవచ్చు.\n\n"
                    "దశలు:\n"
                    "1. **'నివేదికలు'** పేజీకి వెళ్ళండి\n"
                    "2. 'PDF నివేదిక తయారు చేయండి' క్లిక్ చేయండి\n"
                    "3. సమీక్ష తర్వాత 'నిర్ధారించి డౌన్‌లోడ్ చేయండి' బటన్ ద్వారా PDF పొందండి\n\n"
                    "నివేదికలో నేల విశ్లేషణ, పంట సిఫార్సు, వ్యవసాయ సలహా మరియు డేటా వనరులు ఉంటాయి."
                )
            return (
                f"A PDF report is available for your assessment (ID: {aid}…).\n\n"
                "Steps:\n"
                "1. Navigate to the **'Reports'** page\n"
                "2. Click 'Generate PDF Report'\n"
                "3. Review the confirmation dialog and click 'Confirm & Download PDF'\n\n"
                "The report includes soil analysis, crop recommendation, agronomic advisory, and data sources."
            )
        if lang == "te":
            return "PDF నివేదిక పొందాలంటే మొదట **'పొలం అంచనా'** పూర్తి చేయండి."
        return "To generate a PDF report, first complete a **'Farm Assessment'**."

    def _handle_irrigation(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment and assessment.advisor:
            water = assessment.advisor.water_and_irrigation
            rec = water.get("recommendation_te" if lang == "te" else "recommendation", "")
            irr = water.get("irrigation_type", "")
            src = water.get("water_availability", "")
            if lang == "te":
                return f"**నీటి పారుదల విధానం:** {irr}\n**నీటి వనరు:** {src}\n\n{rec}"
            return f"**Irrigation method:** {irr}\n**Water source:** {src}\n\n{rec}"
        if lang == "te":
            return "నీటి నిర్వహణ సలహా చూడాలంటే **'పొలం అంచనా'** పూర్తి చేయండి.\nలేదా **'నీటి పారుదల'** పేజీకి వెళ్ళండి."
        return "To view water management advice, complete a **'Farm Assessment'** first.\nOr visit the **'Irrigation & Water'** page."

    def _handle_assessment(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if assessment:
            aid = assessment.assessment_id[:8]
            storage = assessment.storage
            if lang == "te":
                return (
                    f"మీ తాజా అంచనా (ID: {aid}…) విజయవంతంగా పూర్తయింది.\n"
                    f"నిల్వ: **{storage}**\n\n"
                    "ఫలితాలు చూడాలంటే **'పంట సిఫార్సులు'** పేజీకి వెళ్ళండి.\n"
                    "కొత్త అంచనా వేయాలంటే **'పొలం అంచనా'** పేజీకి వెళ్ళండి."
                )
            return (
                f"Your latest assessment (ID: {aid}…) completed successfully.\n"
                f"Storage: **{storage}**\n\n"
                "View results on the **'Crop Recommendations'** page.\n"
                "To run a new assessment, navigate to **'Farm Assessment'**."
            )
        if lang == "te":
            return (
                "పొలం అంచనా ప్రారంభించడానికి:\n"
                "1. **'పొలం అంచనా'** పేజీకి వెళ్ళండి\n"
                "2. దశ 1: పొలం మరియు స్థానం వివరాలు నమోదు చేయండి\n"
                "3. దశ 2: సాయిల్ హెల్త్ కార్డ్ నుండి N, P, K, pH విలువలు నమోదు చేయండి\n"
                "4. దశ 3: వాతావరణం — ఓపెన్-మెటియో ద్వారా ఆటో-ఫిల్ లేదా మాన్యువల్‌గా నమోదు చేయండి\n"
                "5. దశ 4: గతంలో వేసిన పంటలు మరియు ప్రాధాన్యతలు\n"
                "6. 'ధృవీకరించిన అంచనా ప్రారంభించండి' బటన్ క్లిక్ చేయండి"
            )
        return (
            "To start a farm assessment:\n"
            "1. Navigate to **'Farm Assessment'**\n"
            "2. Step 1: Enter farm name, district, state, acreage, season, irrigation\n"
            "3. Step 2: Enter N, P, K, pH from your Soil Health Card\n"
            "4. Step 3: Weather — auto-fill via Open-Meteo or enter manually\n"
            "5. Step 4: Previous crops and farmer preferences\n"
            "6. Click 'Run Verified Farm Assessment'"
        )

    def _handle_disease(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if lang == "te":
            return (
                "🚫 **మొక్కల తెగుళ్ల విశ్లేషణ ప్రస్తుతం అందుబాటులో లేదు.**\n\n"
                "plant_disease.h5 మోడల్ క్లాస్ లేబుల్ మ్యాపింగ్ మరియు TensorFlow రన్‌టైమ్ ధృవీకరణలో ఉంది.\n"
                "KshetraIQ ధృవీకరించబడని రోగనిర్ధారణలు ఇవ్వదు.\n\n"
                "మొక్కల తెగుళ్ల సమస్యలకు మీ సమీపంలోని KVK (కృషి విజ్ఞాన కేంద్రం) లేదా వ్యవసాయ అధికారిని సంప్రదించండి."
            )
        return (
            "🚫 **Plant disease analysis is currently unavailable.**\n\n"
            "The plant_disease.h5 model is pending class label mapping and TensorFlow runtime verification.\n"
            "KshetraIQ does not provide unverified diagnostic results.\n\n"
            "For plant disease concerns, please consult your nearest KVK (Krishi Vigyan Kendra) or Agricultural Extension Officer."
        )

    def _handle_market(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if lang == "te":
            return (
                "🚫 **మార్కెట్ ధరల సమాచారం ప్రస్తుతం అందుబాటులో లేదు.**\n\n"
                "APMC మండీ ధరల మోడల్ రన్‌టైమ్ ధృవీకరణలో ఉంది.\n"
                "KshetraIQ ఊహాజనిత లేదా కల్పిత మార్కెట్ ధరలను అందించదు.\n\n"
                "తాజా మార్కెట్ ధరల కోసం మీ జిల్లా APMC వెబ్‌సైట్ లేదా Agmarknet సందర్శించండి."
            )
        return (
            "🚫 **Market price information is currently unavailable.**\n\n"
            "The market price model and APMC Mandi price contracts require runtime verification.\n"
            "KshetraIQ does not provide fabricated or simulated market prices.\n\n"
            "For current market prices, visit your district APMC website or Agmarknet (agmarknet.gov.in)."
        )

    def _handle_help(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if lang == "te":
            return (
                "KshetraIQ సహాయ గైడ్:\n\n"
                "📋 **పొలం అంచనా** — నేల విలువలతో పంట సిఫార్సులు పొందండి\n"
                "🌱 **పంట సిఫార్సులు** — RandomForest మోడల్ ఫలితాలు చూడండి\n"
                "🌤 **వాతావరణం** — ఓపెన్-మెటియో ప్రత్యక్ష డేటా\n"
                "🧪 **నేల ఆరోగ్యం** — pH మరియు NPK విశ్లేషణ\n"
                "💧 **నీటి పారుదల** — నీటి నిర్వహణ సలహా\n"
                "📄 **నివేదికలు** — PDF డౌన్‌లోడ్ చేయండి\n"
                "⚙️ **సెట్టింగ్స్** — భాష, API URL మార్చండి\n\n"
                "ఏదైనా ప్రశ్న అడగండి — నేను మీ నేల, పంట, వాతావరణం గురించి వివరిస్తాను!"
            )
        return (
            "KshetraIQ Help Guide:\n\n"
            "📋 **Farm Assessment** — Get crop recommendations with your soil values\n"
            "🌱 **Crop Recommendations** — View RandomForest model results\n"
            "🌤 **Weather** — Open-Meteo live observations\n"
            "🧪 **Soil Health** — pH and NPK analysis\n"
            "💧 **Irrigation & Water** — Water management advisory\n"
            "📄 **Reports** — Download PDF dossiers\n"
            "⚙️ **Settings** — Change language, API URL\n\n"
            "Ask me anything about your soil, crops, weather, or the platform!"
        )

    def _handle_general(self, msg: str, lang: str, assessment: AssessmentResponse | None) -> str:
        if lang == "te":
            return (
                "నమస్కారం! నేను KshetraIQ రైతు సహాయకుడిని.\n\n"
                "నేను సహాయం చేయగలిగే విషయాలు:\n"
                "• మీ నేల పరీక్ష ఫలితాలు వివరించడం\n"
                "• పంట సిఫార్సులు ఎందుకు ఇవ్వబడ్డాయో వివరించడం\n"
                "• వాతావరణ సమాచారం అర్థం చేసుకోవడం\n"
                "• పొలం అంచనా ప్రక్రియలో సహాయం\n"
                "• నివేదిక తయారు చేయడం\n\n"
                "మీకు ఏ విషయం గురించి తెలుసుకోవాలి?"
            )
        return (
            "Hello! I'm the KshetraIQ Farm Assistant.\n\n"
            "I can help you with:\n"
            "• Understanding your soil test results\n"
            "• Explaining why a crop was recommended\n"
            "• Interpreting weather observations\n"
            "• Navigating the farm assessment process\n"
            "• Generating PDF reports\n\n"
            "What would you like to know?"
        )
