from __future__ import annotations

import asyncio
import base64
import json

import pytest

from app.voice_realtime import (
    RealtimeVoiceError,
    build_session_update,
    decode_pcm_chunk,
    relay_realtime_transcription,
)


def test_session_update_uses_pcm_24khz_and_selected_language() -> None:
    payload = build_session_update("ru")
    input_config = payload["session"]["audio"]["input"]
    assert payload["type"] == "session.update"
    assert payload["session"]["type"] == "transcription"
    assert input_config["format"] == {"type": "audio/pcm", "rate": 24000}
    assert input_config["transcription"]["model"] == "gpt-live-transcribe"
    assert input_config["transcription"]["languages"] == ["ru"]
    assert input_config["turn_detection"] is None


def test_decode_pcm_chunk_rejects_invalid_or_odd_audio() -> None:
    pcm = base64.b64encode(b"\x00\x00\x01\x00").decode("ascii")
    assert decode_pcm_chunk(pcm) == b"\x00\x00\x01\x00"
    with pytest.raises(RealtimeVoiceError):
        decode_pcm_chunk("not-base64")
    with pytest.raises(RealtimeVoiceError):
        decode_pcm_chunk(base64.b64encode(b"\x00").decode("ascii"))


class FakeUpstream:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.events: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False
        self.completed_seen = False

    async def __aenter__(self) -> "FakeUpstream":
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True

    async def send(self, value: str) -> None:
        self.sent.append(json.loads(value))
        if self.sent[-1]["type"] == "input_audio_buffer.commit":
            await self.events.put(json.dumps({
                "type": "conversation.item.input_audio_transcription.delta",
                "item_id": "item-1",
                "delta": "Привет",
            }))
            await self.events.put(json.dumps({
                "type": "conversation.item.input_audio_transcription.completed",
                "item_id": "item-1",
                "transcript": "Привет мир.",
            }))

    def __aiter__(self) -> "FakeUpstream":
        return self

    async def __anext__(self) -> str:
        if self.closed or self.completed_seen:
            raise StopAsyncIteration
        value = await self.events.get()
        if '"type": "conversation.item.input_audio_transcription.completed"' in value:
            self.completed_seen = True
        return value


def test_relay_forwards_audio_and_commit_and_maps_interim_results() -> None:
    async def scenario() -> tuple[FakeUpstream, list[dict]]:
        upstream = FakeUpstream()
        incoming = iter([
            {"type": "audio", "audio": base64.b64encode(b"\x00\x00" * 32).decode("ascii")},
            {"type": "commit"},
        ])
        outgoing: list[dict] = []

        async def receive() -> dict:
            return next(incoming)

        async def send(message: dict) -> None:
            outgoing.append(message)

        def connect_factory(*_args: object, **_kwargs: object) -> FakeUpstream:
            return upstream

        await relay_realtime_transcription(
            receive=receive,
            send=send,
            api_key="test-key",
            language="ru",
            connect_factory=connect_factory,
            max_seconds=15,
        )
        return upstream, outgoing

    upstream, outgoing = asyncio.run(scenario())
    assert outgoing[0] == {"type": "ready", "sample_rate": 24000}
    assert {message["type"] for message in outgoing} >= {"delta", "completed"}
    assert any(message["type"] == "completed" and message["text"] == "Привет мир." for message in outgoing)
    assert [message["type"] for message in upstream.sent] == [
        "session.update",
        "input_audio_buffer.append",
        "input_audio_buffer.commit",
    ]
    assert "test-key" not in json.dumps(outgoing)


def test_relay_provider_error_is_user_safe() -> None:
    async def scenario() -> list[dict]:
        class ErrorUpstream(FakeUpstream):
            async def __aenter__(self) -> "ErrorUpstream":
                await self.events.put(json.dumps({
                    "type": "error",
                    "error": {"type": "invalid_api_key", "message": "secret detail"},
                }))
                return self

        upstream = ErrorUpstream()
        outgoing: list[dict] = []

        async def receive() -> dict:
            await asyncio.sleep(10)
            return {"type": "close"}

        async def send(message: dict) -> None:
            outgoing.append(message)

        def connect_factory(*_args: object, **_kwargs: object) -> ErrorUpstream:
            return upstream

        with pytest.raises(RealtimeVoiceError, match="provider"):
            await relay_realtime_transcription(
                receive=receive,
                send=send,
                api_key="test-key",
                language="en",
                connect_factory=connect_factory,
            )
        return outgoing

    outgoing = asyncio.run(scenario())
    assert outgoing[-1] == {"type": "error", "code": "provider", "reason": "invalid_api_key"}
    assert "secret detail" not in json.dumps(outgoing)
