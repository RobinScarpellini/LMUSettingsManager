"""
Field widget for displaying and editing configuration fields.

Provides type-appropriate input controls for different field types.
"""

from typing import Any, Optional
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QTextEdit,
    QPushButton,
    QFrame,
    QSizePolicy, # Added for RetainSizeWhenHidden
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ...core.parsers.json_parser import FieldInfo, FieldType
from ...core.models.configuration_model import ConfigurationModel


class FieldWidget(QWidget):
    """Widget for displaying and editing a configuration field."""

    # Signals
    value_changed = pyqtSignal(str, object)  # field_path, new_value
    revert_requested = pyqtSignal(str)  # field_path

    def __init__(
        self,
        field_path: str,
        field_info: FieldInfo,
        config_model: ConfigurationModel,
        parent=None,
    ):
        """
        Initialize the field widget.

        Args:
            field_path: Path to the configuration field
            field_info: Field information and metadata
            config_model: Configuration model for state tracking
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        # Field data
        self.field_path = field_path
        self.field_info = field_info
        self.config_model = config_model

        # UI components
        self.name_label: Optional[QLabel] = None
        self.input_widget: Optional[QWidget] = None
        self.description_label: Optional[QLabel] = None
        self.modified_indicator: Optional[QLabel] = None
        self.revert_button: Optional[QPushButton] = None

        # State
        self.is_updating = False  # Prevent recursive updates
        self.is_highlighted = False
        self.original_style = ""

        # Debounce timer for text inputs
        self.change_timer = QTimer()
        self.change_timer.setSingleShot(True)
        self.change_timer.timeout.connect(self.emit_value_changed)
        
        self.setup_ui()
        self.update_modification_state()
        self._log_layout_details() # Add this call after UI is set up

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        # Removed stretch from the top to ensure top-alignment of content

        # Set L,R margins to 5. Top margin is 1px. Bottom margin is 0 for now.
        layout.setContentsMargins(
            5, 1, 5, 0  # Reduced top margin to 1px
        )
        # Internal spacing for items directly in this layout (e.g., name_block vs description_block)
        layout.setSpacing(0) # Reduced internal spacing to 0px
        
        # Create input widget first to determine layout type
        self.input_widget = self.create_input_widget()

        # Field name label (common for both layouts)
        raw_display_name = self.field_path.split(".")[-1]
        
        # Clean known prefixes/suffixes from the field name for display
        # Order of replacement can matter if prefixes/suffixes overlap or interact.
        
        temp_name = raw_display_name
        
        # Define common prefixes and suffixes to remove from field names for display
        # These are typically category-level descriptors that end up in field names.
        prefixes_to_remove = [
            "UI Gamepad Mouse - ",
            # Add other common prefixes if identified
        ]
        suffixes_to_remove = [
            " In Packages Directory", # This seems to be a category descriptor
            # Add other common suffixes if identified
        ]

        for prefix in prefixes_to_remove:
            if temp_name.startswith(prefix):
                temp_name = temp_name[len(prefix):]
                
        for suffix in suffixes_to_remove:
            if temp_name.endswith(suffix):
                temp_name = temp_name[:-len(suffix)]
        
        # After removing known affixes, strip and ensure it's not empty
        cleaned_display_name = temp_name.strip()
        if not cleaned_display_name: # Fallback if cleaning results in empty string
            cleaned_display_name = raw_display_name

        self.name_label = QLabel(cleaned_display_name)
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)

        # Revert button (Item 3.1: Relocated and orange dot removed)
        self.revert_button = QPushButton("Revert")
        self.revert_button.setVisible(False)
        self.revert_button.clicked.connect(self.revert_field)
        self.revert_button.setMaximumWidth(60)
        sp = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sp.setRetainSizeWhenHidden(True)
        self.revert_button.setSizePolicy(sp) # Keep space when hidden
        # self.revert_button.setStyleSheet("margin-right: 5px;") # Adjusted margin for new position

        self.modified_indicator = None  # Explicitly set to None

        if isinstance(self.input_widget, QTextEdit):
            # Vertical layout for QTextEdit (multiline)
            # Header: Revert, Name Label, Stretch
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0,0,0,0) # Ensure no extra margins
            # Ensure header content is left-aligned
            header_layout.addWidget(
                self.revert_button
            )
            header_layout.addWidget(self.name_label)
            header_layout.addStretch(1) # Pushes name and revert button to the left
            # Removed controls_layout from here as modified_indicator is removed
            layout.addLayout(header_layout)

            if self.input_widget:
                # Item 1.4: Remove setMaximumWidth to allow full column width
                # self.input_widget.setMaximumWidth(400)
                layout.addWidget(self.input_widget)
        else:
            # Horizontal layout for QLineEdit, QCheckBox (single-line)
            content_layout = QHBoxLayout()
            content_layout.setContentsMargins(0,0,0,0) # Ensure no extra margins
            content_layout.setSpacing(1) # Reduced spacing to 1px to match main layout
            
            # Item 1 (Revert Button Position): NameLabel first
            self.name_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            content_layout.addWidget(self.name_label, 1) # Allow name_label to take available space
            # content_layout.addStretch(1) # Original spacer, now name_label takes space

            # Item 1 (Revert Button Position): Revert button before input widget
            content_layout.addWidget(self.revert_button)
            
            if self.input_widget:
                if isinstance(
                    self.input_widget, QLineEdit
                ):  # Item 2: Only QLineEdit gets fixed width
                    self.input_widget.setFixedWidth(160) # Increased width
                # elif isinstance(self.input_widget, QCheckBox): # Item 2: QCheckBox sizes naturally
                # self.input_widget.setFixedWidth(200) # Removed
                
                content_layout.addWidget(
                    self.input_widget,
                    0, # Stretch factor 0 for input_widget
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                )
            
            layout.addLayout(content_layout)

        # Description label
        self.description_label = QLabel(self.field_info.description if self.field_info.description else "")
        self.description_label.setWordWrap(True)
        # Make description more visible in light theme, and ensure consistent height with padding
        self.description_label.setStyleSheet(
            "color: #555; font-size: 11px; padding: 1px;" # Reduced padding to 1px
        )
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self.description_label)

        # Add spacing (1px) before the separator line
        layout.addSpacing(1) # Reduced spacing to 1px

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #ddd;")
        separator.setFixedHeight(1) # Ensure it's thin
        layout.addWidget(separator)

        # Store original style for highlighting
        self.original_style = self.styleSheet()

        # Set size policy to allow varying heights
        sp = self.sizePolicy()
        sp.setVerticalPolicy(QSizePolicy.Policy.Preferred) # Prefer natural height
        sp.setHorizontalPolicy(QSizePolicy.Policy.Expanding) # Expand horizontally
        self.setSizePolicy(sp)
        
    def _log_layout_details(self):
        """Logs detailed layout information for debugging."""
        if not self.logger.isEnabledFor(logging.DEBUG):
            return

        # self.logger.debug(f"--- FieldWidget Debug: {self.field_path} ---")
        
        # Main layout
        main_layout = self.layout()
        if main_layout:
            self.logger.debug(f"  MainLayout: type={type(main_layout)}")
            cm = main_layout.contentsMargins()
            self.logger.debug(f"    contentsMargins=(L:{cm.left()}, T:{cm.top()}, R:{cm.right()}, B:{cm.bottom()})")
            self.logger.debug(f"    spacing={main_layout.spacing()}")
        else:
            self.logger.debug("  MainLayout: None")

        self.logger.debug(f"  FieldWidget: sizeHint={self.sizeHint()}, minimumSizeHint={self.minimumSizeHint()}")
        # Name Label
        if self.name_label:
            self.logger.debug(f"  NameLabel: text='{self.name_label.text()}'")
            self.logger.debug(f"    sizeHint={self.name_label.sizeHint()}, minimumSizeHint={self.name_label.minimumSizeHint()}")
            self.logger.debug(f"    fontPointSize={self.name_label.font().pointSize()}, bold={self.name_label.font().bold()}")

        # Input Widget
        if self.input_widget:
            self.logger.debug(f"  InputWidget: type={type(self.input_widget)}")
            self.logger.debug(f"    sizeHint={self.input_widget.sizeHint()}, minimumSizeHint={self.input_widget.minimumSizeHint()}")
            if hasattr(self.input_widget, 'contentsMargins') and callable(getattr(self.input_widget, 'contentsMargins', None)):
                cm_input = self.input_widget.contentsMargins()
                self.logger.debug(f"    InputWidget contentsMargins=(L:{cm_input.left()}, T:{cm_input.top()}, R:{cm_input.right()}, B:{cm_input.bottom()})")
            if hasattr(self.input_widget, 'styleSheet'):
                 self.logger.debug(f"    styleSheet='{self.input_widget.styleSheet()}'")


        # Description Label
        if self.description_label:
            desc_text = self.description_label.text()
            # Log actual visibility at this point, though it might change later
            self.logger.debug(f"  DescriptionLabel: text='{desc_text[:30]}...' (len={len(desc_text)}) isVisibleToLayout={self.description_label.isVisibleTo(self)}")
            self.logger.debug(f"    sizeHint={self.description_label.sizeHint()}, minimumSizeHint={self.description_label.minimumSizeHint()}")
            self.logger.debug(f"    styleSheet='{self.description_label.styleSheet()}'")


        # Separator - usually a QFrame, height is key
        if main_layout:
            for i in range(main_layout.count()):
                item = main_layout.itemAt(i)
                if item is None:
                    continue
                
                widget = item.widget()
                if widget and isinstance(widget, QFrame) and widget.frameShape() == QFrame.Shape.HLine:
                    self.logger.debug(f"  Separator (QFrame): sizeHint={widget.sizeHint()}, minimumSizeHint={widget.minimumSizeHint()}")
                    self.logger.debug(f"    styleSheet='{widget.styleSheet()}'")
                    break
                # Also check for QSpacerItem if layout.addSpacing was used
                spacer = item.spacerItem()
                if spacer and not widget : # It's a spacer item
                     self.logger.debug(f"  SpacerItem before separator: sizeHint={spacer.sizeHint()}, isEmpty={spacer.isEmpty()}")


            # Log the explicit spacer added before the separator if it's the one before last item (separator)
            # This assumes separator is the last widget, and spacer is before it.
            if main_layout.count() >= 2:
                item_before_last = main_layout.itemAt(main_layout.count() - 2) # Potentially the addSpacing(1)
                if item_before_last and item_before_last.spacerItem():
                     self.logger.debug(f"  Explicit Spacer (before separator): sizeHint={item_before_last.spacerItem().sizeHint()}, isEmpty={item_before_last.spacerItem().isEmpty()}")


        # self.logger.debug(f"--- End FieldWidget Debug: {self.field_path} ---")

    def create_input_widget(self) -> Optional[QWidget]:
        """
        Create the appropriate input widget based on field type.

        Returns:
            Input widget for the field type
        """
        current_value = self.config_model.get_field_value(self.field_path)

        if self.field_info.type == FieldType.BOOLEAN:
            return self.create_boolean_widget(current_value)
        elif self.field_info.type == FieldType.ARRAY:
            return self.create_array_widget(current_value)
        else:  # STRING, INTEGER, FLOAT or fallback - all use text fields
            return self.create_string_widget(current_value)

    def create_boolean_widget(self, current_value: Any) -> QCheckBox:
        """Create a checkbox for boolean values."""
        checkbox = QCheckBox()
        checkbox.setChecked(bool(current_value))
        checkbox.stateChanged.connect(self.on_boolean_changed)
        return checkbox

    def create_string_widget(self, current_value: Any) -> QLineEdit:
        """Create a line edit for string values."""
        line_edit = QLineEdit()
        line_edit.setText(str(current_value) if current_value is not None else "")
        line_edit.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )  # Align text within QLineEdit to the right
        line_edit.textChanged.connect(self.on_text_changed)
        return line_edit

    def create_array_widget(self, current_value: Any) -> QTextEdit:
        """Create a text edit for array/object values."""
        text_edit = QTextEdit()
        # text_edit.setMaximumHeight(60) # Removed to allow individual height
        text_edit.setPlainText(str(current_value) if current_value is not None else "")
        text_edit.textChanged.connect(self.on_text_area_changed)
        return text_edit

    def on_boolean_changed(self, state: int) -> None:
        """Handle boolean value changes."""
        if self.is_updating:
            return

        new_value = state == Qt.CheckState.Checked.value
        self.schedule_value_change(new_value)

    def on_text_changed(self, text: str) -> None:
        """Handle text value changes with debouncing."""
        if self.is_updating:
            return

        # Debounce text changes
        self.pending_value = text
        self.change_timer.stop()
        self.change_timer.start(500)  # 500ms delay

    def on_text_area_changed(self) -> None:
        """Handle text area value changes with debouncing."""
        if self.is_updating:
            return

        text = self.input_widget.toPlainText()
        self.pending_value = text
        self.change_timer.stop()
        self.change_timer.start(500)  # 500ms delay

    def schedule_value_change(self, value: Any) -> None:
        """Schedule a value change to be emitted."""
        self.pending_value = value
        self.emit_value_changed()

    def emit_value_changed(self) -> None:
        """Emit the value changed signal."""
        if hasattr(self, "pending_value"):
            self.value_changed.emit(self.field_path, self.pending_value)
            self.update_modification_state()

    def revert_field(self) -> None:
        """Revert the field to its original value."""
        self.revert_requested.emit(self.field_path)

    def refresh_from_model(self) -> None:
        """Refresh the widget state from the model."""
        self.is_updating = True

        try:
            # Get current value from model
            current_value = self.config_model.get_field_value(self.field_path)

            # Update input widget
            if isinstance(self.input_widget, QCheckBox):
                self.input_widget.setChecked(bool(current_value))
            elif isinstance(self.input_widget, QLineEdit):
                self.input_widget.setText(
                    str(current_value) if current_value is not None else ""
                )
            elif isinstance(self.input_widget, QTextEdit):
                self.input_widget.setPlainText(
                    str(current_value) if current_value is not None else ""
                )

            # Update modification state
            self.update_modification_state()

        finally:
            self.is_updating = False

    def update_modification_state(self) -> None:
        """Update the visual indication of modification state."""
        is_modified = self.config_model.is_field_modified(self.field_path)

        # Show/hide modification indicator and revert button
        if self.modified_indicator:  # Item 3.1: Check if indicator exists
            self.modified_indicator.setVisible(is_modified)
        if self.revert_button:
            self.revert_button.setVisible(is_modified)

        # Update field border color
        if is_modified:
            if self.input_widget:
                # Revert to simpler border styling for all input widgets, including QCheckBox
                # This ensures the checkmark visibility is not broken by complex indicator styling.
                self.input_widget.setStyleSheet("border: 1px solid orange;") # Thinner border for less intrusion
        else:
            if self.input_widget:
                self.input_widget.setStyleSheet("") # Reset style

    def highlight_search_match(self, is_current: bool = False) -> None:
        """Highlight this field as a search match."""
        self.is_highlighted = True
        if is_current:
            # Current viewed property gets darker blue highlighting on title only
            self.name_label.setStyleSheet(
                "background-color: #cce7ff; border: 2px solid #0066cc; padding: 2px; border-radius: 3px;"
            )
        else:
            # Other matches get lighter blue highlighting on title only
            self.name_label.setStyleSheet(
                "background-color: #e6f3ff; border: 1px solid #007acc; padding: 2px; border-radius: 3px;"
            )

    def clear_search_highlight(self) -> None:
        """Clear search match highlighting."""
        self.is_highlighted = False
        # Clear name label highlighting and restore original font styling
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("")

    def scroll_into_view(self) -> None:
        """Scroll this widget into view in its parent scroll area."""
        # Find the parent scroll area by traversing up the widget hierarchy
        parent = self.parent()
        while parent and not isinstance(parent, QWidget):
            parent = parent.parent()

        if parent:
            # Look for QScrollArea in parent hierarchy
            scroll_area = None
            current = parent
            while current:
                if hasattr(current, "ensureWidgetVisible"):
                    scroll_area = current
                    break
                current = current.parent()

            if scroll_area:
                try:
                    scroll_area.ensureWidgetVisible(self)
                except Exception:
                    # Fallback: scroll to make this widget visible
                    pass

    def get_current_value(self) -> Any:
        """
        Get the current value from the input widget.

        Returns:
            Current value in the widget
        """
        if isinstance(self.input_widget, QCheckBox):
            return self.input_widget.isChecked()
        elif isinstance(self.input_widget, QLineEdit):
            return self.input_widget.text()
        elif isinstance(self.input_widget, QTextEdit):
            return self.input_widget.toPlainText()
        else:
            return None
