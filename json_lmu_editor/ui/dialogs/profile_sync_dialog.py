"""
Profile synchronization dialog for handling conflicts between active profile and current settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QButtonGroup, QRadioButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import List, Optional


class ProfileSyncChoice:
    """Represents user's choice for profile sync conflict."""
    UPDATE_PROFILE = "update_profile"
    UPDATE_SETTINGS = "update_settings" 
    IGNORE = "ignore"


class ProfileSyncDialog(QDialog):
    """Dialog for handling profile synchronization conflicts."""
    
    def __init__(self, profile_name: str, differences: List[str], parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.differences = differences
        self.choice = None
        
        self.setWindowTitle("Profile Synchronization")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Profile Synchronization Conflict")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #ddd;")
        layout.addWidget(separator)
        
        # Description
        desc_text = (
            f"The active profile <b>'{self.profile_name}'</b> does not match "
            f"your current game settings.\n\n"
            f"The following files have differences:"
        )
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Differences list
        diff_text = QTextEdit()
        diff_text.setMaximumHeight(100)
        diff_text.setReadOnly(True)
        diff_content = "\n".join(f"• {diff}" for diff in self.differences)
        diff_text.setPlainText(diff_content)
        layout.addWidget(diff_text)
        
        # Choice section
        choice_label = QLabel("How would you like to resolve this conflict?")
        choice_font = QFont()
        choice_font.setBold(True)
        choice_label.setFont(choice_font)
        layout.addWidget(choice_label)
        
        # Radio button group
        self.button_group = QButtonGroup(self)
        
        # Option 1: Update profile
        self.update_profile_radio = QRadioButton(
            f"Update profile '{self.profile_name}' with current settings"
        )
        self.update_profile_radio.setChecked(True)  # Default choice
        self.button_group.addButton(self.update_profile_radio, 0)
        layout.addWidget(self.update_profile_radio)
        
        profile_desc = QLabel("This will overwrite the saved profile with your current game settings.")
        profile_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 10px;")
        profile_desc.setWordWrap(True)
        layout.addWidget(profile_desc)
        
        # Option 2: Update settings
        self.update_settings_radio = QRadioButton(
            f"Update current settings with profile '{self.profile_name}'"
        )
        self.button_group.addButton(self.update_settings_radio, 1)
        layout.addWidget(self.update_settings_radio)
        
        settings_desc = QLabel("This will overwrite your current game settings with the saved profile.")
        settings_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 10px;")
        settings_desc.setWordWrap(True)
        layout.addWidget(settings_desc)
        
        # Option 3: Ignore
        self.ignore_radio = QRadioButton("Ignore and continue")
        self.button_group.addButton(self.ignore_radio, 2)
        layout.addWidget(self.ignore_radio)
        
        ignore_desc = QLabel("Keep both files as they are. No synchronization will be performed.")
        ignore_desc.setStyleSheet("color: #666; margin-left: 20px;")
        ignore_desc.setWordWrap(True)
        layout.addWidget(ignore_desc)
        
        # Spacer
        layout.addStretch()
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # OK button
        ok_button = QPushButton("Apply")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
    
    def get_choice(self) -> Optional[str]:
        """Get the user's choice."""
        if self.result() == QDialog.DialogCode.Accepted:
            checked_id = self.button_group.checkedId()
            if checked_id == 0:
                return ProfileSyncChoice.UPDATE_PROFILE
            elif checked_id == 1:
                return ProfileSyncChoice.UPDATE_SETTINGS
            elif checked_id == 2:
                return ProfileSyncChoice.IGNORE
        return None
    
    @staticmethod
    def show_sync_dialog(profile_name: str, differences: List[str], parent=None) -> Optional[str]:
        """
        Show the profile sync dialog and return user's choice.
        
        Args:
            profile_name: Name of the active profile
            differences: List of files with differences
            parent: Parent widget
            
        Returns:
            User's choice or None if cancelled
        """
        dialog = ProfileSyncDialog(profile_name, differences, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_choice()
        return None