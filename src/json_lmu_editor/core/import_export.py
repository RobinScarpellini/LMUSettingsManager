"""
Configuration import/export functionality.

Provides functionality to package and unpackage configurations for sharing.
"""

import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import logging

from .configuration_manager import ConfigurationManager


class ValidationResult:
    """Result of import file validation."""

    def __init__(
        self,
        is_valid: bool,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.metadata = metadata or {}


class ConfigurationPorter:
    """Handles importing and exporting configurations."""

    def __init__(self):
        """Initialize the configuration porter."""
        self.logger = logging.getLogger(__name__)

    def export_configuration(
        self,
        config_manager: ConfigurationManager,
        config_name: str,
        export_path: Path,
        include_description: bool = True,
    ) -> bool:
        """
        Export a configuration to a .lmuconfig file.

        Args:
            config_manager: Configuration manager instance
            config_name: Name of configuration to export
            export_path: Path where to save the export file
            include_description: Whether to include description

        Returns:
            True if export was successful
        """
        try:
            # Get configuration files
            json_path, ini_path = config_manager.get_configuration_files(config_name)

            if not json_path.exists() or not ini_path.exists():
                self.logger.error(f"Configuration files not found for '{config_name}'")
                return False

            # Get configuration info
            config_info = config_manager.get_configuration_info(config_name)

            # Create metadata
            metadata = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "configuration_name": config_name,
                "description": config_info.get("description", "")
                if config_info
                else "",
                "original_created": config_info.get("created", "")
                if config_info
                else "",
                "exporter": "LMU Configuration Editor",
                "format_version": "1.0",
            }

            # Create ZIP archive
            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add JSON file
                zipf.write(json_path, "settings.json")

                # Add INI file
                zipf.write(ini_path, "config_dx11.ini")

                # Add metadata
                metadata_json = json.dumps(metadata, indent=2)
                zipf.writestr("metadata.json", metadata_json)

                # Add description file if requested
                if (
                    include_description
                    and config_info
                    and config_info.get("description")
                ):
                    zipf.writestr("description.txt", config_info["description"])

            self.logger.info(
                f"Successfully exported configuration '{config_name}' to {export_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to export configuration '{config_name}': {e}")
            return False

    def import_configuration(
        self,
        import_path: Path,
        config_manager: ConfigurationManager,
        target_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Import a configuration from a .lmuconfig file.

        Args:
            import_path: Path to .lmuconfig file
            config_manager: Configuration manager instance
            target_name: Optional target name (uses original if None)

        Returns:
            Tuple of (success, error_message_or_imported_name)
        """
        try:
            # Validate import file
            validation = self.validate_import_file(import_path)
            if not validation.is_valid:
                return False, validation.error_message

            # Determine target name
            if not target_name:
                target_name = validation.metadata.get(
                    "configuration_name", "imported_config"
                )

            # Check for name conflicts
            existing_configs = config_manager.get_saved_configurations()
            original_name = target_name
            counter = 1

            while target_name in existing_configs:
                target_name = f"{original_name}_{counter}"
                counter += 1

            # Extract to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract ZIP file
                with zipfile.ZipFile(import_path, "r") as zipf:
                    zipf.extractall(temp_path)

                # Copy files to configuration directory
                json_source = temp_path / "settings.json"
                ini_source = temp_path / "config_dx11.ini"

                if not json_source.exists() or not ini_source.exists():
                    return False, "Import file is missing required configuration files"

                # Generate target file names
                json_target = (
                    config_manager.config_dir / f"conf_{target_name}_settings.json"
                )
                ini_target = (
                    config_manager.config_dir / f"conf_{target_name}_Config_DX11.ini"
                )

                # Copy files
                shutil.copy2(json_source, json_target)
                shutil.copy2(ini_source, ini_target)

                # Update metadata
                description = validation.metadata.get("description", "")
                if target_name in config_manager.metadata["configurations"]:
                    # Update existing entry
                    config_manager.metadata["configurations"][target_name].update(
                        {
                            "description": description,
                            "imported_at": datetime.now().isoformat(),
                            "imported_from": str(import_path),
                        }
                    )
                else:
                    # Create new entry
                    config_manager.metadata["configurations"][target_name] = {
                        "description": description,
                        "created": datetime.now().isoformat(),
                        "imported_at": datetime.now().isoformat(),
                        "imported_from": str(import_path),
                        "json_file": f"conf_{target_name}_settings.json",
                        "ini_file": f"conf_{target_name}_Config_DX11.ini",
                    }

                # Save metadata
                config_manager._save_metadata()

            self.logger.info(f"Successfully imported configuration as '{target_name}'")
            return True, target_name

        except Exception as e:
            error_msg = f"Failed to import configuration: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def validate_import_file(self, filepath: Path) -> ValidationResult:
        """
        Validate an import file.

        Args:
            filepath: Path to import file

        Returns:
            ValidationResult with validation status
        """
        try:
            if not filepath.exists():
                return ValidationResult(False, "File does not exist")

            if filepath.suffix.lower() != ".lmuconfig":
                return ValidationResult(False, "File must have .lmuconfig extension")

            # Check if it's a valid ZIP file
            if not zipfile.is_zipfile(filepath):
                return ValidationResult(False, "File is not a valid .lmuconfig archive")

            # Check archive contents
            with zipfile.ZipFile(filepath, "r") as zipf:
                file_list = zipf.namelist()

                # Check for required files
                required_files = ["settings.json", "config_dx11.ini", "metadata.json"]
                missing_files = [f for f in required_files if f not in file_list]

                if missing_files:
                    return ValidationResult(
                        False,
                        f"Archive is missing required files: {', '.join(missing_files)}",
                    )

                # Validate metadata
                try:
                    metadata_content = zipf.read("metadata.json").decode("utf-8")
                    metadata = json.loads(metadata_content)

                    # Check metadata version
                    if metadata.get("version") != "1.0":
                        return ValidationResult(
                            False,
                            f"Unsupported metadata version: {metadata.get('version')}",
                        )

                    return ValidationResult(True, "", metadata)

                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    return ValidationResult(False, f"Invalid metadata file: {e}")

        except Exception as e:
            return ValidationResult(False, f"Error validating file: {e}")

    def handle_name_conflict(self, suggested_name: str, existing_names: list) -> str:
        """
        Handle naming conflicts by suggesting alternative names.

        Args:
            suggested_name: Originally suggested name
            existing_names: List of existing configuration names

        Returns:
            Available name
        """
        if suggested_name not in existing_names:
            return suggested_name

        # Try numbered variants
        counter = 1
        while f"{suggested_name}_{counter}" in existing_names:
            counter += 1

        return f"{suggested_name}_{counter}"
