"""
Configuration manager for saving, loading, and managing multiple configurations.

Handles the file operations for saved configurations following the LMU naming convention.
"""

import json
import shutil
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import logging

from .models.configuration_model import ConfigurationModel
from .parsers.json_parser import JsonWithCommentsParser
from .parsers.ini_parser import IniParser


class ConfigurationManager:
    """Manages saving, loading, and organizing multiple game configurations."""

    def __init__(self, game_config_dir: Path):
        """
        Initialize the configuration manager.

        Args:
            game_config_dir: Directory containing game configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.game_config_dir = game_config_dir
        
        # AppData directory for storing saved configurations
        self.saved_configs_dir = self._get_saved_configs_dir()

        # File paths for active game files
        self.active_json_file = self.game_config_dir / "settings.json"
        self.active_ini_file = self.game_config_dir / "Config_DX11.ini"

        # Metadata file for descriptions and timestamps (in AppData)
        self.metadata_file = self.saved_configs_dir / "lmu_config_metadata.json"

        # Load existing metadata
        self.metadata = self._load_metadata()

    def _get_saved_configs_dir(self) -> Path:
        """
        Get the directory for storing saved configurations in AppData.
        
        Returns:
            Path to saved configurations directory
        """
        if os.name == "nt":  # Windows
            app_data = Path(os.getenv("LOCALAPPDATA", ""))
        else:  # Linux/Mac
            app_data = Path.home() / ".local" / "share"
        
        configs_dir = app_data / "LMUConfigEditor" / "SavedConfigurations"
        configs_dir.mkdir(parents=True, exist_ok=True)
        
        return configs_dir

    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load configuration metadata from file.

        Returns:
            Metadata dictionary
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load metadata: {e}")

        return {
            "version": "1.0",
            "configurations": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _save_metadata(self) -> bool:
        """
        Save configuration metadata to file.

        Returns:
            True if successful
        """
        try:
            self.metadata["last_updated"] = datetime.now().isoformat()
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            return False

    def get_saved_configurations(self) -> List[str]:
        """
        Get list of saved configuration names.

        Returns:
            List of configuration names
        """
        configurations = []

        # Look for configuration files matching pattern
        for json_file in self.saved_configs_dir.glob("conf_*_settings.json"):
            # Extract name from filename
            name = json_file.stem.replace("conf_", "").replace("_settings", "")

            # Check if corresponding INI file exists
            ini_file = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"
            if ini_file.exists():
                configurations.append(name)

        return sorted(configurations)

    def save_configuration(
        self, name: str, model: ConfigurationModel
    ) -> bool:
        """
        Save current configuration with given name.

        Args:
            name: Configuration name
            model: Configuration model containing current state

        Returns:
            True if successful
        """
        try:
            # Generate filenames
            json_filename = f"conf_{name}_settings.json"
            ini_filename = f"conf_{name}_Config_DX11.ini"

            json_path = self.saved_configs_dir / json_filename
            ini_path = self.saved_configs_dir / ini_filename

            # Create backups if files exist
            self._create_backup_if_exists(json_path)
            self._create_backup_if_exists(ini_path)

            # Write JSON configuration
            if model.json_config:
                json_parser = JsonWithCommentsParser()
                if not json_parser.write_preserving_structure(
                    model.json_config, json_path
                ):
                    raise Exception("Failed to write JSON configuration")

            # Write INI configuration
            if model.ini_config:
                ini_parser = IniParser()
                if not ini_parser.write_preserving_structure(
                    model.ini_config, ini_path
                ):
                    raise Exception("Failed to write INI configuration")

            # Update metadata
            self.metadata["configurations"][name] = {
                "description": "", # Description removed
                "created": datetime.now().isoformat(),
                "json_file": json_filename,
                "ini_file": ini_filename,
            }

            # Save metadata
            if not self._save_metadata():
                self.logger.warning(
                    "Failed to save metadata, but configuration files were saved"
                )

            self.logger.info(f"Successfully saved configuration '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration '{name}': {e}")
            # Clean up partial files
            self._cleanup_partial_save(name)
            return False

    def load_configuration(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Load saved configuration by name.

        Args:
            name: Configuration name to load

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check if configuration exists
            if name not in self.get_saved_configurations():
                return False, f"Configuration '{name}' not found"

            # Get file paths
            json_path = self.saved_configs_dir / f"conf_{name}_settings.json"
            ini_path = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"

            # Verify files exist
            if not json_path.exists():
                return False, f"JSON file not found: {json_path}"
            if not ini_path.exists():
                return False, f"INI file not found: {ini_path}"

            # Create backups of current active files
            self._create_backup_if_exists(self.active_json_file, suffix=".before_load")
            self._create_backup_if_exists(self.active_ini_file, suffix=".before_load")

            # Copy saved files to active locations
            shutil.copy2(json_path, self.active_json_file)
            shutil.copy2(ini_path, self.active_ini_file)

            self.logger.info(f"Successfully loaded configuration '{name}'")
            return True, None

        except Exception as e:
            error_msg = f"Failed to load configuration '{name}': {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete_configuration(self, name: str) -> bool:
        """
        Delete a saved configuration.

        Args:
            name: Configuration name to delete

        Returns:
            True if successful
        """
        try:
            # Get file paths
            json_path = self.saved_configs_dir / f"conf_{name}_settings.json"
            ini_path = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"

            # Delete files
            if json_path.exists():
                json_path.unlink()
            if ini_path.exists():
                ini_path.unlink()

            # Remove from metadata
            if name in self.metadata["configurations"]:
                del self.metadata["configurations"][name]
                self._save_metadata()

            self.logger.info(f"Successfully deleted configuration '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete configuration '{name}': {e}")
            return False

    def get_configuration_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a saved configuration.

        Args:
            name: Configuration name

        Returns:
            Configuration info dictionary or None
        """
        if name in self.metadata["configurations"]:
            info = self.metadata["configurations"][name].copy()

            # Add file size information
            json_path = self.saved_configs_dir / info.get("json_file", "")
            ini_path = self.saved_configs_dir / info.get("ini_file", "")

            if json_path.exists():
                info["json_size"] = json_path.stat().st_size
            if ini_path.exists():
                info["ini_size"] = ini_path.stat().st_size

            return info

        return None

    def _create_backup_if_exists(self, filepath: Path, suffix: str = ".bak") -> None:
        """
        Create backup of file if it exists.

        Args:
            filepath: Path to file to backup
            suffix: Backup suffix
        """
        if filepath.exists():
            backup_path = filepath.with_suffix(filepath.suffix + suffix)
            try:
                shutil.copy2(filepath, backup_path)
                self.logger.debug(f"Created backup: {backup_path}")
            except Exception as e:
                self.logger.warning(f"Failed to create backup for {filepath}: {e}")

    def _cleanup_partial_save(self, name: str) -> None:
        """
        Clean up partially saved configuration files.

        Args:
            name: Configuration name
        """
        try:
            json_path = self.saved_configs_dir / f"conf_{name}_settings.json"
            ini_path = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"

            if json_path.exists():
                json_path.unlink()
            if ini_path.exists():
                ini_path.unlink()

        except Exception as e:
            self.logger.error(f"Failed to cleanup partial save for '{name}': {e}")

    def validate_configuration_pair(self, name: str) -> bool:
        """
        Validate that both JSON and INI files exist for a configuration.

        Args:
            name: Configuration name

        Returns:
            True if both files exist
        """
        json_path = self.saved_configs_dir / f"conf_{name}_settings.json"
        ini_path = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"

        return json_path.exists() and ini_path.exists()

    def get_configuration_files(self, name: str) -> Tuple[Path, Path]:
        """
        Get paths to configuration files.

        Args:
            name: Configuration name

        Returns:
            Tuple of (json_path, ini_path)
        """
        json_path = self.saved_configs_dir / f"conf_{name}_settings.json"
        ini_path = self.saved_configs_dir / f"conf_{name}_Config_DX11.ini"

        return json_path, ini_path

    def get_saved_configs_directory(self) -> Path:
        """
        Get the directory where saved configurations are stored.
        
        Returns:
            Path to saved configurations directory
        """
        return self.saved_configs_dir
