from __future__ import annotations

import logging
from typing import Any

import httpx

from .ai_assistant import _clean_output_text, _provider_error_fields, assistant_is_enabled
from .config import settings


logger = logging.getLogger("chinatraderesolve.voice_transcription")

MAX_VOICE_AUDIO_BYTES = 4 * 1024 * 1024
SUPPORTED_AUDIO_TYPES: dict[str, tuple[str, str]] = {
    "audio/webm": ("voice.webm", "audio/webm"),
    "video/webm": ("voice.webm", "audio/webm"),
    "audio/mp4": ("voice.m4a", "audio/mp4"),
    "audio/mpeg": ("voice.mp3", "audio/mpeg"),
    "audio/wav": ("voice.wav", "audio/wav"),
    "audio/x-wav": ("voice.wav", "audio/wav"),
}
LANGUAGE_CODES = {"en", "fr", "de", "es", "ru", "sr"}


class VoiceConfigurationError(RuntimeError):
    """Raised when voice transcription is not configured."""


class VoiceProviderError(RuntimeError):
    """Raised when the transcription provider fails."""


class VoiceValidationError(ValueError):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(kind)


def voice_input_is_enabled() -> bool:
    return bool(
        settings.enable_voice_input
        and assistant_is_enabled()
        and settings.openai_transcription_model
    )


def validate_voice_audio(audio_bytes: bytes, content_type: str | None) -> tuple[str, str]:
    if not audio_bytes:
        raise VoiceValidationError("invalid")
    if len(audio_bytes) > MAX_VOICE_AUDIO_BYTES:
        raise VoiceValidationError("too_large")
    normalized_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in SUPPORTED_AUDIO_TYPES:
        raise VoiceValidationError("invalid")
    return SUPPORTED_AUDIO_TYPES[normalized_type]


async def transcribe_audio(
    audio_bytes: bytes,
    content_type: str | None,
    language: str,
    safety_identifier: str,
) -> str:
    if not voice_input_is_enabled():
        raise VoiceConfigurationError("Voice transcription is not configured")
    filename, normalized_type = validate_voice_audio(audio_bytes, content_type)
    language_code = language if language in LANGUAGE_CODES else "en"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    if safety_identifier:
        headers["OpenAI-Safety-Identifier"] = safety_identifier
    data: dict[str, Any] = {
        "model": str(settings.openai_transcription_model),
        "language": language_code,
        "response_format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=max(30, settings.openai_timeout_seconds)) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=data,
                files={"file": (filename, audio_bytes, normalized_type)},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        fields = _provider_error_fields(exc.response)
        logger.warning(
            "OpenAI transcription HTTP error model=%s status=%s type=%s code=%s param=%s request_id=%s message=%s",
            settings.openai_transcription_model,
            exc.response.status_code,
            fields["type"],
            fields["code"],
            fields["param"],
            exc.response.headers.get("x-request-id", "none"),
            fields["message"],
        )
        raise VoiceProviderError("Transcription provider returned an error") from exc
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning(
            "OpenAI transcription request failed model=%s error_type=%s",
            settings.openai_transcription_model,
            type(exc).__name__,
        )
        raise VoiceProviderError("Transcription provider request failed") from exc
    if not isinstance(payload, dict):
        raise VoiceProviderError("Transcription provider returned an invalid response")
    transcript = _clean_output_text(str(payload.get("text") or ""))[:8000]
    if not transcript:
        raise VoiceProviderError("Transcription provider returned no text")
    return transcript
