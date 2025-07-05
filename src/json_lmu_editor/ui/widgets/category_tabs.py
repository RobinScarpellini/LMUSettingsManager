"""
Category tab widget for organizing configuration fields.

Provides tabbed interface for different configuration categories.
"""

from typing import Dict, List, Optional
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QGridLayout,  # Added QGridLayout
    QSizePolicy, # Added for expanding policies
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics

from ...core.models.configuration_model import ConfigurationModel
from .field_widget import FieldWidget


class MultiRowTabWidget(QWidget):
    """Custom widget that creates multiple rows of tab buttons."""

    # Signals
    field_changed = pyqtSignal(str, object)  # field_path, new_value
    field_reverted = pyqtSignal(str)  # field_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # Configuration model
        self.config_model: Optional[ConfigurationModel] = None

        # Field widgets by path
        self.field_widgets: Dict[str, FieldWidget] = {}

        # Search highlighting
        self.highlighted_fields: List[str] = []
        self.current_search_index = -1  # Track current search result

        # Tab management
        self.tab_buttons: List[QPushButton] = []
        self.tab_widgets: List[QWidget] = []
        self.dx11_tab_indices: List[int] = []
        self.current_tab_index = 0

        # Set the widget's own size policy to expand horizontally
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(sp)

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create tab button area with multiple rows
        self.tab_button_area = QWidget()
        sp_tab_area = self.tab_button_area.sizePolicy()
        sp_tab_area.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.tab_button_area.setSizePolicy(sp_tab_area)
        self.tab_button_layout = QVBoxLayout(self.tab_button_area)
        self.tab_button_layout.setContentsMargins(5, 5, 5, 0)
        self.tab_button_layout.setSpacing(2)

        # Create button group for mutual exclusion
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        self.button_group.buttonClicked.connect(self.on_tab_clicked)

        layout.addWidget(self.tab_button_area)

        # Create content area
        self.content_area = QWidget()
        sp_content_area = self.content_area.sizePolicy()
        sp_content_area.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.content_area.setSizePolicy(sp_content_area)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_area)

    def add_tab_row(self) -> QHBoxLayout:
        """Add a new row for tab buttons."""
        row_widget = QWidget()
        sp_row_widget = row_widget.sizePolicy()
        sp_row_widget.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        row_widget.setSizePolicy(sp_row_widget)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)
        row_layout.addStretch()  # Add stretch at the end to left-align buttons

        self.tab_button_layout.addWidget(row_widget)
        return row_layout

    def on_tab_clicked(self, button: QPushButton) -> None:
        """Handle tab button clicks."""
        tab_index = self.tab_buttons.index(button)
        self.set_current_index(tab_index)

    def set_current_index(self, index: int) -> None:
        """Set the current active tab."""
        self.logger.debug(f"set_current_index called with index: {index}. Total tabs: {len(self.tab_widgets)}")
        if 0 <= index < len(self.tab_widgets):
            self.logger.debug(f"Setting active tab to index {index}, button: '{self.tab_buttons[index].text() if index < len(self.tab_buttons) else 'N/A'}'")
            # Update button states
            for i, button in enumerate(self.tab_buttons):
                button.setChecked(i == index)

            # Hide all tab widgets first
            self.logger.debug(f"Hiding current tab widgets. Content layout children: {self.content_layout.count()}")
            for i_hide, widget_hide in enumerate(self.tab_widgets):
                if widget_hide.parent() == self.content_area: # Check if it's currently in the content_layout
                    self.logger.debug(f"  Hiding and removing widget for tab {i_hide} ('{self.tab_buttons[i_hide].text() if i_hide < len(self.tab_buttons) else 'N/A'}')")
                    widget_hide.hide()
                    self.content_layout.removeWidget(widget_hide) # Important to remove from layout
            
            # Show and add the selected tab widget
            selected_widget = self.tab_widgets[index]
            self.logger.debug(f"Selected widget for tab {index} ('{self.tab_buttons[index].text() if index < len(self.tab_buttons) else 'N/A'}'). Current parent: {selected_widget.parent()}")

            if selected_widget.parent() != self.content_area:
                self.logger.debug("  Setting parent of selected_widget to content_area.")
                selected_widget.setParent(self.content_area) # Ensure parent is correct before adding
            
            # Ensure it's not already in some other layout or a child of a different visible widget
            if selected_widget.parentWidget() and selected_widget.parentWidget() != self.content_area :
                if selected_widget.parentWidget().layout():
                    selected_widget.parentWidget().layout().removeWidget(selected_widget)

            self.logger.debug(f"  Adding selected_widget to content_layout. Content layout children before add: {self.content_layout.count()}")
            self.content_layout.addWidget(selected_widget)
            self.logger.debug(f"  Showing selected_widget. Content layout children after add: {self.content_layout.count()}")
            selected_widget.show()
            self.current_tab_index = index
            self.logger.debug(f"set_current_index finished for index {index}. Current tab index is now {self.current_tab_index}")
        else:
            self.logger.warning(f"set_current_index: Index {index} is out of range for tab_widgets length {len(self.tab_widgets)}.")

    def addTab(self, widget: QWidget, label: str) -> int:
        """Add a tab with the given widget and label."""
        self.logger.debug(f"addTab called for label: '{label}'")
        # Create tab button
        button = QPushButton(label)
        button.setCheckable(True)
        button.setMinimumHeight(24)

        # Set font and ensure text is not elided
        font = QFont()
        font.setPointSize(10)
        button.setFont(font)

        # Calculate button width accounting for both normal and bold text (when selected)
        font_metrics = button.fontMetrics()
        button_text_width = font_metrics.horizontalAdvance(label)

        # Also calculate width with bold font (used when selected)
        bold_font = QFont(font)
        bold_font.setBold(True)
        bold_metrics = QFontMetrics(bold_font)
        bold_text_width = bold_metrics.horizontalAdvance(label)

        # Use the wider of the two measurements
        max_text_width = max(button_text_width, bold_text_width)
        # Add padding: CSS padding (4px*2) + margins + buffer for safety
        button_width = max_text_width + 28  # Extra padding to account for bold text
        button.setMinimumWidth(button_width)
        # button.setMaximumWidth(button_width + 5)  # Removed to allow expansion

        # Debug logging for text width issues
        self.logger.debug(
            f"Tab '{label}': normal_width={button_text_width}, bold_width={bold_text_width}, total_width={button_width}"
        )

        # Style the button
        self._style_tab_button(button, len(self.tab_buttons))

        # Add to button group
        self.button_group.addButton(button)

        # Store tab data
        tab_index = len(self.tab_buttons)
        self.tab_buttons.append(button)
        self.tab_widgets.append(widget)

        # Add button to appropriate row
        self._add_button_to_row(button, tab_index)

        # Set first tab as active
        if tab_index == 0:
            self.logger.debug(f"  Setting first tab '{label}' (index 0) as current.")
            self.set_current_index(0)
        
        self.logger.debug(f"addTab finished for label: '{label}', assigned index: {tab_index}")
        return tab_index

    def _style_tab_button(self, button: QPushButton, tab_index: int) -> None:
        """Apply styling to a tab button."""
        base_style = """
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #cccccc;
                padding: 4px 8px;
                margin-right: 2px;
                text-align: center;
                border-radius: 0px;
            }
            QPushButton:checked {
                background: #ffffff;
                border-bottom: 2px solid #007acc;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e8e8e8;
            }
        """
        button.setStyleSheet(base_style)

    def _add_button_to_row(self, button: QPushButton, tab_index: int) -> None:
        """Add button to appropriate row, creating new rows as needed."""
        # Calculate which row this button should go in (max 10 tabs per row with compact buttons)
        tabs_per_row = 10
        row_index = tab_index // tabs_per_row

        # Ensure we have enough rows
        while self.tab_button_layout.count() <= row_index:
            self.add_tab_row()

        # Get the row layout
        row_widget = self.tab_button_layout.itemAt(row_index).widget()
        row_layout = row_widget.layout()

        # Insert button before the stretch
        row_layout.insertWidget(row_layout.count() - 1, button)

    def count(self) -> int:
        """Return the number of tabs."""
        return len(self.tab_widgets)

    def tabText(self, index: int) -> str:
        """Return the text of the tab at the given index."""
        if 0 <= index < len(self.tab_buttons):
            return self.tab_buttons[index].text()
        return ""

    def currentIndex(self) -> int:
        """Return the index of the current tab."""
        return self.current_tab_index

    def setCurrentIndex(self, index: int) -> None:
        """Set the current tab by index."""
        self.set_current_index(index)

    def clear(self) -> None:
        """Clear all tabs."""
        self.logger.debug(f"clear called. Current tab count: {len(self.tab_widgets)}")

        # 1. Remove and delete current content from content_area
        # Check if current_tab_index is valid and there's a widget to remove
        if 0 <= self.current_tab_index < len(self.tab_widgets) :
            current_content_widget = self.tab_widgets[self.current_tab_index]
            if current_content_widget and current_content_widget.parent() == self.content_area:
                self.logger.debug(f"  Hiding and removing current content widget for tab {self.current_tab_index} ('{self.tab_buttons[self.current_tab_index].text() if self.current_tab_index < len(self.tab_buttons) else 'N/A'}') from content_layout.")
                current_content_widget.hide()
                self.content_layout.removeWidget(current_content_widget)
                # current_content_widget.setParent(None) # Explicitly unparent before deleteLater
        
        # 2. Delete all tab content widgets (QScrollArea and its contents)
        self.logger.debug(f"  Deleting {len(self.tab_widgets)} tab content widgets.")
        for i, widget in enumerate(self.tab_widgets):
            self.logger.debug(f"    Deleting content widget for tab {i} ('{self.tab_buttons[i].text() if i < len(self.tab_buttons) else 'N/A'}')")
            widget.deleteLater()
        self.tab_widgets.clear()

        # 3. Remove all buttons from button group and delete them
        self.logger.debug(f"  Removing and deleting {len(self.tab_buttons)} tab buttons.")
        for button in self.tab_buttons:
            self.logger.debug(f"    Removing and deleting button: {button.text()}")
            self.button_group.removeButton(button)
            button.deleteLater()
        self.tab_buttons.clear()

        # 4. Clear the QHBoxLayouts (rows) from the QVBoxLayout (tab_button_layout)
        #    and delete the QWidget rows themselves.
        self.logger.debug(f"  Clearing tab button rows from tab_button_layout. Row count: {self.tab_button_layout.count()}")
        while self.tab_button_layout.count() > 0:
            item = self.tab_button_layout.takeAt(0) # Remove item from layout
            if item:
                widget = item.widget()
                if widget:
                    self.logger.debug(f"    Deleting tab button row widget: {widget}")
                    widget.deleteLater() # Delete the QWidget that holds a row of buttons
        
        # Reset other state
        self.dx11_tab_indices.clear()
        self.current_tab_index = -1 # No tab selected
        self.logger.debug("clear finished. All tab structures reset.")


