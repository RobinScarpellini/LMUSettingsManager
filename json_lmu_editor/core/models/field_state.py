"""
Field state management for tracking configuration changes.
"""

from datetime import datetime
from typing import Any, List, Optional
from enum import Enum


class ValidationState(Enum):
    """Field validation states."""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"


class FieldState:
    """Tracks the state of a configuration field including modifications and validation."""

    def __init__(self, original_value: Any):
        """
        Initialize field state.

        Args:
            original_value: The original value of the field
        """
        self.original_value = original_value
        self.current_value = original_value
        self.is_modified = False
        self.modification_time: Optional[datetime] = None
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.validation_state = ValidationState.VALID

    def set_value(self, new_value: Any) -> bool:
        """
        Set a new value for the field.

        Args:
            new_value: The new value to set

        Returns:
            True if the value was changed, False if it's the same
        """
        if new_value == self.current_value:
            return False

        self.current_value = new_value
        self.is_modified = new_value != self.original_value

        if self.is_modified:
            self.modification_time = datetime.now()
        else:
            self.modification_time = None

        # Clear validation state when value changes
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.validation_state = ValidationState.VALID

        return True

    def revert(self) -> bool:
        """
        Revert the field to its original value.

        Returns:
            True if the field was reverted, False if it was already at original value
        """
        if not self.is_modified:
            return False

        self.current_value = self.original_value
        self.is_modified = False
        self.modification_time = None
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.validation_state = ValidationState.VALID

        return True

    def apply_changes(self) -> None:
        """Apply changes by making current value the new original value."""
        self.original_value = self.current_value
        self.is_modified = False
        self.modification_time = None

    def add_validation_error(self, error: str) -> None:
        """
        Add a validation error.

        Args:
            error: Error message
        """
        if error not in self.validation_errors:
            self.validation_errors.append(error)
            self.validation_state = ValidationState.ERROR

    def add_validation_warning(self, warning: str) -> None:
        """
        Add a validation warning.

        Args:
            warning: Warning message
        """
        if warning not in self.validation_warnings:
            self.validation_warnings.append(warning)
            if self.validation_state == ValidationState.VALID:
                self.validation_state = ValidationState.WARNING

    def clear_validation(self) -> None:
        """Clear all validation errors and warnings."""
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.validation_state = ValidationState.VALID

    def has_errors(self) -> bool:
        """Check if field has validation errors."""
        return len(self.validation_errors) > 0

    def has_warnings(self) -> bool:
        """Check if field has validation warnings."""
        return len(self.validation_warnings) > 0

    def is_valid(self) -> bool:
        """Check if field is valid (no errors)."""
        return not self.has_errors()

    def get_all_validation_messages(self) -> List[str]:
        """Get all validation messages (errors and warnings)."""
        return self.validation_errors + self.validation_warnings

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "modified" if self.is_modified else "unchanged"
        return f"FieldState(value={self.current_value}, {status}, {self.validation_state.value})"
