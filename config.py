"""Bot configuration - loads settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Look for .env file in current directory or parent directories
_dotenv_path: Path | None = None
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
    return value if value is not None else ""


@dataclass(frozen=True, slots=True)
class Config:
    """All the settings in one place"""

    # Bot token from @BotFather
    telegram_token: str = _env("TELEGRAM_BOT_TOKEN")

    # API key from Yandex Cloud console
    # (service account key works best - no folder_id needed)
    yandex_api_key: str = _env("YANDEX_API_KEY")
    
    # Folder ID (required for v1 API SSML support)
    yandex_folder_id: str | None = os.getenv("YANDEX_FOLDER_ID")

    # TTS defaults
    default_voice: str = os.getenv("DEFAULT_VOICE", "marina")
    default_role: str | None = os.getenv("DEFAULT_ROLE", "friendly")
    default_format: str = os.getenv("DEFAULT_AUDIO_FORMAT", "oggopus")  # oggopus works great for Telegram
    default_speed: str = os.getenv("DEFAULT_SPEED", "0.95")
    
    # TTS Version Settings
    tts_version: str = os.getenv("YANDEX_TTS_VERSION", "3")  # Use v3 by default
    
    # GPT Settings
    gpt_model: str = os.getenv("GPT_MODEL", "yandexgpt-pro:rc")  # Using Release Candidate by default
    enable_auto_format: bool = os.getenv("ENABLE_AUTO_FORMAT", "true").lower() == "true"
    max_pause_ms: int = int(os.getenv("MAX_PAUSE_MS", "5000"))
    
    # Feature flags
    use_tts_markup: bool = os.getenv("USE_TTS_MARKUP", "true").lower() == "true"


# Single global instance
CONFIG = Config()
