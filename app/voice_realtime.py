from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

from .voice_transcription import LANGUAGE_CODES, TRANSCRIPTION_PROMPTS


logger = logging.getLogger("chinatraderesolve.voice_realtime")

REALTIME_URL = "wss://api.openai.com/v1/realtime"
REALTIME_AUDIO_RATE = 24_000
MAX_AUDIO_CHUNK_BYTES = 96 * 1024
MAX_AUDIO_BYTES = REALTIME_AUDIO_RATE * 2 * 300
MAX_CLIENT_MESSAGE_BYTES = 140 * 1024
STOP_DRAIN_SECONDS = 8.0


class RealtimeVoiceError(RuntimeError):
    """A safe, user-facing error from the realtime transcription path."""


def normalize_language(language: str) -> str:
    return language if language in LANGUAGE_CODES else "en"


def build_session_update(language: str, model: str = "gpt-live-transcribe") -> dict[str, Any]:
    language_code = normalize_language(language)
    return {
        "type": "session.update",
        "session": {
            "type": "transcription",
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": REALTIME_AUDIO_RATE},
                    "transcription": {
                        "model": model,
                        "languages": [language_code],
                        "prompt": TRANSCRIPTION_PROMPTS.get(language_code, TRANSCRIPTION_PROMPTS["en"]),
                    },
                    "turn_detection": None,
                }
            },
        },
    }


def decode_pcm_chunk(value: Any) -> bytes:
    if not isinstance(value, str) or not value or len(value) > MAX_CLIENT_MESSAGE_BYTES:
        raise RealtimeVoiceError("invalid_audio")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RealtimeVoiceError("invalid_audio") from exc
    if not decoded or len(decoded) > MAX_AUDIO_CHUNK_BYTES or len(decoded) % 2:
        raise RealtimeVoiceError("invalid_audio")
    return decoded


def _provider_message(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("type") or "")
    if event_type == "conversation.item.input_audio_transcription.delta":
        return {
            "type": "delta",
            "item_id": str(event.get("item_id") or ""),
            "text": str(event.get("delta") or ""),
        }
    if event_type == "conversation.item.input_audio_transcription.completed":
        return {
            "type": "completed",
            "item_id": str(event.get("item_id") or ""),
            "text": str(event.get("transcript") or ""),
        }
    if event_type == "error":
        error = event.get("error")
        error_type = error.get("type") if isinstance(error, dict) else "provider_error"
        return {"type": "error", "code": "provider", "reason": str(error_type or "provider_error")[:80]}
    return None


async def relay_realtime_transcription(
    *,
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
    api_key: str,
    language: str,
    model: str = "gpt-live-transcribe",
    safety_identifier: str = "",
    max_seconds: int = 120,
    connect_factory: Callable[..., Any] = websockets.connect,
) -> None:
    """Relay PCM16 chunks to OpenAI and expose only transcript events to the browser.

    Audio and transcript contents are deliberately kept in local variables only.  The
    caller owns authentication, rate limits, and the browser WebSocket lifecycle.
    """
    if not api_key:
        raise RealtimeVoiceError("unavailable")
    if not model:
        raise RealtimeVoiceError("unavailable")
    if max_seconds < 1:
        raise RealtimeVoiceError("invalid_config")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }
    if safety_identifier:
        headers["OpenAI-Safety-Identifier"] = safety_identifier

    try:
        async with connect_factory(
            f"{REALTIME_URL}?model={model}",
            additional_headers=headers,
            open_timeout=10,
            ping_interval=20,
            ping_timeout=20,
            max_size=1024 * 1024,
        ) as upstream:
            await upstream.send(json.dumps(build_session_update(language, model), ensure_ascii=False))
            await send({"type": "ready", "sample_rate": REALTIME_AUDIO_RATE})
            total_audio = 0
            stopping = False
            deadline = asyncio.get_running_loop().time() + max_seconds

            async def client_to_upstream() -> None:
                nonlocal total_audio, stopping
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise RealtimeVoiceError("too_long")
                    try:
                        message = await asyncio.wait_for(receive(), timeout=remaining)
                    except asyncio.TimeoutError as exc:
                        raise RealtimeVoiceError("too_long") from exc
                    kind = str(message.get("type") or "")
                    if kind == "audio":
                        if stopping:
                            continue
                        pcm = decode_pcm_chunk(message.get("audio"))
                        total_audio += len(pcm)
                        if total_audio > MAX_AUDIO_BYTES:
                            raise RealtimeVoiceError("too_long")
                        if asyncio.get_running_loop().time() > deadline:
                            raise RealtimeVoiceError("too_long")
                        await upstream.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(pcm).decode("ascii"),
                        }))
                    elif kind == "commit":
                        if not stopping:
                            stopping = True
                            await upstream.send(json.dumps({"type": "input_audio_buffer.commit"}))
                        return
                    elif kind == "close":
                        return
                    else:
                        raise RealtimeVoiceError("invalid_message")

            async def upstream_to_client() -> None:
                async for raw_event in upstream:
                    try:
                        event = json.loads(raw_event)
                    except (TypeError, ValueError):
                        continue
                    if not isinstance(event, dict):
                        continue
                    mapped = _provider_message(event)
                    if mapped:
                        await send(mapped)
                    if mapped and mapped.get("type") == "error":
                        raise RealtimeVoiceError("provider")

            client_task = asyncio.create_task(client_to_upstream())
            provider_task = asyncio.create_task(upstream_to_client())
            try:
                done, pending = await asyncio.wait(
                    {client_task, provider_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if client_task in done:
                    client_error = client_task.exception()
                    if client_error:
                        raise client_error
                    if stopping:
                        try:
                            await asyncio.wait_for(provider_task, timeout=STOP_DRAIN_SECONDS)
                        except asyncio.TimeoutError:
                            pass
                    else:
                        await provider_task
                else:
                    provider_error = provider_task.exception()
                    if provider_error:
                        raise provider_error
                    await client_task
            finally:
                for task in (client_task, provider_task):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(client_task, provider_task, return_exceptions=True)
    except RealtimeVoiceError:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Do not log provider messages, audio, transcripts, or request headers.
        logger.warning("realtime transcription connection failed error_type=%s", type(exc).__name__)
        raise RealtimeVoiceError("provider") from exc
