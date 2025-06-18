"""
JSON parser for LMU settings files with comment support.

Handles parsing of JSON files with embedded comments and field descriptions.
"""

import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging


class FieldType(Enum):
    """Field data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class FieldInfo:
    """Information about a configuration field."""

    def __init__(
        self,
        path: str,
        value: Any,
        description: Optional[str] = None,
        field_type: FieldType = FieldType.STRING,
        category: str = "",
    ):
        self.path = path
        self.value = value
        self.description = description
        self.type = field_type
        self.category = category
        self.original_value = value  # Keep track of original value


class ConfigData:
    """Container for parsed configuration data."""

    def __init__(self):
        self.fields: OrderedDict[str, FieldInfo] = OrderedDict()
        self.categories: OrderedDict[str, List[str]] = OrderedDict()
        self.descriptions: Dict[str, str] = {}
        self.types: Dict[str, FieldType] = {}
        self.raw_lines: List[str] = []  # Store original lines for write-back


class JsonWithCommentsParser:
    """Parser for JSON files with embedded comments and field descriptions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, filepath: Path) -> ConfigData:
        """
        Parse a JSON file with comments.

        Args:
            filepath: Path to JSON file

        Returns:
            ConfigData object with parsed information

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is malformed
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            config_data = ConfigData()
            config_data.raw_lines = lines

            # Extract descriptions from comments
            descriptions = self.extract_descriptions(lines)
            config_data.descriptions = descriptions

            # Clean JSON for parsing
            clean_json = self._remove_comments(lines)

            # Debug: Save cleaned JSON for inspection if parsing fails
            try:
                # Parse JSON with object order preservation
                json_data = json.loads(clean_json, object_pairs_hook=OrderedDict)
            except json.JSONDecodeError:
                # Save cleaned JSON for debugging
                debug_file = filepath.parent / f"debug_cleaned_{filepath.name}"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(clean_json)
                self.logger.error(
                    f"JSON parsing failed, cleaned JSON saved to {debug_file}"
                )
                raise

            # Build field hierarchy
            config_data.fields = self.build_field_hierarchy(json_data, descriptions)
            config_data.categories = self._build_categories(config_data.fields)

            self.logger.info(f"Parsed {len(config_data.fields)} fields from {filepath}")
            return config_data

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error in {filepath}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing {filepath}: {e}")
            raise

    def extract_descriptions(self, lines: List[str]) -> Dict[str, str]:
        """
        Extract field descriptions from comment lines.

        Args:
            lines: List of file lines

        Returns:
            Dictionary mapping field names to descriptions
        """
        descriptions = {}

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for comment patterns with descriptions
            # Format: "Field Name": value,  // Description text #: "This is what the setting does"
            # Also support: "Field Name#": "Description text"

            if "//" in line and "#" in line:
                # Extract field name from the line
                field_match = re.search(r'"([^"]+)":', line)
                if field_match:
                    field_name = field_match.group(1)

                    # Extract description after #:
                    # This regex needs to be robust for escaped quotes as well.
                    desc_match = re.search(
                        r'#[:\s]*["\']?(?P<desc>(?:\\.|[^"\'])*)["\']?', line
                    )
                    if desc_match:
                        description_raw = desc_match.group("desc").strip()
                        # Unescape common sequences
                        description = (
                            description_raw.replace('\\"', '"')
                            .replace("\\'", "'")
                            .replace("\\\\", "\\")
                        )
                        descriptions[field_name] = description
                        self.logger.debug(
                            f"Found inline comment description for '{field_name}': {description} (raw: {description_raw})"
                        )

            # Check for dedicated description lines (field names ending with #)
            # Format: "Field Name#": "Description text with \"escaped quotes\""
            if (
                '#":' in line and "//" not in line
            ):  # Ensure it's not a comment line itself
                # Regex to capture field name and the full description, handling escaped quotes
                field_match = re.search(
                    r'"([^"]+)#":\s*"(?P<desc>(?:\\.|[^"\\])*)"', line
                )
                if field_match:
                    field_name = field_match.group(1)
                    description_raw = field_match.group("desc")  # Use named group
                    # Unescape common sequences like \" -> "
                    description = (
                        description_raw.replace('\\"', '"')
                        .replace("\\'", "'")
                        .replace("\\\\", "\\")
                    )
                    descriptions[field_name] = description
                    self.logger.debug(
                        f"Found standalone description for '{field_name}': {description} (raw: {description_raw})"
                    )

        return descriptions

    def _remove_comments(self, lines: List[str]) -> str:
        """
        Remove comments from JSON lines to create valid JSON.

        Args:
            lines: List of file lines

        Returns:
            Clean JSON string
        """
        clean_lines = []

        for i, line in enumerate(lines):
            # Remove // comments but preserve the line structure
            if "//" in line:
                # Find the comment start, but make sure it's not inside a string
                in_string = False
                escape_next = False
                comment_pos = -1

                for j, char in enumerate(line):
                    if escape_next:
                        escape_next = False
                        continue

                    if char == "\\":
                        escape_next = True
                        continue

                    if char == '"':
                        in_string = not in_string
                        continue

                    if (
                        not in_string
                        and char == "/"
                        and j + 1 < len(line)
                        and line[j + 1] == "/"
                    ):
                        comment_pos = j
                        break

                if comment_pos >= 0:
                    line = line[:comment_pos].rstrip()

            # Skip lines that are description-only (ending with #)
            stripped_line = line.strip()
            # Regex to match lines like: "FieldName#": "Description with \"escaped quotes\" might be here",
            # It allows for escaped quotes within the description string.
            if re.match(r'^\s*"[^"]+#":\s*"(?:\\.|[^"\\])*"[,]?\s*$', stripped_line):
                self.logger.debug(f"Skipping description-only line: {stripped_line}")
                continue

            clean_lines.append(line)

        # Post-process to fix trailing commas before closing braces/brackets
        result = "".join(clean_lines)
        # Remove trailing commas before } or ]
        result = re.sub(r",(\s*[}\]])", r"\1", result)

        return result

    def build_field_hierarchy(
        self,
        data: Union[Dict, OrderedDict],
        descriptions: Dict[str, str],
        parent_path: str = "",
    ) -> OrderedDict[str, FieldInfo]:
        """
        Build a flat hierarchy of fields from nested JSON data.

        Args:
            data: JSON data (dict or OrderedDict)
            descriptions: Field descriptions
            parent_path: Current path prefix

        Returns:
            OrderedDict of field paths to FieldInfo objects
        """
        fields = OrderedDict()

        for key, value in data.items():
            current_path = f"{parent_path}.{key}" if parent_path else key
            field_type = self.preserve_types(value)
            # Try to find description by field name (key) first, then by full path
            # This handles both inline comments and standalone description fields
            description = descriptions.get(key, "") or descriptions.get(
                current_path, ""
            )

            if isinstance(value, dict):
                # This is a category/section
                category = key
                # Recursively process nested fields
                nested_fields = self.build_field_hierarchy(
                    value, descriptions, current_path
                )
                for nested_path, nested_field in nested_fields.items():
                    nested_field.category = category
                    fields[nested_path] = nested_field
            else:
                # This is a regular field
                field_info = FieldInfo(
                    path=current_path,
                    value=value,
                    description=description,
                    field_type=field_type,
                    category=parent_path if parent_path else "General",
                )
                fields[current_path] = field_info

        return fields

    def preserve_types(self, value: Any) -> FieldType:
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
        elif isinstance(value, list):
            return FieldType.ARRAY
        elif isinstance(value, dict):
            return FieldType.OBJECT
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
        Write configuration data back to file preserving original structure.

        Args:
            config_data: Configuration data to write
            output_path: Path to write to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Reconstruct the file line by line, preserving structure
            new_lines = []

            for line in config_data.raw_lines:
                # Check if this line contains a field we need to update
                field_match = re.search(r'"([^"]+)":\s*([^,}]+)', line)
                if field_match:
                    field_name = field_match.group(1)

                    # Find the field in our data
                    field_info = None
                    for field_path, info in config_data.fields.items():
                        if field_path.endswith(field_name) or field_path == field_name:
                            field_info = info
                            break

                    if field_info and field_info.value != field_info.original_value:
                        # Update the value while preserving the line structure
                        old_value = field_match.group(2)
                        new_value = self._format_value_for_json(
                            field_info.value, field_info.type
                        )
                        new_line = line.replace(old_value, new_value)
                        new_lines.append(new_line)
                        continue

                # Keep the original line
                new_lines.append(line)

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            self.logger.info(f"Successfully wrote configuration to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error writing configuration: {e}")
            return False

    def _format_value_for_json(self, value: Any, field_type: FieldType) -> str:
        """
        Format a value for JSON output.

        Args:
            value: Value to format
            field_type: Type of the field

        Returns:
            JSON-formatted string
        """
        if field_type == FieldType.STRING:
            return f'"{value}"'
        elif field_type == FieldType.BOOLEAN:
            return "true" if value else "false"
        elif field_type in (FieldType.INTEGER, FieldType.FLOAT):
            return str(value)
        elif field_type in (FieldType.ARRAY, FieldType.OBJECT):
            return json.dumps(value)
        else:
            return f'"{value}"'
