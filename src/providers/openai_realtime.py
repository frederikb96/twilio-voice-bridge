"""OpenAI Realtime API provider using native g711_ulaw over WebSocket."""

import json
import logging
from collections.abc import AsyncIterator

import websockets

from ..provider import (
    AudioDelta,
    AudioDone,
    AudioEvent,
    ProviderConfig,
    SpeechStarted,
    SpeechStopped,
)

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class OpenAIRealtimeProvider:
    """AudioProvider implementation for OpenAI Realtime API."""

    def __init__(self) -> None:
        self._ws: websockets.ClientConnection | None = None

    async def connect(self, config: ProviderConfig) -> None:
        """Open WebSocket to OpenAI Realtime and configure the session."""
        api_key = config.extra.get("api_key", "")
        url = f"{OPENAI_REALTIME_URL}?model={config.model}"

        self._ws = await websockets.connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
        )

        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": config.voice,
                "instructions": config.system_prompt,
                "modalities": ["audio", "text"],
            },
        }
        await self._ws.send(json.dumps(session_update))
        logger.info("Connected to OpenAI Realtime (model=%s)", config.model)

    async def send_audio(self, audio_payload: str) -> None:
        """Forward base64-encoded g711_ulaw audio to OpenAI."""
        if self._ws is None:
            return
        await self._ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_payload,
        }))

    async def receive_audio(self) -> AsyncIterator[AudioEvent]:
        """Yield AudioEvents from the OpenAI Realtime stream."""
        if self._ws is None:
            return
        async for raw in self._ws:
            data = json.loads(raw)
            event_type = data.get("type", "")

            if event_type == "response.audio.delta":
                delta = data.get("delta", "")
                if delta:
                    yield AudioDelta(payload=delta)
            elif event_type == "response.audio.done":
                yield AudioDone()
            elif event_type == "input_audio_buffer.speech_started":
                yield SpeechStarted()
            elif event_type == "input_audio_buffer.speech_stopped":
                yield SpeechStopped()

    async def disconnect(self) -> None:
        """Close the OpenAI WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from OpenAI Realtime")
