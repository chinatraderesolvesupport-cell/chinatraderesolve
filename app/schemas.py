from __future__ import annotations

from typing import Literal
import re
from urllib.parse import parse_qsl, urlencode, urlsplit
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class ApplicationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    country: str = Field(default="", max_length=100)
    preferred_language: str = Field(default="English", max_length=30)
    purchasing_channel: str = Field(default="Other", max_length=80)
    amount_in_dispute: str = Field(default="", max_length=60)
    main_problem: str = Field(min_length=3, max_length=160)
    supplier_name: str = Field(default="", max_length=180)
    order_number: str = Field(default="", max_length=120)
    order_value: str = Field(default="", max_length=60)
    requested_result: str = Field(default="Not sure", max_length=120)
    description: str = Field(min_length=50, max_length=8000)
    company_website: str = Field(default="", max_length=200)
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=160)
    utm_content: str = Field(default="", max_length=160)
    landing_path: str = Field(default="", max_length=500)
    referrer: str = Field(default="", max_length=500)
    turnstile_token: str = Field(default="", max_length=2048, exclude=True)
    free_access_terms: bool
    sharing_authority: bool
    ai_consent: bool
    no_guarantee: bool

    @field_validator("full_name", "country", "supplier_name", "order_number", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> str:
        """Clean user text without destroying useful paragraph structure."""
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", "", text)
        lines = [" ".join(line.split()) for line in text.split("\n")]
        cleaned: list[str] = []
        blank_run = 0
        for line in lines:
            if line:
                cleaned.append(line)
                blank_run = 0
            elif cleaned and blank_run < 1:
                cleaned.append("")
                blank_run += 1
        return "\n".join(cleaned).strip()

    @field_validator("utm_source", "utm_medium", "utm_campaign", "utm_content", mode="before")
    @classmethod
    def normalize_campaign_value(cls, value: object) -> str:
        text = re.sub(r"[\x00-\x1f\x7f]+", "", str(value or ""))
        return " ".join(text.split()).strip()

    @field_validator("landing_path", mode="before")
    @classmethod
    def normalize_landing_path(cls, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            parsed = urlsplit(text)
        except ValueError:
            return ""
        path = parsed.path if parsed.path.startswith("/") else "/"
        allowed = {"lang", "utm_source", "utm_medium", "utm_campaign", "utm_content"}
        query = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=False) if key in allowed]
        return path + ("?" + urlencode(query) if query else "")

    @field_validator("referrer", mode="before")
    @classmethod
    def normalize_referrer(cls, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            parsed = urlsplit(text)
        except ValueError:
            return ""
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        host = parsed.hostname.lower()
        try:
            port = parsed.port
        except ValueError:
            return ""
        default_port = 80 if parsed.scheme == "http" else 443
        authority = f"{host}:{port}" if port and port != default_port else host
        return f"{parsed.scheme}://{authority}"

    @field_validator("free_access_terms", "sharing_authority", "no_guarantee")
    @classmethod
    def require_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Required consent is missing")
        return value


Decision = Literal["pilot_candidate", "needs_information", "human_review", "declined"]
RiskLevel = Literal["low", "medium", "high", "critical"]
StrengthCategory = Literal["insufficient", "unclear", "potentially_supportable", "supportable_for_review"]


class TriageResult(BaseModel):
    decision: Decision
    risk_level: RiskLevel
    priority: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    position_strength: StrengthCategory
    in_scope: bool
    hard_stop: bool
    reasons: list[str] = Field(default_factory=list, max_length=12)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    risk_flags: list[str] = Field(default_factory=list, max_length=12)
    recommended_action: str = Field(max_length=500)
    public_message: str = Field(max_length=500)
    source: Literal["rules", "ai", "rules+ai"] = "rules"


class StatusUpdate(BaseModel):
    status: Literal["submitted", "needs_information", "pilot_candidate", "human_review", "declined", "accepted", "closed"]
    note: str = Field(default="", max_length=1000)


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback_text: str = Field(min_length=10, max_length=3000)
    display_name: str = Field(default="", max_length=80)
    testimonial_consent: bool = False

    @field_validator("feedback_text", "display_name", mode="before")
    @classmethod
    def normalize_feedback_text(cls, value: object) -> str:
        return " ".join(str(value or "").split()).strip()


AssistantLanguage = Literal["en", "fr", "de", "es", "ru", "sr"]


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: object) -> str:
        return " ".join(str(value or "").split()).strip()


class AssistantChatRequest(BaseModel):
    language: AssistantLanguage = "en"
    messages: list[AssistantMessage] = Field(min_length=1, max_length=10)
    turnstile_token: str = Field(default="", max_length=2048, exclude=True)

    @model_validator(mode="after")
    def validate_conversation(self) -> "AssistantChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The final chat message must be from the user")
        if sum(len(message.content) for message in self.messages) > 10000:
            raise ValueError("Conversation is too long")
        return self


class AssistantChatResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)


class VoiceTranscriptionResponse(BaseModel):
    transcript: str = Field(min_length=1, max_length=8000)
