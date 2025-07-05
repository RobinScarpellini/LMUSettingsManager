"""
Configuration comparison engine.

Provides functionality to compare two configurations and identify differences.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .parsers.json_parser import FieldType


class DifferenceType(Enum):
    """Types of differences between configurations."""

    VALUE_CHANGED = "value_changed"
    TYPE_CHANGED = "type_changed"
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"


@dataclass
class Difference:
    """Represents a difference between two configuration values."""

    field_path: str
    field_name: str
    category: str
    difference_type: DifferenceType
    value1: Any
    value2: Any
    field_type: FieldType
    description: str = ""


class ComparisonEngine:
    """Engine for comparing configurations and identifying differences."""

    def __init__(self):
        """Initialize the comparison engine."""
        self.logger = logging.getLogger(__name__)

    def compare_configurations(
        self, config1_data: Dict[str, Any], config2_data: Dict[str, Any]
    ) -> List[Difference]:
        """
        Compare two configuration data sets.

        Args:
            config1_data: First configuration (field_path -> field_info)
            config2_data: Second configuration (field_path -> field_info)

        Returns:
            List of differences found
        """
        differences = []

        # Get all field paths from both configurations
        all_paths = set(config1_data.keys()) | set(config2_data.keys())

        for field_path in all_paths:
            field1 = config1_data.get(field_path)
            field2 = config2_data.get(field_path)

            # Field only in config1
            if field1 and not field2:
                differences.append(
                    Difference(
                        field_path=field_path,
                        field_name=self._get_field_name(field_path),
                        category=field1.category,
                        difference_type=DifferenceType.FIELD_REMOVED,
                        value1=field1.value,
                        value2=None,
                        field_type=field1.type,
                        description=field1.description or "",
                    )
                )

            # Field only in config2
            elif field2 and not field1:
                differences.append(
                    Difference(
                        field_path=field_path,
                        field_name=self._get_field_name(field_path),
                        category=field2.category,
                        difference_type=DifferenceType.FIELD_ADDED,
                        value1=None,
                        value2=field2.value,
                        field_type=field2.type,
                        description=field2.description or "",
                    )
                )

            # Field in both configurations
            elif field1 and field2:
                # Check if types differ
                if field1.type != field2.type:
                    differences.append(
                        Difference(
                            field_path=field_path,
                            field_name=self._get_field_name(field_path),
                            category=field1.category,
                            difference_type=DifferenceType.TYPE_CHANGED,
                            value1=field1.value,
                            value2=field2.value,
                            field_type=field1.type,
                            description=field1.description or "",
                        )
                    )

                # Check if values differ
                elif not self._values_equal(field1.value, field2.value):
                    differences.append(
                        Difference(
                            field_path=field_path,
                            field_name=self._get_field_name(field_path),
                            category=field1.category,
                            difference_type=DifferenceType.VALUE_CHANGED,
                            value1=field1.value,
                            value2=field2.value,
                            field_type=field1.type,
                            description=field1.description or "",
                        )
                    )

        # Sort differences by category and field name
        differences.sort(key=lambda d: (d.category, d.field_name))

        self.logger.info(f"Found {len(differences)} differences between configurations")
        return differences

    def _get_field_name(self, field_path: str) -> str:
        """
        Extract display name from field path.

        Args:
            field_path: Full field path

        Returns:
            Display name
        """
        return field_path.split(".")[-1]

    def _values_equal(self, value1: Any, value2: Any) -> bool:
        """
        Compare two values for equality, handling different types appropriately.

        Args:
            value1: First value
            value2: Second value

        Returns:
            True if values are considered equal
        """
        # Handle None values
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False

        # Handle numeric comparisons with tolerance for floats
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            if isinstance(value1, float) or isinstance(value2, float):
                return abs(float(value1) - float(value2)) < 1e-10
            else:
                return value1 == value2

        # Handle string comparisons
        if isinstance(value1, str) and isinstance(value2, str):
            return value1.strip() == value2.strip()

        # Handle boolean comparisons
        if isinstance(value1, bool) and isinstance(value2, bool):
            return value1 == value2

        # Handle list/tuple comparisons
        if isinstance(value1, (list, tuple)) and isinstance(value2, (list, tuple)):
            if len(value1) != len(value2):
                return False
            return all(self._values_equal(v1, v2) for v1, v2 in zip(value1, value2))

        # Default comparison
        return value1 == value2

    def categorize_differences(
        self, differences: List[Difference]
    ) -> Dict[str, List[Difference]]:
        """
        Categorize differences by category.

        Args:
            differences: List of differences

        Returns:
            Dictionary mapping categories to differences
        """
        categorized = {}

        for diff in differences:
            category = diff.category
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(diff)

        return categorized

    def format_value_for_display(self, value: Any, field_type: FieldType) -> str:
        """
        Format a value for display in comparison view.

        Args:
            value: Value to format
            field_type: Type of the field

        Returns:
            Formatted string representation
        """
        if value is None:
            return "(not set)"

        if field_type == FieldType.BOOLEAN:
            return "Yes" if value else "No"
        elif field_type == FieldType.ARRAY:
            if isinstance(value, (list, tuple)):
                return f"[{len(value)} items]"
            else:
                return str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        elif field_type == FieldType.FLOAT:
            if isinstance(value, float):
                return (
                    f"{value:.6g}"  # Use general format to avoid unnecessary decimals
                )
            else:
                return str(value)
        else:
            str_value = str(value)
            return str_value[:50] + "..." if len(str_value) > 50 else str_value

    def get_difference_summary(self, differences: List[Difference]) -> Dict[str, int]:
        """
        Get summary statistics of differences.

        Args:
            differences: List of differences

        Returns:
            Dictionary with difference counts by type
        """
        summary = {
            "total": len(differences),
            "value_changed": 0,
            "type_changed": 0,
            "field_added": 0,
            "field_removed": 0,
        }

        for diff in differences:
            if diff.difference_type == DifferenceType.VALUE_CHANGED:
                summary["value_changed"] += 1
            elif diff.difference_type == DifferenceType.TYPE_CHANGED:
                summary["type_changed"] += 1
            elif diff.difference_type == DifferenceType.FIELD_ADDED:
                summary["field_added"] += 1
            elif diff.difference_type == DifferenceType.FIELD_REMOVED:
                summary["field_removed"] += 1

        return summary
