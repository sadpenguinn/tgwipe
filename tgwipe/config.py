import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    phone: str
    session_name: str = "tgwipe"
    # Delay between delete requests in seconds
    request_delay: float = 0.5
    # Number of message IDs to buffer before sending a delete request
    batch_size: int = 100
    # API key from console.anthropic.com; required when --ai-filter is used
    anthropic_api_key: str | None = None
    # Number of messages sent to Claude in a single analysis request
    ai_batch_size: int = 10
    # Claude model used for analysis
    ai_model: str = "claude-sonnet-4-6"
    # System prompt for the AI filter; overrides the built-in default when set
    ai_prompt: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        api_id_raw = _require_env("TELEGRAM_API_ID")
        try:
            api_id = int(api_id_raw)
        except ValueError:
            raise ConfigError("TELEGRAM_API_ID must be a valid integer")

        return cls(
            api_id=api_id,
            api_hash=_require_env("TELEGRAM_API_HASH"),
            phone=_require_env("TELEGRAM_PHONE"),
            session_name=os.getenv("TGWIPE_SESSION_NAME", "tgwipe"),
            request_delay=float(os.getenv("TGWIPE_REQUEST_DELAY", "0.5")),
            batch_size=int(os.getenv("TGWIPE_BATCH_SIZE", "100")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            ai_batch_size=int(os.getenv("TGWIPE_AI_BATCH_SIZE", "10")),
            ai_model=os.getenv("TGWIPE_AI_MODEL", "claude-sonnet-4-6"),
            ai_prompt=os.getenv("TGWIPE_AI_PROMPT") or None,
        )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(
            f"Required environment variable '{name}' is not set.\n"
            f"Copy .env.example to .env and fill in your credentials."
        )
    return value
