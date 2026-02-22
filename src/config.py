"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables and .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    PORT: int = 5050
    LOG_LEVEL: str = "INFO"
    TWILIO_AUTH_TOKEN: str
    ALLOWED_CALLERS: str = ""
    PROVIDER: str = "openai"
    SYSTEM_PROMPT: str = "You are a helpful voice assistant."
    VOICE: str = "alloy"
    MODEL: str = "gpt-4o-realtime-preview"
    OPENAI_API_KEY: str = ""
    MAX_CALL_DURATION: int = 300

    @property
    def allowed_caller_list(self) -> list[str]:
        """Split ALLOWED_CALLERS into a list, filtering empty strings."""
        return [c.strip() for c in self.ALLOWED_CALLERS.split(",") if c.strip()]
