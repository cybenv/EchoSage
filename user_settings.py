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
    
    def _get_complete_defaults(self) -> Dict[str, Any]:
        """Get complete default settings for all configurable options"""
        return {
            "voice": CONFIG.default_voice,
            "role": CONFIG.default_role,
            "speed": CONFIG.default_speed,
            "auto_format": CONFIG.enable_auto_format,
            "use_markup": CONFIG.use_tts_markup,
        }
    
    def load(self) -> Dict[str, Any]:
        """Get user settings or defaults if nothing saved yet.
        
        Always returns a complete settings dictionary with all expected keys,
        using saved values where available and global defaults for missing keys.
        """
        # Start with complete defaults
        defaults = self._get_complete_defaults()
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                    logger.info(f"Loaded settings for user {self.user_id}: {saved_settings}")
                    
                    # Merge saved settings with defaults - saved settings override defaults
                    # but defaults ensure all keys are present (e.g., for older saved files)
                    merged_settings = {**defaults, **saved_settings}
                    return merged_settings
        except Exception as e:
            logger.error(f"Failed to load settings for user {self.user_id}: {e}")
        
        # First time user or corrupted file - return complete defaults
        logger.info(f"Using default settings for user {self.user_id}: {defaults}")
        return defaults
    
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
        """Reset all settings to their global default values"""
        default_settings = self._get_complete_defaults()
        return self.save(default_settings)
