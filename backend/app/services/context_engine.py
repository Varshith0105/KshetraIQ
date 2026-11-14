"""
KshetraIQ Global Context Collection Engine.

Collects and harmonizes the 4 essential categories of context:
  1. User Context (Auth identity, farmer profile, farm profile, soil NPK/pH, assessments, predictions, language)
  2. Screen Context (Active view, displayed numbers, filters, chart stats, selected crop)
  3. User Activity Context (Recent actions, navigation timestamps, entity references)
  4. Conversation Context (Session memory, multi-turn follow-ups, entity references)

Enforces strict backend authorization: user identity is NEVER trusted from frontend payload.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.schemas.assessment import AssessmentResponse
from app.schemas.chat import ChatMessageItem, ScreenContextPayload, UserActivityResponse
from app.services.activity_service import ActivityService, activity_service
from app.services.auth_service import AuthService, FarmProfileResponse, UserProfileResponse
from app.services.conversation_service import ConversationService, conversation_service
from app.services.prediction_history_service import PredictionHistoryService, prediction_history_service

logger = logging.getLogger(__name__)


class UserContext:
    """Consolidated user profile, farm records, and historical ML predictions."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        user_profile: Optional[UserProfileResponse] = None,
        farm_profile: Optional[FarmProfileResponse] = None,
        latest_assessment: Optional[AssessmentResponse] = None,
        past_assessments: Optional[List[AssessmentResponse]] = None,
        prediction_history: Optional[List[Dict[str, Any]]] = None,
        language: str = "en",
    ) -> None:
        self.user_id = user_id
        self.user_profile = user_profile
        self.farm_profile = farm_profile
        self.latest_assessment = latest_assessment
        self.past_assessments = past_assessments or []
        self.prediction_history = prediction_history or []
        self.language = language
        self.has_assessment = latest_assessment is not None

        # Derived farm attributes
        self.farm_name = (
            (farm_profile.farm_name if farm_profile else None)
            or (latest_assessment.input.farm_name if latest_assessment else "My Farm")
        )
        self.state = (
            (farm_profile.state if farm_profile else None)
            or (latest_assessment.input.state if latest_assessment else "Andhra Pradesh")
        )
        self.district = (
            (farm_profile.district if farm_profile else None)
            or (latest_assessment.input.district if latest_assessment else "Guntur")
        )
        self.acreage = float(
            (farm_profile.acreage if farm_profile else None)
            or (latest_assessment.input.acreage if latest_assessment else 2.5)
        )
        self.season = (
            (farm_profile.season if farm_profile else None)
            or (latest_assessment.input.season if latest_assessment else "Kharif")
        )
        self.irrigation_type = (
            (farm_profile.irrigation_method if farm_profile else None)
            or (latest_assessment.input.irrigation_type if latest_assessment else "Drip")
        )
        self.water_availability = (
            (farm_profile.water_availability if farm_profile else None)
            or (latest_assessment.input.water_availability if latest_assessment else "Borewell")
        )

        # Derived soil values
        if latest_assessment and latest_assessment.input.soil:
            s = latest_assessment.input.soil
            self.nitrogen = s.nitrogen_kg_ha
            self.phosphorus = s.phosphorus_kg_ha
            self.potassium = s.potassium_kg_ha
            self.ph = s.ph
        else:
            self.nitrogen = None
            self.phosphorus = None
            self.potassium = None
            self.ph = None

        # Recommended crop from latest assessment
        self.recommended_crop = None
        self.recommended_crop_confidence = None
        self.alternative_crops = []
        if latest_assessment:
            for r in latest_assessment.results:
                if r.model_id == "crop-recommendation-v1" and r.prediction:
                    self.recommended_crop = r.prediction.recommended_crop
                    self.recommended_crop_confidence = r.prediction.confidence
                    self.alternative_crops = [
                        c.crop for c in (r.prediction.top_candidates or [])
                        if c.crop.lower() != r.prediction.recommended_crop.lower()
                    ]
                    break

    def to_dict(self) -> Dict[str, Any]:
        # Compute assessment stats
        completed_assessments = []
        incomplete_assessments = []
        for a in self.past_assessments:
            has_crop_rec = any(
                r.model_id == "crop-recommendation-v1" and r.prediction is not None
                for r in (a.results or [])
            )
            if has_crop_rec:
                completed_assessments.append(a)
            else:
                incomplete_assessments.append(a)

        # Group predictions by model for quick agent access
        predictions_by_model: Dict[str, Any] = {}
        for p in self.prediction_history:
            mid = p.get("model_id", "")
            if mid not in predictions_by_model:
                predictions_by_model[mid] = p

        return {
            "user_id": self.user_id,
            "farmer_name": self.user_profile.full_name if self.user_profile else "Farmer",
            "farm_name": self.farm_name,
            "location": f"{self.district}, {self.state}",
            "district": self.district,
            "state": self.state,
            "acreage": self.acreage,
            "season": self.season,
            "irrigation_type": self.irrigation_type,
            "water_availability": self.water_availability,
            "soil": {
                "nitrogen": self.nitrogen,
                "phosphorus": self.phosphorus,
                "potassium": self.potassium,
                "ph": self.ph,
            },
            "recommended_crop": self.recommended_crop,
            "recommended_crop_confidence": self.recommended_crop_confidence,
            "alternative_crops": self.alternative_crops,
            "has_assessment": self.latest_assessment is not None,
            "past_assessments_count": len(self.past_assessments),
            "completed_assessments_count": len(completed_assessments),
            "incomplete_assessments_count": len(incomplete_assessments),
            "prediction_history_count": len(self.prediction_history),
            "predictions_by_model": predictions_by_model,
            "language": self.language,
        }