class CategoryTabWidget(MultiRowTabWidget):
    """Tab widget for organizing configuration fields by category with multi-row support."""

    def __init__(self, parent=None):
        """Initialize the category tab widget."""
        super().__init__(parent)

        # Additional initialization if needed
        pass

    def populate_categories(
        self, categories: Dict[str, List[str]], config_model: ConfigurationModel
    ) -> None:
        """
        Populate tabs with configuration categories.

        Args:
            categories: Dictionary mapping category names to field lists
            config_model: Configuration model containing field data
        """
        self.config_model = config_model

        # Clear existing tabs
        self.clear()
        self.field_widgets.clear()

        # Separate JSON and DX11 categories, and identify small categories
        large_json_categories = {}
        small_categories = {}
        dx11_fields = []
        misc_fields = []

        for category_name, field_paths in categories.items():
            if field_paths:  # Only process categories with fields
                if "DX11" in category_name:
                    dx11_fields.extend(field_paths)
                else:
                    # Check if category has fewer than 9 fields
                    if len(field_paths) < 9:
                        small_categories[category_name] = field_paths
                        misc_fields.extend(field_paths)
                    else:
                        large_json_categories[category_name] = field_paths

        # Add large JSON category tabs
        for category_name, field_paths in large_json_categories.items():
            tab_widget = self.create_category_tab(category_name, field_paths)
            display_name = self._format_tab_name(category_name)
            self.addTab(tab_widget, display_name)

        # Add Misc tab if there are small categories
        if misc_fields:
            misc_tab_widget = self.create_misc_tab(
                small_categories
            )  # Removed all_misc_fields
            self.addTab(misc_tab_widget, "Misc")

        # Add single DX11 tab if there are DX11 fields
        if dx11_fields:
            dx11_tab_widget = self.create_category_tab(
                "DX11 - Config_DX11.ini", dx11_fields
            )
            tab_index = self.addTab(dx11_tab_widget, "Config_DX11.ini")
            self.dx11_tab_indices.append(tab_index)
            self._apply_dx11_button_styling(tab_index)

        tab_count = (
            len(large_json_categories)
            + (1 if misc_fields else 0)
            + (1 if dx11_fields else 0)
        )
        self.logger.info(
            f"Populated {tab_count} category tabs with {len(self.field_widgets)} field widgets"
        )
        self.logger.info(
            f"Misc tab contains {len(small_categories)} small categories with {len(misc_fields)} fields"
        )
        
        # Ensure first tab is selected if any tabs were added
        if self.count() > 0 and self.currentIndex() == -1:
            self.logger.info(f"Setting current index to 0 after populating {self.count()} tabs.")
            self.setCurrentIndex(0)
        elif self.count() == 0:
            self.logger.info("No tabs were populated.")

        # Debug: Show field widget distribution
        if self.logger.isEnabledFor(logging.DEBUG):
            field_count_by_tab = {}
            for field_path in self.field_widgets.keys():
                field_info = self.config_model.get_field_info(field_path)
                if field_info:
                    category = field_info.category
                    if "DX11" in category:
                        tab_name = "Config_DX11.ini"
                    elif (
                        len(
                            [
                                f
                                for cat, f_list in categories.items()
                                if cat == category
                                for f in f_list
                            ]
                        )
                        < 9
                    ):
                        tab_name = "Misc"
                    else:
                        tab_name = self._format_tab_name(category)
                    field_count_by_tab[tab_name] = (
                        field_count_by_tab.get(tab_name, 0) + 1
                    )

            for tab_name, count in field_count_by_tab.items():
                self.logger.debug(f"  Tab '{tab_name}': {count} field widgets")

    def _format_tab_name(self, category_name: str) -> str:
        """
        Format category name for tab display.

        Args:
            category_name: Original category name

        Returns:
            Formatted tab name in PascalCase without prefixes
        """
        # Remove prefixes
        display_name = category_name
        if display_name.startswith("JSON - "):
            display_name = display_name[7:]  # Remove "JSON - "
        elif display_name.startswith("DX11 - "):
            display_name = display_name[7:]  # Remove "DX11 - "

        # Convert to PascalCase
        words = display_name.replace("_", " ").replace("-", " ").split()
        pascal_case = "".join(word.capitalize() for word in words)

        return pascal_case

    def _apply_dx11_button_styling(self, tab_index: int) -> None:
        """Apply soft yellowish styling to a DX11 tab button."""
        if tab_index < len(self.tab_buttons):
            button = self.tab_buttons[tab_index]
            dx11_style = """
                QPushButton {
                    background: #fefdf5;
                    border: 1px solid #e6e0b8;
                    padding: 4px 8px;
                    margin-right: 2px;
                    text-align: center;
                    color: #333;
                    border-radius: 0px;
                }
                QPushButton:checked {
                    background: #fcf9e8;
                    border-bottom: 2px solid #d4a017;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #fbf7e3;
                }
            """
            button.setStyleSheet(dx11_style)

    def create_misc_tab(self, small_categories: Dict[str, List[str]]) -> QWidget:
        """
        Create a special Misc tab that groups small categories with headers.

        Args:
            small_categories: Dictionary of small categories and their fields

        Returns:
            Widget for the Misc tab
        """
        # Main tab widget
        tab_widget = QWidget()
        sp_tab_widget_misc = tab_widget.sizePolicy()
        sp_tab_widget_misc.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        tab_widget.setSizePolicy(sp_tab_widget_misc)
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Scroll area for fields
        scroll_area = QScrollArea()
        sp_scroll_misc = scroll_area.sizePolicy()
        sp_scroll_misc.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        scroll_area.setSizePolicy(sp_scroll_misc)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget for scroll area
        content_widget = QWidget()
        sp_content_misc = content_widget.sizePolicy()
        sp_content_misc.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        content_widget.setSizePolicy(sp_content_misc)
        # Main layout for the Misc tab content (holds headers and grids)
        main_misc_layout = QVBoxLayout(content_widget)
        main_misc_layout.setContentsMargins(5, 5, 5, 5) # Reduced margins
        main_misc_layout.setSpacing(8)

        total_field_count = 0
        num_columns = 2

        for category_name, field_paths in small_categories.items():
            # Add category header
            # Clean specific prefixes/suffixes from the original category_name first
            cleaned_category_name = category_name
            if cleaned_category_name.startswith("JSON - "):
                cleaned_category_name = cleaned_category_name[7:]
            
            known_prefixes_suffixes = {
                "UI Gamepad Mouse - ": "",
                " In Packages Directory": ""
                # Add other known full prefixes/suffixes here if they appear before PascalCase conversion
            }
            for text_to_remove, replacement in known_prefixes_suffixes.items():
                if text_to_remove in cleaned_category_name:
                    cleaned_category_name = cleaned_category_name.replace(text_to_remove, replacement)

            # Then format the cleaned name (e.g., to PascalCase)
            display_header_name = self._format_tab_name(cleaned_category_name.strip())

            header_label = QLabel(display_header_name)
            header_font = QFont()
            header_font.setBold(True)
            header_font.setPointSize(11) # Slightly smaller for Misc headers
            header_label.setFont(header_font)
            header_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    background-color: #ecf0f1;
                    padding: 8px;
                    border-left: 4px solid #3498db;
                    margin-top: 10px;
                    margin-bottom: 5px;
                }
            """)
            main_misc_layout.addWidget(header_label)

            # Create a QGridLayout for fields under this specific header
            fields_grid_layout = QGridLayout()
            fields_grid_layout.setHorizontalSpacing(5)
            fields_grid_layout.setVerticalSpacing(2) # Reduced vertical spacing

            # Set column stretch for a 50/50 split within this sub-grid
            # num_columns is already defined as 2 earlier in the class or could be passed
            for i in range(num_columns):
                fields_grid_layout.setColumnStretch(i, 1)

            row, col = 0, 0
            fields_in_this_category_count = 0
            for field_path in field_paths:
                field_info = self.config_model.get_field_info(field_path)
                if field_info:
                    try:
                        field_widget = FieldWidget(
                            field_path, field_info, self.config_model
                        )

                        field_widget.value_changed.connect(self.on_field_changed)
                        field_widget.revert_requested.connect(self.on_field_reverted)

                        self.field_widgets[field_path] = field_widget

                        fields_grid_layout.addWidget(field_widget, row, col)
                        total_field_count += 1
                        fields_in_this_category_count += 1

                        col += 1
                        if col >= num_columns:
                            col = 0
                            row += 1

                    except Exception as e:
                        self.logger.error(
                            f"Error creating field widget for {field_path}: {e}"
                        )
                else:
                    self.logger.warning(f"No field info found for {field_path}")

            # Add vertical stretch within this category's grid
            if fields_in_this_category_count > 0:
                fields_grid_layout.setRowStretch(row + 1, 1)
            else:  # If no fields in this sub-category, still add a stretch to prevent collapse
                fields_grid_layout.setRowStretch(0, 1)

            main_misc_layout.addLayout(
                fields_grid_layout
            )  # Add the grid for this category

        # Add overall stretch to push all content to top
        main_misc_layout.addStretch(1)

        # Set content widget
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Add category info label
        info_label = QLabel(
            f"{total_field_count} settings from {len(small_categories)} categories"
        )
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)

        self.logger.debug(
            f"Created Misc tab with {total_field_count} field widgets from {len(small_categories)} categories"
        )
        # Log the main QVBoxLayout for the Misc tab
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("--- CategoryTabs Misc Tab Main Layout Debug ---")
            self.logger.debug(f"  MiscMainLayout: type={type(main_misc_layout)}")
            cm = main_misc_layout.contentsMargins()
            self.logger.debug(f"    contentsMargins=(L:{cm.left()}, T:{cm.top()}, R:{cm.right()}, B:{cm.bottom()})")
            self.logger.debug(f"    spacing={main_misc_layout.spacing()}")
            self.logger.debug("--- End Misc Tab Main Layout Debug ---")

            # Iterate through items in main_misc_layout to find and log sub-QGridLayouts
            for i in range(main_misc_layout.count()):
                item = main_misc_layout.itemAt(i)
                if item is None:
                    continue
                
                # Check if the item is a layout itself (QGridLayouts are added as sub-layouts)
                sub_layout = item.layout()
                if sub_layout and isinstance(sub_layout, QGridLayout):
                    # Try to get a more descriptive name if possible, e.g., from a preceding QLabel
                    header_text = f"SubGrid {i}"
                    if i > 0: # Check if there's a QLabel header before this grid
                        prev_item = main_misc_layout.itemAt(i-1)
                        if prev_item and prev_item.widget() and isinstance(prev_item.widget(), QLabel):
                            header_text = f"SubGrid for '{prev_item.widget().text()}'"
                    self._log_grid_layout_details(sub_layout, f"Misc Tab - {header_text}")

        return tab_widget

    def create_category_tab(
        self, category_name: str, field_paths: List[str]
    ) -> QWidget:
        """
        Create a tab widget for a category.

        Args:
            category_name: Name of the category
            field_paths: List of field paths in this category

        Returns:
            Widget for the tab
        """
        # Main tab widget
        tab_widget = QWidget()
        sp_tab_widget_cat = tab_widget.sizePolicy()
        sp_tab_widget_cat.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        tab_widget.setSizePolicy(sp_tab_widget_cat)
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Scroll area for fields
        scroll_area = QScrollArea()
        sp_scroll_cat = scroll_area.sizePolicy()
        sp_scroll_cat.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        scroll_area.setSizePolicy(sp_scroll_cat)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget for scroll area
        content_widget = QWidget()
        sp_content_cat = content_widget.sizePolicy()
        sp_content_cat.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        content_widget.setSizePolicy(sp_content_cat)
        # Use QGridLayout for two-column layout
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5) # Reduced margins
        content_layout.setHorizontalSpacing(5)
        content_layout.setVerticalSpacing(2) # Reduced vertical spacing

        # Set column stretch for a 50/50 split
        num_columns = 2  # Already defined below, but good to have here for clarity
        for i in range(num_columns):
            content_layout.setColumnStretch(i, 1)

        # Add field widgets to the grid
        field_count = 0
        row, col = 0, 0
        num_columns = 2

        for field_path in field_paths:
            field_info = self.config_model.get_field_info(field_path)
            if field_info:
                try:
                    field_widget = FieldWidget(
                        field_path, field_info, self.config_model
                    )

                    # Connect signals
                    field_widget.value_changed.connect(self.on_field_changed)
                    field_widget.revert_requested.connect(self.on_field_reverted)

                    # Store reference
                    self.field_widgets[field_path] = field_widget

                    # Add to grid layout
                    content_layout.addWidget(field_widget, row, col)
                    field_count += 1

                    # Update row and column for next widget
                    col += 1
                    if col >= num_columns:
                        col = 0
                        row += 1

                except Exception as e:
                    self.logger.error(
                        f"Error creating field widget for {field_path}: {e}"
                    )
            else:
                self.logger.warning(f"No field info found for {field_path}")

        # Add vertical stretch to push fields to top
        if field_count > 0:  # Only add stretch if there are fields
            content_layout.setRowStretch(
                row + 1, 1
            )  # Stretch below the last row of items
        else:  # If no fields, still add a stretch to prevent collapse
            content_layout.setRowStretch(0, 1)

        # Set content widget
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Add category info label
        info_label = QLabel(f"{field_count} settings")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)

        self.logger.debug(
            f"Created tab '{category_name}' with {field_count} field widgets"
        )
        self._log_grid_layout_details(content_layout, category_name)

        return tab_widget

    def on_field_changed(self, field_path: str, new_value: object) -> None:
        """
        Handle field value changes.

        Args:
            field_path: Path of the changed field
            new_value: New field value
        """
        if self.config_model:
            self.config_model.set_field_value(field_path, new_value)

        # Emit signal
        self.field_changed.emit(field_path, new_value)

    def on_field_reverted(self, field_path: str) -> None:
        """
        Handle field revert requests.

        Args:
            field_path: Path of the field to revert
        """
        if self.config_model:
            if self.config_model.revert_field(field_path):
                # Update the field widget
                field_widget = self.field_widgets.get(field_path)
                if field_widget:
                    field_widget.refresh_from_model()

        # Emit signal
        self.field_reverted.emit(field_path)

    def highlight_search_results(self, results: List[str]) -> None:
        """
        Highlight search results across all tabs.

        Args:
            results: List of field paths to highlight
        """
        # Clear previous highlights
        self.clear_search_results()

        self.highlighted_fields = results

        # Count how many results we can actually highlight
        highlighted_count = 0
        missing_count = 0

        # Highlight matching fields
        for i, field_path in enumerate(results):
            field_widget = self.field_widgets.get(field_path)
            if field_widget:
                # First result is considered current
                is_current = i == 0
                field_widget.highlight_search_match(is_current)
                highlighted_count += 1
            else:
                missing_count += 1

        self.logger.info(
            f"Search results: {len(results)} total, {highlighted_count} highlighted, {missing_count} widgets not found"
        )

        if missing_count > 0:
            self.logger.warning(
                f"Missing field widgets for {missing_count}/{len(results)} search results"
            )
            self.logger.warning(
                f"Total field widgets stored: {len(self.field_widgets)}"
            )

            # Log first few missing results and categorize by expected tab
            for i, field_path in enumerate(results):
                if not self.field_widgets.get(field_path):
                    # Determine which tab this field should be in
                    expected_tab = "Unknown"
                    if self.config_model:
                        field_info = self.config_model.get_field_info(field_path)
                        if field_info:
                            category = field_info.category
                            if "DX11" in category:
                                expected_tab = "Config_DX11.ini"
                            else:
                                # Check if small category (Misc tab)
                                all_categories = self.config_model.get_categories()
                                category_size = len(all_categories.get(category, []))
                                if category_size < 8:
                                    expected_tab = "Misc"
                                else:
                                    expected_tab = self._format_tab_name(category)

                    self.logger.warning(
                        f"  Missing widget: {field_path} (expected in '{expected_tab}' tab)"
                    )
                    if i >= 10:  # Log first 10 missing instead of 5
                        break

        # Set current index and switch to first result's tab if results exist
        if results:
            self.current_search_index = 0
            self.navigate_to_current_result()

    def clear_search_results(self) -> None:
        """Clear search result highlighting."""
        for field_path in self.highlighted_fields:
            field_widget = self.field_widgets.get(field_path)
            if field_widget:
                field_widget.clear_search_highlight()

        self.highlighted_fields.clear()
        self.current_search_index = -1

    def navigate_to_current_result(self) -> None:
        """Navigate to the current search result."""
        if self.highlighted_fields and 0 <= self.current_search_index < len(
            self.highlighted_fields
        ):
            current_result = self.highlighted_fields[self.current_search_index]

            self.logger.debug(
                f"Navigating to result {self.current_search_index + 1}/{len(self.highlighted_fields)}: {current_result}"
            )

            # Update highlighting to show current result
            for i, field_path in enumerate(self.highlighted_fields):
                field_widget = self.field_widgets.get(field_path)
                if field_widget:
                    is_current = i == self.current_search_index
                    field_widget.highlight_search_match(is_current)

            self.switch_to_field_tab(current_result)
            # Scroll to the field if possible
            field_widget = self.field_widgets.get(current_result)
            if field_widget:
                field_widget.scroll_into_view()
            else:
                self.logger.warning(
                    f"Cannot scroll to field, widget not found: {current_result}"
                )

    def navigate_to_next_result(self) -> bool:
        """
        Navigate to the next search result.

        Returns:
            True if navigation was successful, False otherwise
        """
        if not self.highlighted_fields:
            return False

        self.current_search_index = (self.current_search_index + 1) % len(
            self.highlighted_fields
        )
        self.navigate_to_current_result()
        return True

    def navigate_to_previous_result(self) -> bool:
        """
        Navigate to the previous search result.

        Returns:
            True if navigation was successful, False otherwise
        """
        if not self.highlighted_fields:
            return False

        self.current_search_index = (self.current_search_index - 1) % len(
            self.highlighted_fields
        )
        self.navigate_to_current_result()
        return True

    def get_current_search_position(self) -> tuple:
        """
        Get the current search position.

        Returns:
            Tuple of (current_index + 1, total_results)
        """
        if not self.highlighted_fields:
            return (0, 0)
        return (self.current_search_index + 1, len(self.highlighted_fields))

    def switch_to_field_tab(self, field_path: str) -> None:
        """
        Switch to the tab containing the specified field.

        Args:
            field_path: Path of the field to navigate to
        """
        if not self.config_model:
            return

        # Get field info to determine category
        field_info = self.config_model.get_field_info(field_path)
        if not field_info:
            return

        category = field_info.category

        # Check if this is a DX11 field
        if "DX11" in category:
            target_tab_name = "Config_DX11.ini"
        else:
            # Check if this field belongs to a small category (< 8 fields) that would be in Misc
            all_categories = self.config_model.get_categories()
            original_category_fields = []

            for cat_name, field_list in all_categories.items():
                # Handle category name prefixes (e.g., "JSON - Graphic Options" vs "Graphic Options")
                if cat_name == category or cat_name == f"JSON - {category}":
                    original_category_fields = field_list
                    break

            # If the category has fewer than 9 fields, it goes to Misc tab
            if len(original_category_fields) < 9:
                target_tab_name = "Misc"
            else:
                # Convert category to the same format as tab names (PascalCase without prefixes)
                target_tab_name = self._format_tab_name(category)

        # Find tab with matching category
        self.logger.debug(
            f"Looking for tab '{target_tab_name}' for field '{field_path}' in category '{category}'"
        )
        for i in range(self.count()):
            tab_text = self.tabText(i)
            self.logger.debug(f"  Tab {i}: '{tab_text}'")
            if tab_text == target_tab_name:
                self.logger.debug(f"  -> Switching to tab {i}: '{tab_text}'")
                self.setCurrentIndex(i)

                # Scroll to the field
                field_widget = self.field_widgets.get(field_path)
                if field_widget:
                    field_widget.scroll_into_view()
                return

        self.logger.warning(
            f"Could not find tab '{target_tab_name}' for field '{field_path}'"
        )

    def refresh_all_fields(self) -> None:
        """Refresh all field widgets from the model."""
        for field_widget in self.field_widgets.values():
            field_widget.refresh_from_model()

    def get_current_category(self) -> str:
        """
        Get the name of the currently selected category.

        Returns:
            Current category name
        """
        current_index = self.currentIndex()
        if current_index >= 0:
            return self.tabText(current_index)
        return ""

    def get_field_widget(self, field_path: str) -> Optional[FieldWidget]:
        """
        Get the field widget for a specific field path.

        Args:
            field_path: Path of the field

        Returns:
            FieldWidget instance or None if not found
        """
        return self.field_widgets.get(field_path)

    def _log_grid_layout_details(self, grid_layout: QGridLayout, layout_name: str):
        """Logs detailed QGridLayout information for debugging."""
        if not self.logger.isEnabledFor(logging.DEBUG) or not isinstance(grid_layout, QGridLayout):
            if not isinstance(grid_layout, QGridLayout):
                self.logger.warning(f"Attempted to log non-QGridLayout as grid: {layout_name}, type: {type(grid_layout)}")
            return

        self.logger.debug(f"--- CategoryTabs Grid Debug: Layout='{layout_name}' ---")
        self.logger.debug(f"  GridLayout: type={type(grid_layout)}")
        cm = grid_layout.contentsMargins()
        self.logger.debug(f"    contentsMargins=(L:{cm.left()}, T:{cm.top()}, R:{cm.right()}, B:{cm.bottom()})")
        self.logger.debug(f"    horizontalSpacing={grid_layout.horizontalSpacing()}, verticalSpacing={grid_layout.verticalSpacing()}")
        self.logger.debug(f"    rowCount={grid_layout.rowCount()}, columnCount={grid_layout.columnCount()}")

        for r in range(grid_layout.rowCount()):
            self.logger.debug(f"    Row {r}: rowStretch={grid_layout.rowStretch(r)}, rowMinimumHeight={grid_layout.rowMinimumHeight(r)}")
        for c in range(grid_layout.columnCount()):
            self.logger.debug(f"    Col {c}: columnStretch={grid_layout.columnStretch(c)}, columnMinimumWidth={grid_layout.columnMinimumWidth(c)}")

        # Log info about some child widgets (FieldWidgets)
        items_to_log = min(grid_layout.count(), 5) # Log first few items
        self.logger.debug(f"  Logging details for up to {items_to_log} child items in '{layout_name}':")
        for i in range(grid_layout.count()): # Iterate all to find widgets, but log details for first few
            item = grid_layout.itemAt(i)
            if item is None:
                continue
            
            widget = item.widget()
            if widget and isinstance(widget, FieldWidget):
                if i < items_to_log: # Only log details for the first few FieldWidgets
                    self.logger.debug(f"    Child {i} (FieldWidget): path='{widget.field_path}'")
                    # Geometry is often (0,0,0,0) or incorrect if logged before widget is shown and parent layout is finalized.
                    # if widget.isVisibleTo(self): # Check visibility relative to CategoryTabWidget
                    #      self.logger.debug(f"      geometry={widget.geometry()}, size={widget.size()}")
                    # else:
                    #      self.logger.debug(f"      Not (yet) fully visible, geometry/size might be inaccurate.")
                    self.logger.debug(f"      sizeHint={widget.sizeHint()}, minimumSizeHint={widget.minimumSizeHint()}")
            elif widget and i < items_to_log: # Log other types of widgets if among first few
                self.logger.debug(f"    Child {i}: type={type(widget)}, objectName='{widget.objectName()}', sizeHint={widget.sizeHint()}")
            elif item.spacerItem() and i < items_to_log:
                 self.logger.debug(f"    Child {i} (QSpacerItem): sizeHint={item.spacerItem().sizeHint()}")


        self.logger.debug(f"--- End CategoryTabs Grid Debug: Layout='{layout_name}' ---")
