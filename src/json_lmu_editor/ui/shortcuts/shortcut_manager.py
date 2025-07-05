"""
Keyboard shortcut management for the LMU Configuration Editor.

Provides centralized management of keyboard shortcuts with tooltip updates.
"""

from typing import Dict, Callable, Optional
import logging

from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QAction


class ShortcutManager(QObject):
    """Manages keyboard shortcuts for the application."""

    # Signals
    shortcut_triggered = pyqtSignal(str, str)  # action_name, shortcut_key

    def __init__(self, main_window: QMainWindow):
        """
        Initialize the shortcut manager.

        Args:
            main_window: Main application window
        """
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.main_window = main_window
        self.shortcuts: Dict[str, QShortcut] = {}
        self.actions: Dict[str, QAction] = {}

        # Standard shortcut mappings - only Ctrl+S for apply changes
        self.shortcut_map = {
            # Only shortcut: apply changes
            "apply_changes": ("Ctrl+S", "Apply all pending changes", "apply_changes"),
        }

    def register_shortcuts(self) -> None:
        """Register all keyboard shortcuts for the main window."""
        self.logger.info("Registering keyboard shortcuts")

        for action_name, (
            shortcut_key,
            description,
            method_name,
        ) in self.shortcut_map.items():
            try:
                # Get the method from main window
                method = getattr(self.main_window, method_name, None)
                if method and callable(method):
                    self.create_shortcut(action_name, shortcut_key, description, method)
                else:
                    # Create placeholder for methods that don't exist yet
                    def placeholder(name=action_name):
                        return self.shortcut_triggered.emit(name, shortcut_key)

                    self.create_shortcut(
                        action_name, shortcut_key, description, placeholder
                    )

            except Exception as e:
                self.logger.warning(f"Failed to register shortcut '{action_name}': {e}")

        # Update tooltips with shortcuts
        self.update_tooltips_with_shortcuts()

        self.logger.info(f"Registered {len(self.shortcuts)} keyboard shortcuts")

    def create_shortcut(
        self, name: str, shortcut: str, description: str, callback: Callable
    ) -> Optional[QShortcut]:
        """
        Create a keyboard shortcut.

        Args:
            name: Shortcut name/identifier
            shortcut: Key sequence (e.g., 'Ctrl+S')
            description: Human-readable description
            callback: Function to call when triggered

        Returns:
            Created QShortcut or None if failed
        """
        try:
            key_sequence = QKeySequence(shortcut)
            if key_sequence.isEmpty():
                self.logger.warning(f"Invalid key sequence: {shortcut}")
                return None

            # Create QShortcut
            shortcut_obj = QShortcut(key_sequence, self.main_window)
            shortcut_obj.activated.connect(callback)

            # Store for management
            self.shortcuts[name] = shortcut_obj

            self.logger.debug(f"Created shortcut '{name}': {shortcut} -> {description}")
            return shortcut_obj

        except Exception as e:
            self.logger.error(f"Error creating shortcut '{name}': {e}")
            return None

    def create_action(
        self,
        name: str,
        shortcut: str,
        description: str,
        callback: Callable,
        parent: Optional[QWidget] = None,
    ) -> Optional[QAction]:
        """
        Create a QAction with keyboard shortcut.

        Args:
            name: Action name/identifier
            shortcut: Key sequence (e.g., 'Ctrl+S')
            description: Human-readable description
            callback: Function to call when triggered
            parent: Parent widget (defaults to main window)

        Returns:
            Created QAction or None if failed
        """
        try:
            if parent is None:
                parent = self.main_window

            action = QAction(description, parent)
            action.setShortcut(QKeySequence(shortcut))
            action.setStatusTip(f"{description} ({shortcut})")
            action.triggered.connect(callback)

            # Store for management
            self.actions[name] = action

            return action

        except Exception as e:
            self.logger.error(f"Error creating action '{name}': {e}")
            return None

    def update_tooltips_with_shortcuts(self) -> None:
        """Update widget tooltips to include keyboard shortcuts."""
        try:
            # Update apply button tooltip
            if (
                hasattr(self.main_window, "apply_button")
                and self.main_window.apply_button
            ):
                original_tooltip = (
                    self.main_window.apply_button.toolTip() or "Apply changes"
                )
                if "Ctrl+S" not in original_tooltip:
                    new_tooltip = f"{original_tooltip} (Ctrl+S)"
                    self.main_window.apply_button.setToolTip(new_tooltip)

        except Exception as e:
            self.logger.warning(f"Error updating tooltips: {e}")

    def get_shortcut_text(self, action_name: str) -> str:
        """
        Get the shortcut text for an action.

        Args:
            action_name: Name of the action

        Returns:
            Shortcut text or empty string if not found
        """
        if action_name in self.shortcut_map:
            return self.shortcut_map[action_name][0]
        return ""

    def get_shortcut_description(self, action_name: str) -> str:
        """
        Get the description for an action.

        Args:
            action_name: Name of the action

        Returns:
            Description text or empty string if not found
        """
        if action_name in self.shortcut_map:
            return self.shortcut_map[action_name][1]
        return ""

    def enable_shortcut(self, action_name: str, enabled: bool = True) -> None:
        """
        Enable or disable a specific shortcut.

        Args:
            action_name: Name of the shortcut to modify
            enabled: Whether to enable or disable
        """
        if action_name in self.shortcuts:
            self.shortcuts[action_name].setEnabled(enabled)
        if action_name in self.actions:
            self.actions[action_name].setEnabled(enabled)

    def get_all_shortcuts(self) -> Dict[str, tuple]:
        """
        Get all registered shortcuts.

        Returns:
            Dictionary mapping action names to (shortcut, description, method) tuples
        """
        return self.shortcut_map.copy()

    def is_shortcut_available(self, key_sequence: str) -> bool:
        """
        Check if a key sequence is available (not already used).

        Args:
            key_sequence: Key sequence to check

        Returns:
            True if available, False if already used
        """
        for shortcut_data in self.shortcut_map.values():
            if shortcut_data[0] == key_sequence:
                return False
        return True

    def add_custom_shortcut(
        self, name: str, shortcut: str, description: str, callback: Callable
    ) -> bool:
        """
        Add a custom shortcut at runtime.

        Args:
            name: Unique name for the shortcut
            shortcut: Key sequence
            description: Human-readable description
            callback: Function to call

        Returns:
            True if added successfully
        """
        if name in self.shortcut_map:
            self.logger.warning(f"Shortcut name '{name}' already exists")
            return False

        if not self.is_shortcut_available(shortcut):
            self.logger.warning(f"Shortcut '{shortcut}' is already in use")
            return False

        # Add to shortcut map
        self.shortcut_map[name] = (shortcut, description, callback.__name__)

        # Create the shortcut
        shortcut_obj = self.create_shortcut(name, shortcut, description, callback)
        return shortcut_obj is not None

    def remove_shortcut(self, action_name: str) -> bool:
        """
        Remove a shortcut.

        Args:
            action_name: Name of the shortcut to remove

        Returns:
            True if removed successfully
        """
        removed = False

        if action_name in self.shortcuts:
            self.shortcuts[action_name].deleteLater()
            del self.shortcuts[action_name]
            removed = True

        if action_name in self.actions:
            self.actions[action_name].deleteLater()
            del self.actions[action_name]
            removed = True

        if action_name in self.shortcut_map:
            del self.shortcut_map[action_name]
            removed = True

        return removed


class KeyboardNavigationMixin:
    """Mixin class to add keyboard navigation capabilities to widgets."""

    def setup_keyboard_navigation(self) -> None:
        """Set up keyboard navigation for the widget."""
        # This can be implemented by widgets that need custom navigation
        pass

    def handle_tab_navigation(self, event) -> bool:
        """
        Handle tab navigation key events.

        Args:
            event: QKeyEvent

        Returns:
            True if event was handled
        """
        # Default implementation - can be overridden
        return False

    def handle_field_navigation(self, event) -> bool:
        """
        Handle field navigation key events.

        Args:
            event: QKeyEvent

        Returns:
            True if event was handled
        """
        # Default implementation - can be overridden
        return False

    def focus_next_modified_field(self) -> bool:
        """
        Focus the next modified field.

        Returns:
            True if a field was focused
        """
        # Default implementation - can be overridden
        return False

    def focus_previous_modified_field(self) -> bool:
        """
        Focus the previous modified field.

        Returns:
            True if a field was focused
        """
        # Default implementation - can be overridden
        return False
