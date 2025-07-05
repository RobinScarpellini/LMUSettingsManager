"""
Configuration model for managing game settings with change tracking.

This module provides the main data model for configuration management,
including loading, modification tracking, and validation.
"""

from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import logging

from ..parsers.json_parser import ConfigData, FieldInfo, JsonWithCommentsParser
from ..parsers.ini_parser import IniParser
from .field_state import FieldState


class ConfigurationModel:
    """
    Main model for managing configuration data with change tracking.

    This class provides a unified interface for managing both JSON and INI
    configuration files, tracking changes, and validating modifications.
    """

    def __init__(self):
        """Initialize the configuration model."""
        self.logger = logging.getLogger(__name__)

        # Configuration data
        self.json_config: Optional[ConfigData] = None
        self.ini_config: Optional[ConfigData] = None

        # Field states for change tracking
        self.field_states: Dict[str, FieldState] = {}

        # File paths
        self.json_file_path: Optional[Path] = None
        self.ini_file_path: Optional[Path] = None

        # Change tracking
        self._modified_fields: Set[str] = set()
        self._observers: List[callable] = []

    def load_configuration(self, json_path: Path, ini_path: Path) -> bool:
        """
        Load configuration from JSON and INI files.

        Args:
            json_path: Path to settings.json file
            ini_path: Path to Config_DX11.ini file

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            # Parse JSON configuration
            json_parser = JsonWithCommentsParser()
            self.json_config = json_parser.parse_file(json_path)
            self.json_file_path = json_path

            # Parse INI configuration
            ini_parser = IniParser()
            self.ini_config = ini_parser.parse_file(ini_path)
            self.ini_file_path = ini_path

            # Initialize field states
            self._initialize_field_states()

            self.logger.info(f"Post-parse json_config fields: {len(self.json_config.fields) if self.json_config else 'None'}, categories: {len(self.json_config.categories) if self.json_config else 'None'}")
            self.logger.info(f"Post-parse ini_config fields: {len(self.ini_config.fields) if self.ini_config else 'None'}, categories: {len(self.ini_config.categories) if self.ini_config else 'None'}")
            
            self.logger.info(f"Loaded configuration from {json_path} and {ini_path}")
            self._notify_observers("configuration_loaded")

            return True

        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False

    def _initialize_field_states(self) -> None:
        """Initialize field states for all configuration fields."""
        self.field_states.clear()
        self._modified_fields.clear()

        # Initialize JSON field states
        if self.json_config:
            for field_path, field_info in self.json_config.fields.items():
                self.field_states[field_path] = FieldState(field_info.value)

        # Initialize INI field states
        if self.ini_config:
            for field_path, field_info in self.ini_config.fields.items():
                # Prefix INI fields to avoid conflicts
                ini_field_path = f"ini.{field_path}"
                self.field_states[ini_field_path] = FieldState(field_info.value)

    def get_field_value(self, field_path: str) -> Any:
        """
        Get the current value of a field.

        Args:
            field_path: Path to the field

        Returns:
            Current field value or None if field doesn't exist
        """
        field_state = self.field_states.get(field_path)
        if field_state:
            return field_state.current_value
        return None

    def set_field_value(self, field_path: str, value: Any) -> bool:
        """
        Set the value of a field.

        Args:
            field_path: Path to the field
            value: New value to set

        Returns:
            True if value was changed, False otherwise
        """
        field_state = self.field_states.get(field_path)
        if not field_state:
            self.logger.warning(f"Field not found: {field_path}")
            return False

        # Convert text input to appropriate type based on original value type
        converted_value = self._convert_value_to_type(value, field_state.original_value)

        # Set the value and track changes
        changed = field_state.set_value(converted_value)

        if changed:
            if field_state.is_modified:
                self._modified_fields.add(field_path)
            else:
                self._modified_fields.discard(field_path)

            # Update the underlying configuration data
            self._update_config_data(field_path, converted_value)

            # Notify observers
            self._notify_observers("field_changed", field_path, converted_value)

        return changed

    def _convert_value_to_type(self, value: Any, original_value: Any) -> Any:
        """
        Convert a value to the appropriate type based on the original value type.

        Args:
            value: Input value (typically from text field)
            original_value: Original value to determine target type

        Returns:
            Converted value
        """
        # If original value is boolean, keep it as boolean (handled by checkbox)
        if isinstance(original_value, bool):
            return bool(value)

        # If original value is int, try to convert to int
        elif isinstance(original_value, int):
            try:
                if isinstance(value, str):
                    # Handle empty string
                    if value.strip() == "":
                        return 0
                    return int(
                        float(value)
                    )  # Parse as float first to handle "1.0" -> 1
                return int(value)
            except (ValueError, TypeError):
                self.logger.warning(f"Could not convert '{value}' to integer, using 0")
                return 0

        # If original value is float, try to convert to float
        elif isinstance(original_value, float):
            try:
                if isinstance(value, str):
                    # Handle empty string
                    if value.strip() == "":
                        return 0.0
                    return float(value)
                return float(value)
            except (ValueError, TypeError):
                self.logger.warning(f"Could not convert '{value}' to float, using 0.0")
                return 0.0

        # For everything else (strings, lists, dicts), return as string
        else:
            return str(value) if value is not None else ""

    def _update_config_data(self, field_path: str, value: Any) -> None:
        """
        Update the underlying configuration data structures.

        Args:
            field_path: Path to the field
            value: New value
        """
        if field_path.startswith("ini."):
            # INI field
            actual_path = field_path[4:]  # Remove 'ini.' prefix
            if self.ini_config and actual_path in self.ini_config.fields:
                self.ini_config.fields[actual_path].value = value
        else:
            # JSON field
            if self.json_config and field_path in self.json_config.fields:
                self.json_config.fields[field_path].value = value

    def is_field_modified(self, field_path: str) -> bool:
        """
        Check if a field has been modified.

        Args:
            field_path: Path to the field

        Returns:
            True if field is modified, False otherwise
        """
        field_state = self.field_states.get(field_path)
        return field_state.is_modified if field_state else False

    def get_modified_fields(self) -> List[str]:
        """
        Get list of all modified field paths.

        Returns:
            List of modified field paths
        """
        return list(self._modified_fields)

    def revert_field(self, field_path: str) -> bool:
        """
        Revert a field to its original value.

        Args:
            field_path: Path to the field

        Returns:
            True if field was reverted, False otherwise
        """
        field_state = self.field_states.get(field_path)
        if not field_state:
            return False

        reverted = field_state.revert()
        if reverted:
            self._modified_fields.discard(field_path)
            # Update config data
            self._update_config_data(field_path, field_state.current_value)
            self._notify_observers("field_reverted", field_path)

        return reverted

    def revert_all_changes(self) -> int:
        """
        Revert all modified fields to their original values.

        Returns:
            Number of fields that were reverted
        """
        reverted_count = 0
        modified_fields = list(
            self._modified_fields
        )  # Copy to avoid modification during iteration

        for field_path in modified_fields:
            if self.revert_field(field_path):
                reverted_count += 1

        if reverted_count > 0:
            self._notify_observers("all_changes_reverted", reverted_count)

        return reverted_count

    def apply_changes(self) -> Tuple[bool, Optional[str]]:
        """
        Apply all changes by writing to configuration files.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Write JSON configuration
            if self.json_config and self.json_file_path:
                json_parser = JsonWithCommentsParser()
                if not json_parser.write_preserving_structure(
                    self.json_config, self.json_file_path
                ):
                    return False, "Failed to write JSON configuration"

            # Write INI configuration
            if self.ini_config and self.ini_file_path:
                ini_parser = IniParser()
                if not ini_parser.write_preserving_structure(
                    self.ini_config, self.ini_file_path
                ):
                    return False, "Failed to write INI configuration"

            # Mark all changes as applied
            for field_path in list(self._modified_fields):
                field_state = self.field_states.get(field_path)
                if field_state:
                    field_state.apply_changes()

            self._modified_fields.clear()

            self.logger.info("Successfully applied all configuration changes")
            self._notify_observers("changes_applied")

            return True, None

        except Exception as e:
            error_msg = f"Error applying changes: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_field_info(self, field_path: str) -> Optional[FieldInfo]:
        """
        Get field information including description and type.

        Args:
            field_path: Path to the field

        Returns:
            FieldInfo object or None if field doesn't exist
        """
        if field_path.startswith("ini."):
            actual_path = field_path[4:]
            if self.ini_config and actual_path in self.ini_config.fields:
                return self.ini_config.fields[actual_path]
        else:
            if self.json_config and field_path in self.json_config.fields:
                return self.json_config.fields[field_path]

        return None

    def get_categories(self) -> Dict[str, List[str]]:
        """
        Get all categories and their fields.

        Returns:
            Dictionary mapping category names to field lists
        """
        self.logger.debug(f"get_categories called. json_config valid: {self.json_config is not None}, ini_config valid: {self.ini_config is not None}")
        if self.json_config:
            self.logger.debug(f"json_config categories count: {len(self.json_config.categories) if self.json_config.categories else 'None or Empty'}")
        if self.ini_config:
            self.logger.debug(f"ini_config categories count: {len(self.ini_config.categories) if self.ini_config.categories else 'None or Empty'}")
            
        categories = OrderedDict()
        
        # Add JSON categories
        if self.json_config:
            for category, fields in self.json_config.categories.items():
                categories[f"JSON - {category}"] = fields

        # Add INI categories
        if self.ini_config:
            for category, fields in self.ini_config.categories.items():
                # Prefix INI field paths
                ini_fields = [f"ini.{field}" for field in fields]
                categories[f"DX11 - {category}"] = ini_fields

        return categories

    def search_fields(self, query: str) -> List[str]:
        """
        Search for fields matching the query in field names only.

        Args:
            query: Search query

        Returns:
            List of matching field paths
        """
        query_lower = query.lower()
        matches = []

        # Search JSON fields (only in field names, not descriptions)
        if self.json_config:
            for field_path, field_info in self.json_config.fields.items():
                # Extract the field name (last part after the last dot)
                field_name = field_path.split(".")[-1]
                if query_lower in field_name.lower():
                    matches.append(field_path)

        # Search INI fields (only in field names, not descriptions)
        if self.ini_config:
            for field_path, field_info in self.ini_config.fields.items():
                ini_field_path = f"ini.{field_path}"
                # Extract the field name (last part after the last dot)
                field_name = field_path.split(".")[-1]
                if query_lower in field_name.lower():
                    matches.append(ini_field_path)

        return matches

    def add_observer(self, observer: callable) -> None:
        """
        Add an observer for model changes.

        Args:
            observer: Callable that will be notified of changes
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: callable) -> None:
        """
        Remove an observer.

        Args:
            observer: Observer to remove
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers(self, event: str, *args) -> None:
        """
        Notify all observers of an event.

        Args:
            event: Event name
            *args: Event arguments
        """
        for observer in self._observers:
            try:
                observer(event, *args)
            except Exception as e:
                self.logger.error(f"Error notifying observer: {e}")

    @property
    def has_changes(self) -> bool:
        """Check if there are any pending changes."""
        return len(self._modified_fields) > 0

    @property
    def change_count(self) -> int:
        """Get the number of modified fields."""
        return len(self._modified_fields)

    @property
    def is_valid(self) -> bool:
        """Check if all fields are valid (no validation errors)."""
        return all(field_state.is_valid() for field_state in self.field_states.values())
