"""
Configuration management panel.

Provides interface for managing saved configurations (Phase 3 feature placeholder).
"""

from typing import List, Optional
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QGroupBox,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon # Added QDesktopServices

from .apply_button import ApplyChangesButton
from .search_widget import SearchWidget # Added SearchWidget import
from ...core.optimizations.search_indexer import SearchIndexer # Added SearchIndexer import


class ConfigurationPanel(QWidget):
    """Panel for managing saved configurations."""

    # Signals
    load_requested = pyqtSignal(str)  # config_name
    save_requested = pyqtSignal()
    compare_requested = pyqtSignal(str)  # config_name
    delete_requested = pyqtSignal(str)  # config_name
    reload_config_requested = pyqtSignal()
    # Signals to bubble up from SearchWidget
    search_requested_from_panel = pyqtSignal(str)
    search_cleared_from_panel = pyqtSignal()
    search_navigation_from_panel = pyqtSignal(int)
    open_settings_location_requested = pyqtSignal() # New signal

    def __init__(
        self,
        apply_button_widget: ApplyChangesButton,
        search_indexer: SearchIndexer, # Added search_indexer
        parent=None
    ):
        """Initialize the configuration panel."""
        super().__init__(parent)
        self.search_indexer = search_indexer # Store search_indexer

        self.logger = logging.getLogger(__name__)

        # UI components
        self.config_list: Optional[QListWidget] = None
        self.load_button: Optional[QPushButton] = None
        self.save_button: Optional[QPushButton] = None
        self.compare_button: Optional[QPushButton] = None
        self.delete_button: Optional[QPushButton] = None
        self.reload_button: Optional[QPushButton] = None
        self.open_settings_button: Optional[QPushButton] = None # New button
        self.apply_changes_button_widget = apply_button_widget
        self.search_widget: Optional[SearchWidget] = None # Add SearchWidget member

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_label = QLabel("Configuration Manager")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Item 4: Center title
        layout.addWidget(title_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #ddd;")
        layout.addWidget(separator)
        
        # Current configuration info
        current_group = QGroupBox("Current Configuration")
        current_layout = QVBoxLayout(current_group)

        self.current_info_label = QLabel("Active game configuration") # Will show profile name or "Game Files"
        self.current_info_label.setStyleSheet("color: #333; font-weight: bold;") # Make it more prominent
        self.current_info_label.setWordWrap(True)
        current_layout.addWidget(self.current_info_label)

        self.location_label = QLabel("Location: Not loaded") # New label for path
        self.location_label.setStyleSheet("color: #555; font-size: 10px;")
        self.location_label.setWordWrap(True)
        current_layout.addWidget(self.location_label)

        layout.addWidget(current_group)

        # Saved configurations section
        saved_group = QGroupBox("Saved Configurations")
        saved_layout = QVBoxLayout(saved_group)

        # Configuration list
        self.config_list = QListWidget()
        self.config_list.setMaximumHeight(200)
        saved_layout.addWidget(self.config_list)

        # Button layout
        button_layout = QHBoxLayout()

        self.load_button = QPushButton("Load")
        self.load_button.setEnabled(False)  # Will be enabled when selection is made
        button_layout.addWidget(self.load_button)

        self.save_button = QPushButton("Save As...")
        self.save_button.setEnabled(True)  # Always enabled to save current config
        button_layout.addWidget(self.save_button)

        saved_layout.addLayout(button_layout)

        # Compare button
        self.compare_button = QPushButton("Compare with Selected")
        self.compare_button.setEnabled(False)  # Enabled when selection is made
        saved_layout.addWidget(self.compare_button)

        # Delete button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setEnabled(False)  # Enabled when selection is made
        self.delete_button.setStyleSheet("color: #d32f2f;")
        saved_layout.addWidget(self.delete_button)

        layout.addWidget(saved_group)

        # Search Widget - Moved after "Saved Configurations" group
        self.search_widget = SearchWidget()
        if self.search_indexer:
            self.search_widget.set_search_indexer(self.search_indexer)
        layout.addWidget(self.search_widget)

        # Separator after search
        search_separator = QFrame()
        search_separator.setFrameShape(QFrame.Shape.HLine)
        search_separator.setStyleSheet("color: #ddd;")
        layout.addWidget(search_separator)

        # Spacer to push bottom buttons down
        layout.addStretch(1)  # Ensure this stretch is before bottom_buttons_layout

        # Bottom buttons layout (for Apply Changes, Reload)
        self.bottom_buttons_layout = QHBoxLayout()

        # Add Reload button (Item 7: Reload on the left)
        self.reload_button = QPushButton("")  # Item 6: Remove text
        self.reload_button.setIcon(QIcon.fromTheme("view-refresh"))  # Item 6: Set icon
        self.reload_button.setToolTip("Reload configuration files from disk (F5)")
        # Item 6: Set fixed size for icon button appearance
        self.reload_button.setFixedSize(QSize(32, 32))
        self.reload_button.setIconSize(QSize(24, 24))  # Ensure icon isn't too small
        self.bottom_buttons_layout.addWidget(self.reload_button)

        # Add Open Settings Folder button
        self.open_settings_button = QPushButton("") # Icon only
        self.open_settings_button.setIcon(QIcon.fromTheme("document-open-folder")) # Example icon
        self.open_settings_button.setToolTip("Open Settings.JSON Path...")
        self.open_settings_button.setFixedSize(QSize(32,32))
        self.open_settings_button.setIconSize(QSize(24,24))
        self.bottom_buttons_layout.addWidget(self.open_settings_button)

        self.bottom_buttons_layout.addStretch(1)

        # Add Apply Changes button
        if self.apply_changes_button_widget:
            self.apply_changes_button_widget.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
            self.bottom_buttons_layout.addWidget(self.apply_changes_button_widget)

        self.bottom_buttons_layout.setSpacing(10)

        layout.addLayout(self.bottom_buttons_layout)

        # No additional stretch needed here if the one above pushes content correctly.
        # layout.addStretch()

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # Selection changes
        self.config_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Button clicks
        self.load_button.clicked.connect(self.on_load_clicked)
        self.save_button.clicked.connect(self.on_save_clicked)
        self.compare_button.clicked.connect(self.on_compare_clicked)
        self.delete_button.clicked.connect(self.on_delete_clicked)
        if self.reload_button:
            self.reload_button.clicked.connect(self.on_reload_clicked)
        if self.open_settings_button:
            self.open_settings_button.clicked.connect(self.on_open_settings_location_clicked)
        
        # Connect SearchWidget signals
        if self.search_widget:
            self.search_widget.search_requested.connect(self.search_requested_from_panel.emit)
            self.search_widget.search_cleared.connect(self.search_cleared_from_panel.emit)
            self.search_widget.result_navigation.connect(self.search_navigation_from_panel.emit)

    def on_selection_changed(self) -> None:
        """Handle configuration list selection changes."""
        has_selection = bool(self.config_list.currentItem())
        self.load_button.setEnabled(has_selection)
        self.compare_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def on_load_clicked(self) -> None:
        """Handle load button click."""
        current_item = self.config_list.currentItem()
        if current_item:
            config_name = current_item.text()
            self.load_requested.emit(config_name)

    def on_save_clicked(self) -> None:
        """Handle save button click."""
        self.save_requested.emit()

    def on_compare_clicked(self) -> None:
        """Handle compare button click."""
        current_item = self.config_list.currentItem()
        if current_item:
            config_name = current_item.text()
            self.compare_requested.emit(config_name)

    def on_delete_clicked(self) -> None:
        """Handle delete button click."""
        current_item = self.config_list.currentItem()
        if current_item:
            config_name = current_item.text()
            self.delete_requested.emit(config_name)

    def on_reload_clicked(self) -> None:
        """Handle reload button click."""
        self.reload_config_requested.emit()

    def on_open_settings_location_clicked(self) -> None:
        """Handle open settings location button click."""
        self.open_settings_location_requested.emit()

    def update_current_info(self, config_identifier: str, change_count: int, is_profile: bool = False) -> None:
        """
        Update the current configuration information.

        Args:
            config_identifier: Path to the game installation or name of the loaded profile.
            change_count: Number of pending changes.
            is_profile: True if config_identifier is a profile name, False if it's a game path.
        """
        # Update game path info
        if is_profile:
            self.current_info_label.setText(f"<b>Active Profile:</b> {config_identifier}")
        elif config_identifier == "Example Configuration":
             self.current_info_label.setText(f"<b>Active:</b> {config_identifier}")
        else:
            self.current_info_label.setText("<b>Active Game Files</b>") # Simpler title
            self.location_label.setText(f"Location: {config_identifier}")



    def populate_saved_configurations(self, configurations: List[str]) -> None:
        """
        Populate the list with saved configurations.

        Args:
            configurations: List of saved configuration names
        """
        self.config_list.clear()

        for config_name in configurations:
            self.config_list.addItem(config_name)

        # Update button states
        self.on_selection_changed()

    def get_selected_configuration(self) -> Optional[str]:
        """
        Get the currently selected configuration name.

        Returns:
            Selected configuration name or None
        """
        current_item = self.config_list.currentItem()
        if current_item:
            return current_item.text()
        return None
