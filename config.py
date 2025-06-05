"""Bot configuration - loads settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Look for .env file in current directory or parent directories
_dotenv_path = None
for parent in Path(__file__).resolve().parents:
    maybe_env = parent / ".env"
    if maybe_env.exists():
        _dotenv_path = maybe_env
        break

if _dotenv_path:
    load_dotenv(_dotenv_path)


def _env(key: str, default: str | None = None, required: bool = True) -> str:
    """Get env var or die trying (if required)"""
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Environment variable '{key}' must be set.")
    return value  # type: ignore


@dataclass(frozen=True, slots=True)
class Config:
    """All the settings in one place"""

    # Bot token from @BotFather
    telegram_token: str = _env("TELEGRAM_BOT_TOKEN")

    # API key from Yandex Cloud console
    # (service account key works best - no folder_id needed)
    yandex_api_key: str = _env("YANDEX_API_KEY")

    # TTS defaults
    default_voice: str = os.getenv("DEFAULT_VOICE", "alena")
    default_role: str | None = os.getenv("DEFAULT_ROLE", "neutral")
    default_format: str = os.getenv("DEFAULT_AUDIO_FORMAT", "oggopus")  # oggopus works great for Telegram
    default_speed: str = os.getenv("DEFAULT_SPEED", "1.0")


# Single global instance
CONFIG = Config()
