"""AudioProvider protocol and event types for voice AI providers."""

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass
class ProviderConfig:
    """Configuration passed to a provider on connect."""

    system_prompt: str
    voice: str
    model: str
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class AudioDelta:
    """Chunk of base64-encoded audio from the provider."""

    payload: str


@dataclass
class AudioDone:
    """Provider finished sending the current audio response."""


@dataclass
class SpeechStarted:
    """VAD detected the caller started speaking."""


@dataclass
class SpeechStopped:
    """VAD detected the caller stopped speaking."""


AudioEvent = AudioDelta | AudioDone | SpeechStarted | SpeechStopped


@runtime_checkable
class AudioProvider(Protocol):
    """Interface that all voice AI providers must implement."""

    async def connect(self, config: ProviderConfig) -> None:
        """Establish connection to the provider."""
        ...

    async def send_audio(self, audio_payload: str) -> None:
        """Send base64-encoded audio to the provider."""
        ...

    async def receive_audio(self) -> AsyncIterator[AudioEvent]:
        """Yield audio events from the provider."""
        ...

    async def disconnect(self) -> None:
        """Close the provider connection."""
        ...
