"""
INI parser for LMU configuration files with comment support.

Handles parsing of INI files while preserving comments and structure.
"""

import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, List
import logging

from .json_parser import FieldInfo, FieldType, ConfigData


class IniParser:
    """Parser for INI configuration files with comment preservation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, filepath: Path) -> ConfigData:
        """
        Parse an INI file while preserving structure and comments.

        Args:
            filepath: Path to INI file

        Returns:
            ConfigData object with parsed information

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            config_data = ConfigData()
            config_data.raw_lines = lines

            # Parse INI content
            parsed_data = self.parse_with_comments(lines)

            # Build field hierarchy
            config_data.fields = self._build_field_info(parsed_data)
            config_data.categories = self._build_categories(config_data.fields)

            self.logger.info(f"Parsed {len(config_data.fields)} fields from {filepath}")
            return config_data

        except Exception as e:
            self.logger.error(f"Error parsing {filepath}: {e}")
            raise

    def parse_with_comments(self, lines: List[str]) -> OrderedDict:
        """
        Parse INI content while extracting comments and preserving structure.

        Args:
            lines: List of file lines

        Returns:
            OrderedDict with parsed sections and key-value pairs
        """
        data = OrderedDict()
        current_section = None
        line_number = 0

        for line_num, line in enumerate(lines):
            line_number = line_num
            original_line = line
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip pure comment lines (but store them for context)
            if line.startswith("//"):
                continue

            # Check for section headers [SECTION]
            section_match = re.match(r"^\[([^\]]+)\]", line)
            if section_match:
                current_section = section_match.group(1)
                if current_section not in data:
                    data[current_section] = OrderedDict()
                continue

            # Parse key-value pairs
            if "=" in line and current_section is not None:
                # Handle inline comments
                comment = ""
                if "//" in line:
                    line_part, comment_part = line.split("//", 1)
                    line = line_part.strip()
                    comment = comment_part.strip()

                # Extract key and value
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Parse value type
                parsed_value = self._parse_ini_value(value)

                # Store with metadata
                data[current_section][key] = {
                    "value": parsed_value,
                    "comment": comment,
                    "line_number": line_number,
                    "original_line": original_line,
                }

        return data

    def _parse_ini_value(self, value_str: str) -> Any:
        """
        Parse INI value string to appropriate Python type.

        Args:
            value_str: String value from INI file

        Returns:
            Parsed value with appropriate type
        """
        value_str = value_str.strip()

        # Handle boolean values
        if value_str.lower() in ("true", "on", "yes", "1"):
            return True
        elif value_str.lower() in ("false", "off", "no", "0"):
            return False

        # Handle numeric values
        try:
            # Try integer first
            if "." not in value_str:
                return int(value_str)
            else:
                return float(value_str)
        except ValueError:
            pass

        # Handle tuples/arrays (values in parentheses)
        if value_str.startswith("(") and value_str.endswith(")"):
            # Parse tuple format like (0.609, 0.343, 0.457, 60.000, 0.004)
            inner = value_str[1:-1]
            try:
                parts = [part.strip() for part in inner.split(",")]
                parsed_parts = []
                for part in parts:
                    try:
                        parsed_parts.append(float(part))
                    except ValueError:
                        parsed_parts.append(part)
                return tuple(parsed_parts)
            except Exception:
                pass

        # Return as string if no other type matches
        return value_str

    def _build_field_info(
        self, parsed_data: OrderedDict
    ) -> OrderedDict[str, FieldInfo]:
        """
        Build FieldInfo objects from parsed INI data.

        Args:
            parsed_data: Parsed INI data

        Returns:
            OrderedDict of field paths to FieldInfo objects
        """
        fields = OrderedDict()

        for section_name, section_data in parsed_data.items():
            for key, value_info in section_data.items():
                field_path = f"{section_name}.{key}"
                value = value_info["value"]
                comment = value_info.get("comment", "")

                field_type = self._determine_field_type(value)

                field_info = FieldInfo(
                    path=field_path,
                    value=value,
                    description=comment,
                    field_type=field_type,
                    category=section_name,
                )

                # Store additional metadata
                field_info.line_number = value_info.get("line_number", 0)
                field_info.original_line = value_info.get("original_line", "")

                fields[field_path] = field_info

        return fields

    def _determine_field_type(self, value: Any) -> FieldType:
        """
        Determine the field type from the value.

        Args:
            value: Field value

        Returns:
            FieldType enum value
        """
        if isinstance(value, bool):
            return FieldType.BOOLEAN
        elif isinstance(value, int):
            return FieldType.INTEGER
        elif isinstance(value, float):
            return FieldType.FLOAT
        elif isinstance(value, (list, tuple)):
            return FieldType.ARRAY
        else:
            return FieldType.STRING

    def _build_categories(
        self, fields: OrderedDict[str, FieldInfo]
    ) -> OrderedDict[str, List[str]]:
        """
        Build category structure from fields.

        Args:
            fields: Dictionary of fields

        Returns:
            OrderedDict mapping categories to field lists
        """
        categories = OrderedDict()

        for field_path, field_info in fields.items():
            category = field_info.category
            if category not in categories:
                categories[category] = []
            categories[category].append(field_path)

        return categories

    def write_preserving_structure(
        self, config_data: ConfigData, output_path: Path
    ) -> bool:
        """
        Write INI data back to file preserving original structure.

        Args:
            config_data: Configuration data to write
            output_path: Path to write to

        Returns:
            True if successful, False otherwise
        """
        try:
            new_lines = []

            for line in config_data.raw_lines:
                original_line = line
                line_stripped = line.strip()

                # Skip empty lines and comments - keep as is
                if (
                    not line_stripped
                    or line_stripped.startswith("//")
                    or line_stripped.startswith("[")
                ):
                    new_lines.append(original_line)
                    continue

                # Check if this is a key-value line
                if "=" in line_stripped:
                    # Extract key from line
                    key_match = re.match(r"^([^=]+)=", line_stripped)
                    if key_match:
                        key = key_match.group(1).strip()

                        # Find the field in our data
                        field_info = None
                        for field_path, info in config_data.fields.items():
                            if field_path.endswith("." + key):
                                field_info = info
                                break

                        if field_info and hasattr(field_info, "line_number"):
                            # Check if value was modified
                            if field_info.value != field_info.original_value:
                                # Reconstruct the line with new value
                                new_value = self._format_value_for_ini(
                                    field_info.value, field_info.type
                                )

                                # Preserve comment if present
                                if "//" in line:
                                    line_part, comment_part = line.split("//", 1)
                                    new_line = f"{key}={new_value} //{comment_part}"
                                else:
                                    new_line = f"{key}={new_value}\n"

                                new_lines.append(new_line)
                                continue

                # Keep original line if no changes
                new_lines.append(original_line)

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            self.logger.info(f"Successfully wrote INI configuration to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error writing INI configuration: {e}")
            return False

    def _format_value_for_ini(self, value: Any, field_type: FieldType) -> str:
        """
        Format a value for INI output.

        Args:
            value: Value to format
            field_type: Type of the field

        Returns:
            INI-formatted string
        """
        if field_type == FieldType.BOOLEAN:
            return "1" if value else "0"
        elif field_type == FieldType.ARRAY and isinstance(value, tuple):
            # Format tuple as (val1, val2, val3)
            formatted_values = []
            for v in value:
                if isinstance(v, float):
                    formatted_values.append(f"{v:.3f}")
                else:
                    formatted_values.append(str(v))
            return f"({', '.join(formatted_values)})"
        else:
            return str(value)