class GlobalContext:
    """Holistic representation of user, active screen, activities, and dialogue memory."""

    def __init__(
        self,
        user_context: UserContext,
        screen_context: Optional[ScreenContextPayload] = None,
        recent_activities: Optional[List[UserActivityResponse]] = None,
        conversation_history: Optional[List[ChatMessageItem]] = None,
        query: str = "",
    ) -> None:
        self.user = user_context
        self.screen = screen_context
        self.activities = recent_activities or []
        self.history = conversation_history or []
        self.query = query

    @property
    def active_screen_id(self) -> str:
        if self.screen and self.screen.screen_id:
            return self.screen.screen_id.lower().strip()
        return "dashboard"

    @property
    def displayed_data(self) -> Dict[str, Any]:
        if self.screen and self.screen.displayed_data:
            return self.screen.displayed_data
        return {}

    @property
    def selected_crop(self) -> Optional[str]:
        if self.screen and self.screen.selected_crop:
            return self.screen.selected_crop
        if self.user.recommended_crop:
            return self.user.recommended_crop
        return None

    def get_conversation_entities(self) -> Dict[str, Any]:
        """Extract recent topics, crops, and recommendations from past conversation turns."""
        entities: Dict[str, Any] = {
            "last_crop_discussed": None,
            "last_action_suggested": None,
            "previous_user_question": None,
            "previous_bot_answer": None,
            "turns_count": len(self.history),
        }
        for msg in reversed(self.history):
            if msg.sender == "assistant" and not entities["previous_bot_answer"]:
                entities["previous_bot_answer"] = msg.message
                if msg.recommendation and not entities["last_action_suggested"]:
                    entities["last_action_suggested"] = msg.recommendation
            elif msg.sender == "user" and not entities["previous_user_question"]:
                entities["previous_user_question"] = msg.message

            # Search message for crop mentions
            for c in ["rice", "cotton", "maize", "groundnut", "chilli", "wheat", "coffee", "bengal gram"]:
                if c in msg.message.lower() and not entities["last_crop_discussed"]:
                    entities["last_crop_discussed"] = c.title()

        return entities


