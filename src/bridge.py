"""Core bridge: relay audio between Twilio Media Stream and an AI provider."""

import asyncio
import json
import logging

from fastapi import WebSocket

from .config import Settings
from .provider import AudioDelta, AudioDone, ProviderConfig, SpeechStarted
from .providers import get_provider

logger = logging.getLogger(__name__)


async def run_bridge(websocket: WebSocket, settings: Settings) -> None:
    """Bridge audio between Twilio Media Stream and an AI provider."""
    provider = get_provider(settings.PROVIDER)
    stream_sid: str | None = None

    config = ProviderConfig(
        system_prompt=settings.SYSTEM_PROMPT,
        voice=settings.VOICE,
        model=settings.MODEL,
        extra={
            "api_key": settings.OPENAI_API_KEY,
            "initial_prompt": settings.INITIAL_PROMPT,
            "temperature": settings.TEMPERATURE,
            "vad_type": settings.VAD_TYPE,
            "vad_eagerness": settings.VAD_EAGERNESS,
            "allow_interrupt": settings.ALLOW_INTERRUPT,
        },
    )
    await provider.connect(config)

    async def receive_from_twilio() -> None:
        nonlocal stream_sid
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                event = data.get("event")

                if event == "start":
                    stream_sid = data["start"]["streamSid"]
                    logger.info("Stream started: %s", stream_sid)
                elif event == "media":
                    await provider.send_audio(data["media"]["payload"])
                elif event == "stop":
                    logger.info("Stream stopped")
                    break
        except Exception:
            logger.exception("Error receiving from Twilio")

    async def send_to_twilio() -> None:
        try:
            async for event in provider.receive_audio():  # type: ignore[attr-defined]
                if isinstance(event, AudioDelta) and stream_sid:
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": event.payload},
                    })
                elif isinstance(event, SpeechStarted) and stream_sid:
                    await websocket.send_json({
                        "event": "clear",
                        "streamSid": stream_sid,
                    })
                elif isinstance(event, AudioDone):
                    pass
        except Exception:
            logger.exception("Error sending to Twilio")

    try:
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
    finally:
        await provider.disconnect()
