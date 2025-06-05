"""Persistent storage for user preferences."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from config import CONFIG

logger = logging.getLogger(__name__)

# Using /tmp because it works everywhere (including serverless)
# In production you'd probably want a database instead
SETTINGS_DIR = Path("/tmp/tts_bot_settings")


class UserSettings:
    """Handles saving/loading user preferences to JSON files"""
    
    def __init__(self, user_id: int):
        """Set up storage for a specific user"""
        self.user_id = user_id
        self.settings_file = SETTINGS_DIR / f"user_{user_id}.json"
        self._ensure_settings_dir()
    
    def _ensure_settings_dir(self) -> None:
        """Make sure our storage directory exists"""
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create settings directory: {e}")
    
    def load(self) -> Dict[str, Any]:
        """Get user settings or defaults if nothing saved yet"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    logger.info(f"Loaded settings for user {self.user_id}: {settings}")
                    return settings
        except Exception as e:
            logger.error(f"Failed to load settings for user {self.user_id}: {e}")
        
        # First time user or corrupted file - use defaults
        return {
            "voice": CONFIG.default_voice,
            "role": CONFIG.default_role,
            "speed": CONFIG.default_speed,
        }
    
    def save(self, settings: Dict[str, Any]) -> bool:
        """Write settings to disk"""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved settings for user {self.user_id}: {settings}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings for user {self.user_id}: {e}")
            return False
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a single setting value"""
        settings = self.load()
        return settings.get(key, default)
    
    def update(self, key: str, value: str) -> bool:
        """Change one setting"""
        settings = self.load()
        settings[key] = value
        return self.save(settings)
    
    def update_multiple(self, updates: Dict[str, str]) -> bool:
        """Change multiple settings at once (more efficient)"""
        settings = self.load()
        settings.update(updates)
        return self.save(settings)
    
    def reset_to_defaults(self) -> bool:
        """Start with default settings"""
        default_settings = {
            "voice": CONFIG.default_voice,
            "role": CONFIG.default_role,
            "speed": CONFIG.default_speed,
        }
        return self.save(default_settings)
