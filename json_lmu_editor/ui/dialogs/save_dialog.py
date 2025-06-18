"""
Save configuration dialog.

Provides interface for saving current configuration with a custom name.
"""

import re
from typing import Optional, Tuple
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtGui import QFont


class SaveConfigurationDialog(QDialog):
    """Dialog for saving configuration with custom name and description."""

    def __init__(self, existing_configs: list, parent=None):
        """
        Initialize the save configuration dialog.

        Args:
            existing_configs: List of existing configuration names
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.existing_configs = existing_configs

        # UI components
        self.name_input: Optional[QLineEdit] = None
        # self.description_input: Optional[QTextEdit] = None # Removed
        self.error_label: Optional[QLabel] = None
        self.ok_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None

        # Result
        self.configuration_name = ""
        # self.configuration_description = "" # Removed

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Save Configuration")
        self.setModal(True)
        self.resize(400, 200) # Reduced height as description is removed

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Save Current Configuration")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        layout.addWidget(title_label)

        # Name group
        name_group = QGroupBox("Configuration Name")
        name_layout = QVBoxLayout(name_group)

        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter a name for this configuration...")
        name_layout.addWidget(self.name_input)

        # Name rules
        rules_text = (
            "Rules:\n"
            "• 1-50 characters\n"
            "• Letters, numbers, spaces, hyphens, underscores only\n"
            "• Cannot use reserved names (default, active, etc.)"
        )
        rules_label = QLabel(rules_text)
        rules_label.setStyleSheet("color: #666; font-size: 11px;")
        name_layout.addWidget(rules_label)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setVisible(False)
        name_layout.addWidget(self.error_label)

        layout.addWidget(name_group)

        # Description group - REMOVED
        # desc_group = QGroupBox("Description (Optional)")
        # desc_layout = QVBoxLayout(desc_group)
        #
        # self.description_input = QTextEdit()
        # self.description_input.setPlaceholderText(
        #     "Enter a description for this configuration (e.g., 'Wet weather setup with reduced AI difficulty')"
        # )
        # self.description_input.setMaximumHeight(100)
        # desc_layout.addWidget(self.description_input)
        #
        # layout.addWidget(desc_group)

        layout.addStretch(1) # Add stretch to push buttons to bottom if space allows

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("Save Configuration")
        self.ok_button.setEnabled(False)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # Name input validation
        self.name_input.textChanged.connect(self.validate_name)

        # Buttons
        self.ok_button.clicked.connect(self.accept_save)
        self.cancel_button.clicked.connect(self.reject)

    def validate_name(self, name: str) -> None:
        """
        Validate the configuration name.

        Args:
            name: Name to validate
        """
        is_valid, error_message = self.validate_configuration_name(name)

        if is_valid:
            self.error_label.setVisible(False)
            self.ok_button.setEnabled(True)
        else:
            self.error_label.setText(error_message)
            self.error_label.setVisible(True)
            self.ok_button.setEnabled(False)

    def validate_configuration_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate configuration name according to rules.

        Args:
            name: Name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        name = name.strip()

        # Check empty
        if not name:
            return False, "Name cannot be empty"

        # Check length
        if len(name) > 50:
            return False, "Name too long (maximum 50 characters)"

        # Check allowed characters
        if not re.match(r"^[a-zA-Z0-9 _-]+$", name):
            return False, "Name contains invalid characters"

        # Check reserved names
        reserved_names = {
            "default",
            "active",
            "current",
            "temp",
            "temporary",
            "backup",
            "original",
            "settings",
            "config",
        }
        if name.lower() in reserved_names:
            return False, f"'{name}' is a reserved name"

        # Check duplicates
        if name in self.existing_configs:
            return False, f"Configuration '{name}' already exists"

        return True, ""

    def check_duplicate(self, name: str) -> bool:
        """
        Check if configuration name already exists.

        Args:
            name: Name to check

        Returns:
            True if duplicate exists
        """
        return name in self.existing_configs

    def accept_save(self) -> None:
        """Accept the dialog and save configuration."""
        name = self.name_input.text().strip()

        # Final validation
        is_valid, error_message = self.validate_configuration_name(name)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Name", error_message)
            return

        # Check for duplicate one more time with confirmation
        if self.check_duplicate(name):
            reply = QMessageBox.question(
                self,
                "Configuration Exists",
                f"A configuration named '{name}' already exists.\n\n"
                "Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Store results
        self.configuration_name = name
        # self.configuration_description = self.description_input.toPlainText().strip() # Removed

        # Accept dialog
        self.accept()

    def get_configuration_name(self) -> Optional[str]:
        """
        Get the entered configuration name.

        Returns:
            Configuration name or None if dialog was cancelled
        """
        return self.configuration_name if self.configuration_name else None

    def get_configuration_description(self) -> str:
        """
        Get the entered configuration description. (DEPRECATED - returns empty string)

        Returns:
            Configuration description (empty string)
        """
        return "" # Description field removed
