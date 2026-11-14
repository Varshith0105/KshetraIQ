"""
KshetraIQ Farm Assistant — Context-Aware Agricultural AI Agent Service.

Integrates the Global Context Collection Engine and LangGraph Orchestrator
with 9 Screen-Aware Specialist Agents. Uses real application data and never
fabricates predictions, chemical rates, or uncalibrated yields.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import Settings, get_settings
from app.schemas.assessment import AssessmentResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.activity_service import ActivityService, activity_service
from app.services.agriverse_service import AgriVerseChatService
from app.services.context_engine import ContextEngine, context_engine
from app.services.conversation_service import ConversationService, conversation_service
from app.services.langgraph_orchestrator import LangGraphOrchestrator, langgraph_orchestrator

logger = logging.getLogger(__name__)


class ChatService:
    """Context-aware agricultural chatbot that uses real assessment and screen data."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agriverse = AgriVerseChatService(self.settings)
        self.context_engine = ContextEngine(settings=self.settings)
        self.conversation_service = ConversationService(settings=self.settings)
        self.activity_service = ActivityService(settings=self.settings)
        self.orchestrator = LangGraphOrchestrator(settings=self.settings)

    def respond(
        self,
        request: ChatRequest,
        assessment: AssessmentResponse | None = None,
        user_id: str | None = None,
        past_assessments: list[AssessmentResponse] | None = None,
    ) -> ChatResponse:
        """Generate a context-aware, screen-aware, user-aware response using LangGraph Orchestrator."""
        lang = request.language
        msg_l = request.message.lower()

        # 1. Build Unified Multi-Tier Context
        ctx = self.context_engine.build_context(
            user_id=user_id,
            query=request.message,
            screen_context_payload=request.screen_context,
            assessment=assessment,
            past_assessments=past_assessments,
            conversation_id=request.conversation_id,
            language=lang,
            fallback_farm_context=request.farm_context,
        )

        # 2. Manage User Conversation Memory
        conv_id = request.conversation_id
        if user_id:
            try:
                conv_id = self.conversation_service.get_or_create_conversation(
                    conversation_id=request.conversation_id,
                    user_id=user_id,
                    initial_title=request.message,
                    screen_id=ctx.active_screen_id,
                    language=lang,
                )
                # Record incoming user turn
                self.conversation_service.add_message(
                    conversation_id=conv_id,
                    user_id=user_id,
                    sender="user",
                    message=request.message,
                    screen_id=ctx.active_screen_id,
                )
            except Exception as e:
                logger.debug("Failed managing user conversation memory: %s", e)

        # 3. Check for specific domain anchors
        # Help request
        if msg_l in {"help", "సహాయం", "help me get started"}:
            help_reply = self._handle_help(request.message, lang, assessment)
            res = ChatResponse(
                reply=help_reply,
                answer=help_reply,
                conversation_id=conv_id,
                mode="rule_based",
                provider="kshetraiq_system",
                assessment_context_used=assessment is not None,
                screen_context_used=request.screen_context is not None,
                screen_id=ctx.active_screen_id,
                disclaimer="Decision support guidance only." if lang == "en" else "ఈ సమాచారం సూచనల కొరకు మాత్రమే.",
            )
            if user_id and conv_id:
                try:
                    self.conversation_service.add_message(
                        conversation_id=conv_id,
                        user_id=user_id,
                        sender="assistant",
                        message=help_reply,
                        screen_id=ctx.active_screen_id,
                    )
                except Exception:
                    pass
            return res

        # 4. Run LangGraph Multi-Agent Orchestrator
        try:
            res = self.orchestrator.run(ctx)
            res.conversation_id = conv_id

            # If user has an assessment, ensure assessment_context_used is True
            if assessment is not None or ctx.user.has_assessment:
                res.assessment_context_used = True

            # Record assistant turn and log activity for authenticated users
            if user_id and conv_id:
                try:
                    self.conversation_service.add_message(
                        conversation_id=conv_id,
                        user_id=user_id,
                        sender="assistant",
                        message=res.reply,
                        screen_id=ctx.active_screen_id,
                        observed=res.observed,
                        analysis=res.analysis,
                        recommendation=res.recommendation,
                        next_actions=res.next_actions,
                    )
                    self.activity_service.log_activity(
                        user_id=user_id,
                        action="user_asked_ai",
                        entity_type="chat",
                        entity_id=conv_id,
                        metadata={
                            "screen_id": ctx.active_screen_id,
                            "query": request.message[:100],
                            "agents_used": res.agents_used,
                        },
                    )
                except Exception as e:
                    logger.debug("Error recording conversation message: %s", e)

            return res

        except Exception as err:
            logger.warning("LangGraph orchestrator failed: %s. Using safe fallback.", err)
            fallback_text = self._handle_general(request.message, lang, assessment)
            return ChatResponse(
                reply=fallback_text,
                answer=fallback_text,
                conversation_id=conv_id,
                mode="rule_based",
                provider="rule_based_fallback",
                assessment_context_used=assessment is not None,
                screen_context_used=False,
                screen_id=ctx.active_screen_id,
                disclaimer="Decision support guidance only.",
            )

    # ── Legacy Topic Fallback Handlers ──
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
                "• సాగునీటి నిర్వహణ మరియు బడ్జెట్\n"
                "• అధికారిక నివేదిక డౌన్‌లోడ్ చేయడం\n\n"
                "మీకు ఏ విషయం గురించి తెలుసుకోవాలి?"
            )
        return (
            "Hello! I'm the KshetraIQ Farm Assistant.\n\n"
            "I can help you with:\n"
            "• Understanding your soil test results and pH\n"
            "• Explaining why a crop was recommended\n"
            "• Precision irrigation volumetric budgets\n"
            "• Weather forecasts and safe spraying windows\n"
            "• Generating certified PDF dossiers\n\n"
            "What would you like to know?"
        )
