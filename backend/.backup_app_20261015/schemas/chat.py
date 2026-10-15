"""Pydantic schemas for the KshetraIQ Farm Assistant chatbot."""

from typing import Annotated
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    conversation_id: str | None = None
    language: str = "en"
    assessment_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    answer: str | None = None
    conversation_id: str | None = None
    mode: str  # "llm" or "rule_based"
    provider: str = "rule_based_icar"  # "gemini" | "groq" | "openai" | "rule_based_icar"
    source_context: str | None = None
    assessment_context_used: bool = False
    disclaimer: str = ""

    def model_post_init(self, __context: object) -> None:
        if self.answer is None:
            self.answer = self.reply