class ContextEngine:
    """Collects and aggregates the full multi-tier context safely from backend sources."""

    def __init__(self, settings: Optional[Settings] = None, auth_service: Optional[AuthService] = None) -> None:
        if settings is None:
            from app.core.config import get_settings
            self.settings = get_settings()
        else:
            self.settings = settings

        if auth_service is None:
            self.auth_service = AuthService(settings=self.settings)
        else:
            self.auth_service = auth_service

        self.activity_service = ActivityService(settings=self.settings)
        self.conversation_service = ConversationService(settings=self.settings)
        self.prediction_history_service = PredictionHistoryService(settings=self.settings)

    def build_context(
        self,
        user_id: Optional[str],
        query: str,
        screen_context_payload: Optional[ScreenContextPayload | dict[str, Any]] = None,
        assessment: Optional[AssessmentResponse] = None,
        past_assessments: Optional[List[AssessmentResponse]] = None,
        conversation_id: Optional[str] = None,
        language: str = "en",
        fallback_farm_context: Optional[dict[str, Any]] = None,
    ) -> GlobalContext:
        """Construct the complete context object without trusting client-side claims."""
        # 1. Parse screen context payload
        screen: Optional[ScreenContextPayload] = None
        if isinstance(screen_context_payload, ScreenContextPayload):
            screen = screen_context_payload
        elif isinstance(screen_context_payload, dict):
            try:
                screen = ScreenContextPayload.model_validate(screen_context_payload)
            except Exception as e:
                logger.debug("Failed parsing screen context payload: %s", e)

        # 2. Retrieve user and farm profile from DB if user_id is authenticated
        user_profile: Optional[UserProfileResponse] = None
        farm_profile: Optional[FarmProfileResponse] = None
        recent_activities: List[UserActivityResponse] = []
        conversation_history: List[ChatMessageItem] = []

        if user_id:
            try:
                farm_profile = self.auth_service.get_farm_profile(user_id)
            except Exception as e:
                logger.debug("Error fetching farm profile for user %s: %s", user_id, e)

            try:
                # We can also lookup user details
                conn = self.auth_service._get_connection()
                try:
                    cur = conn.execute(
                        "SELECT id, email, phone_number, full_name, auth_provider, avatar_url, created_at FROM users WHERE id = ?",
                        (user_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        user_profile = UserProfileResponse(
                            user_id=row["id"],
                            email=row["email"],
                            phone_number=row["phone_number"],
                            full_name=row["full_name"],
                            auth_provider=row["auth_provider"],
                            avatar_url=row["avatar_url"],
                            created_at=row["created_at"],
                        )
                finally:
                    conn.close()
            except Exception as e:
                logger.debug("Error fetching user profile for user %s: %s", user_id, e)

            # Retrieve recent activity trail
            try:
                recent_activities = self.activity_service.get_recent_activities(user_id, limit=10)
            except Exception as e:
                logger.debug("Error fetching activities for user %s: %s", user_id, e)

            # Retrieve conversation memory
            if conversation_id:
                try:
                    conversation_history = self.conversation_service.get_messages(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        limit=12,
                    )
                except Exception as e:
                    logger.debug("Error fetching conversation history for %s: %s", conversation_id, e)

        # 2b. Retrieve prediction history from model_predictions table
        prediction_history_records: List[Dict[str, Any]] = []
        if user_id:
            try:
                records = self.prediction_history_service.list_predictions(
                    user_id=user_id, limit=20
                )
                prediction_history_records = [r.to_dict() for r in records]
            except Exception as e:
                logger.debug("Error fetching prediction history for user %s: %s", user_id, e)

        # 3. Create UserContext
        user_ctx = UserContext(
            user_id=user_id,
            user_profile=user_profile,
            farm_profile=farm_profile,
            latest_assessment=assessment,
            past_assessments=past_assessments,
            prediction_history=prediction_history_records,
            language=language,
        )

        # If fallback farm_context dict was provided (e.g. from tests or legacy API calls)
        if fallback_farm_context and isinstance(fallback_farm_context, dict):
            if "soil" in fallback_farm_context and isinstance(fallback_farm_context["soil"], dict):
                s = fallback_farm_context["soil"]
                if user_ctx.nitrogen is None and "nitrogen_kg_ha" in s:
                    user_ctx.nitrogen = s["nitrogen_kg_ha"]
                if user_ctx.phosphorus is None and "phosphorus_kg_ha" in s:
                    user_ctx.phosphorus = s["phosphorus_kg_ha"]
                if user_ctx.potassium is None and "potassium_kg_ha" in s:
                    user_ctx.potassium = s["potassium_kg_ha"]
                if user_ctx.ph is None and "ph" in s:
                    user_ctx.ph = s["ph"]
            if "recommended_crop" in fallback_farm_context and not user_ctx.recommended_crop:
                user_ctx.recommended_crop = fallback_farm_context["recommended_crop"]

        return GlobalContext(
            user_context=user_ctx,
            screen_context=screen,
            recent_activities=recent_activities,
            conversation_history=conversation_history,
            query=query,
        )


# Global singleton
context_engine = ContextEngine()
