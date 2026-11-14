"""Pydantic schemas for the KshetraIQ Farm Assistant chatbot."""

from typing import Annotated, Any
from pydantic import BaseModel, Field


class ScreenContextPayload(BaseModel):
    """Context transmitted from the active user screen/dashboard view."""
    screen_id: str = Field(
        ...,
        description="Active screen identifier (e.g. dashboard, soil, recommendations, results, weather, irrigation, market, disease, reports, registry, profile, settings)"
    )
    screen_title: str | None = None
    route: str | None = None
    selected_crop: str | None = None
    filters: dict[str, Any] | None = None
    displayed_data: dict[str, Any] | None = None
    active_tab: str | None = None


class UserActivityPayload(BaseModel):
    """Payload to record a user activity event."""
    action: str = Field(..., min_length=1, max_length=100)
    entity_type: str | None = Field(default=None, max_length=50)
    entity_id: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] | None = None


class UserActivityResponse(BaseModel):
    """Activity event stored in the system."""
    id: str
    user_id: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str


class ConversationSummary(BaseModel):
    """Summary of a saved conversation."""
    conversation_id: str
    title: str
    screen_id: str | None = None
    language: str = "en"
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatMessageItem(BaseModel):
    """Single message in a conversation."""
    message_id: str
    conversation_id: str
    sender: str  # "user" | "assistant"
    message: str
    screen_id: str | None = None
    observed: str | None = None
    analysis: str | None = None
    recommendation: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    created_at: str


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    conversation_id: str | None = None
    language: str = "en"
    assessment_id: str | None = None
    farm_context: dict[str, Any] | None = None
    screen_context: ScreenContextPayload | dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    answer: str | None = None
    conversation_id: str | None = None
    mode: str = "rule_based"  # "llm" or "rule_based"
    provider: str = "rule_based_icar"  # "gemini" | "groq" | "openai" | "rule_based_icar" | "kshetraiq_orchestrator"
    source_context: str | None = None
    assessment_context_used: bool = False
    screen_context_used: bool = False
    screen_id: str | None = None
    agents_used: list[str] = Field(default_factory=list)
    observed: str | None = None
    analysis: str | None = None
    recommendation: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    disclaimer: str = ""

    def model_post_init(self, __context: object) -> None:
        if self.answer is None:
            self.answer = self.reply
