"""
Settings manager for persistent application configuration.

Handles saving and loading application settings like game path.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging


class SettingsManager:
    """Manages persistent application settings."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._settings_file = self._get_settings_file()
        self._settings = self._load_settings()

    def _get_settings_file(self) -> Path:
        """
        Get path to settings file in user's local app data directory.

        Returns:
            Path to settings file
        """
        if os.name == "nt":  # Windows
            app_data = Path(os.getenv("LOCALAPPDATA", ""))
        else:  # Linux/Mac
            app_data = Path.home() / ".local" / "share"

        settings_dir = app_data / "LMUConfigEditor"
        settings_dir.mkdir(parents=True, exist_ok=True)

        return settings_dir / "settings.json"

    def _load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file.

        Returns:
            Dictionary of settings
        """
        if not self._settings_file.exists():
            return {}

        try:
            with open(self._settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                self.logger.debug(f"Loaded settings from {self._settings_file}")
                return settings
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return {}

    def _save_settings(self) -> bool:
        """
        Save current settings to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
                self.logger.debug(f"Saved settings to {self._settings_file}")
                return True
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False

    def save_game_path(self, path: Path) -> bool:
        """
        Save game installation path.

        Args:
            path: Path to game installation

        Returns:
            True if saved successfully, False otherwise
        """
        self._settings["game_path"] = str(path)
        return self._save_settings()

    def load_game_path(self) -> Optional[Path]:
        """
        Load saved game installation path.

        Returns:
            Path to game installation or None if not saved
        """
        game_path_str = self._settings.get("game_path")
        if not game_path_str:
            return None

        game_path = Path(game_path_str)

        # Validate that the path still exists
        if not game_path.exists():
            self.logger.warning(f"Saved game path no longer exists: {game_path}")
            # Remove invalid path from settings
            self._settings.pop("game_path", None)
            self._save_settings()
            return None

        return game_path

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value

        Returns:
            True if saved successfully, False otherwise
        """
        self._settings[key] = value
        return self._save_settings()

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings.

        Returns:
            Dictionary of all settings
        """
        return self._settings.copy()

    def clear_settings(self) -> bool:
        """
        Clear all settings.

        Returns:
            True if cleared successfully, False otherwise
        """
        self._settings.clear()
        return self._save_settings()
