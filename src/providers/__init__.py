"""Provider registry: map names to AudioProvider implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .openai_realtime import OpenAIRealtimeProvider

if TYPE_CHECKING:
    from ..provider import AudioProvider

PROVIDERS: dict[str, type[Any]] = {
    "openai": OpenAIRealtimeProvider,
}


def get_provider(name: str) -> AudioProvider:
    """Instantiate a provider by name."""
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(PROVIDERS)}")
    return cls()  # type: ignore[no-any-return]
