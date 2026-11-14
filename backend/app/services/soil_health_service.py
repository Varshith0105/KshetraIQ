"""Transparent shared soil-health scoring for API, UI, and farmer reports."""
from __future__ import annotations

from typing import Any


class SoilHealthService:
    """Decision-support score; absent measurements are excluded, never imputed.

    Bands:
      80 - 100: Excellent
      60 - 79:  Good
      40 - 59:  Moderate
      20 - 39:  Poor
      0  - 19:  Critical
    """

    # General Indian soil-test screening bands (kg/ha; P as Olsen P, K as available K).
    _RANGES = {
        "nitrogen_kg_ha": (280.0, 560.0, "Nitrogen"),
        "phosphorus_kg_ha": (10.0, 25.0, "Phosphorus (Olsen P)"),
        "potassium_kg_ha": (120.0, 280.0, "Potassium (available K)"),
        "ph": (6.5, 7.5, "Soil pH"),
    }

    _KEY_ALIASES = {
        "nitrogen_kg_ha": ["nitrogen_kg_ha", "nitrogen", "n"],
        "phosphorus_kg_ha": ["phosphorus_kg_ha", "phosphorus", "p"],
        "potassium_kg_ha": ["potassium_kg_ha", "potassium", "k"],
        "ph": ["ph", "soil_ph"],
        "soil_moisture_percent": ["soil_moisture_percent", "soil_moisture", "moisture"],
    }

    @staticmethod
    def _extract_val(soil: Any, key: str) -> float | None:
        aliases = SoilHealthService._KEY_ALIASES.get(key, [key])
        if isinstance(soil, dict):
            for a in aliases:
                v = soil.get(a)
                if v is not None and v != "":
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        pass
            return None
        for a in aliases:
            v = getattr(soil, a, None)
            if v is not None and v != "":
                try:
                    return float(v)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _band_score(value: float, lower: float, upper: float) -> tuple[float, str]:
        if lower <= value <= upper:
            return 100.0, "optimal"
        width = max(upper - lower, 0.1)
        distance = lower - value if value < lower else value - upper
        return max(0.0, 100.0 * (1.0 - distance / width)), "low" if value < lower else "high"

    def assess(self, soil: Any) -> dict[str, Any]:
        parameters: dict[str, Any] = {}
        scores: list[float] = []
        deficiencies: list[str] = []
        excesses: list[str] = []
        recommendations: list[str] = []
        recommendations_te: list[str] = []

        for key, (lower, upper, label) in self._RANGES.items():
            value = self._extract_val(soil, key)
            if value is None:
                parameters[key] = {
                    "label": label,
                    "value": None,
                    "reference_range": f"{lower:g}-{upper:g}",
                    "status": "not assessed",
                    "score": None,
                }
                continue
            score, status = self._band_score(float(value), lower, upper)
            parameters[key] = {
                "label": label,
                "value": value,
                "reference_range": f"{lower:g}-{upper:g}",
                "status": status,
                "score": round(score, 1),
            }
            scores.append(score)

            if status == "low":
                deficiencies.append(label)
                if key == "nitrogen_kg_ha":
                    recommendations.append("Nitrogen is deficient. Apply 5–10 t/ha Farm Yard Manure (FYM), incorporate Dhaincha/Sunhemp green manure, or apply split doses of Neem-coated Urea.")
                    recommendations_te.append("నత్రజని లోపం ఉంది. ఎకరానికి 2-3 టన్నుల పశువుల ఎరువు వేయండి. జనుము లేదా జీలుగ పచ్చిరొట్ట ఎరువులు వాడండి మరియు వేప పూత పూసిన యూరియాను సమతుల్యంగా వేయండి.")
                elif key == "phosphorus_kg_ha":
                    recommendations.append("Phosphorus is deficient. Apply Single Super Phosphate (SSP) or DAP basal dose; inoculate seed with Phosphate Solubilizing Bacteria (PSB).")
                    recommendations_te.append("భాస్వరం లోపం ఉంది. విత్తే సమయంలో సింగిల్ సూపర్ ఫాస్ఫేట్ (SSP) లేదా DAP వేయండి; భాస్వరం కరిగించే బ్యాక్టీరియా (PSB) కల్చర్‌ను వాడండి.")
                elif key == "potassium_kg_ha":
                    recommendations.append("Potassium is deficient. Apply Muriate of Potash (MOP) to enhance pest/disease resistance, drought tolerance, and grain filling.")
                    recommendations_te.append("పొటాషియం లోపం ఉంది. మ్యూరేట్ ఆఫ్ పొటాష్ (MOP) వేయండి; ఇది పంటకు రోగనిరోధక శక్తిని, కరువు తట్టుకునే సామర్థ్యాన్ని మరియు గింజ బరువును పెంచుతుంది.")
                elif key == "ph":
                    recommendations.append(f"Soil pH is acidic ({value:.1f}). Apply agricultural lime (CaCO3) or dolomite at 1–2 t/ha to correct acidity and improve nutrient bioavailability.")
                    recommendations_te.append(f"నేల ఆమ్లతనం ({value:.1f}) కలిగి ఉంది. ఆమ్లత్వాన్ని తగ్గించి పోషకాలను అందించడానికి వ్యవసాయ సున్నం (డోలమైట్) వేయండి.")
            elif status == "high":
                excesses.append(label)
                if key == "nitrogen_kg_ha":
                    recommendations.append("Nitrogen is excessive. Reduce synthetic nitrogen application to prevent excessive vegetative growth, lodging, and pest attacks.")
                    recommendations_te.append("నత్రజని అధికంగా ఉంది. రసాయన యూరియా వినియోగాన్ని తగ్గించండి; దీనివల్ల చీడపీడల బెడద మరియు పైరు పడిపోవడం తగ్గుతుంది.")
                elif key == "phosphorus_kg_ha":
                    recommendations.append("Phosphorus is elevated. Suspend phosphate fertilizers; provide foliar zinc and iron sprays to prevent induced micronutrient deficiency.")
                    recommendations_te.append("భాస్వరం అధికంగా ఉంది. ఫాస్ఫేట్ ఎరువులను నిలిపివేయండి; జింక్ మరియు ఇనుము లోపాలు రాకుండా తగిన జాగ్రత్తలు తీసుకోండి.")
                elif key == "potassium_kg_ha":
                    recommendations.append("Potassium is elevated. Restrict potash inputs; monitor soil magnesium levels to prevent nutrient antagonism.")
                    recommendations_te.append("పొటాషియం ఎక్కువ మోతాదులో ఉంది. పొటాష్ వాడకాన్ని తగ్గించండి మరియు మెగ్నీషియం శోషణను పర్యవేక్షించండి.")
                elif key == "ph":
                    recommendations.append(f"Soil pH is alkaline ({value:.1f}). Apply agricultural gypsum (calcium sulfate) at 1–2 t/ha and add organic compost to lower pH.")
                    recommendations_te.append(f"నేల క్షార గుణం ({value:.1f}) కలిగి ఉంది. జిప్సం మరియు అధికంగా పశువుల ఎరువు వేసి నేల క్షారత్వాన్ని క్రమబద్ధీకరించండి.")
            else:
                if key == "ph":
                    recommendations.append(f"Soil pH ({value:.1f}) is in the optimal neutral range (6.5–7.5), providing ideal bioavailability for primary and secondary nutrients.")
                    recommendations_te.append(f"నేల pH ({value:.1f}) సమతుల్యంగా ఉంది. ఇది అన్ని పోషకాలు సులభంగా మొక్కలకు అందడానికి అనువైనది.")

        moisture = self._extract_val(soil, "soil_moisture_percent")
        parameters["soil_moisture_percent"] = {
            "label": "Soil moisture",
            "value": moisture,
            "status": "context required" if moisture is not None else "not assessed",
            "score": None,
        }

        score = round(sum(scores) / len(scores), 1) if scores else None

        # 5 Bands: 80-100 Excellent, 60-79 Good, 40-59 Moderate, 20-39 Poor, 0-19 Critical
        if score is None:
            category = "Not assessed"
            category_te = "పరిశీలించబడలేదు"
            badge_color = "gray"
        elif score >= 80:
            category = "Excellent"
            category_te = "అత్యుత్తమం"
            badge_color = "green"
        elif score >= 60:
            category = "Good"
            category_te = "మంచిది"
            badge_color = "teal"
        elif score >= 40:
            category = "Moderate"
            category_te = "మధ్యస్థం"
            badge_color = "amber"
        elif score >= 20:
            category = "Poor"
            category_te = "పేలవం"
            badge_color = "orange"
        else:
            category = "Critical"
            category_te = "క్లిష్టమైనది"
            badge_color = "red"

        if not recommendations:
            recommendations.append("All measured soil parameters (N-P-K and pH) are in optimal ranges. Maintain balanced crop rotation and organic fertility.")
            recommendations_te.append("పరీక్షించిన అన్ని నేల పోషకాలు (N-P-K మరియు pH) సరైన శ్రేణిలో ఉన్నాయి. పంట మార్పిడి మరియు సేంద్రియ ఎరువుల సమతుల్యతను కొనసాగించండి.")

        return {
            "score": score,
            "category": category,
            "category_te": category_te,
            "badge_color": badge_color,
            "is_provisional": len(scores) < 4,
            "assessed_parameter_count": len(scores),
            "parameters": parameters,
            "deficiencies": deficiencies,
            "excesses": excesses,
            "recommendations": recommendations,
            "recommendations_te": recommendations_te,
            "bands_guide": {
                "80-100": "Excellent",
                "60-79": "Good",
                "40-59": "Moderate",
                "20-39": "Poor",
                "0-19": "Critical",
            },
            "methodology": "Average of available N, P, K and pH parameter scores; missing measurements are excluded. General reference bands require local laboratory/crop validation and this index is not a certified soil test.",
            "reference_sources": "ICAR soil-test interpretation practice; Olsen P and available K laboratory methods. Local State Agricultural University/KVK guidance supersedes these screening bands.",
        }


soil_health_service = SoilHealthService()

