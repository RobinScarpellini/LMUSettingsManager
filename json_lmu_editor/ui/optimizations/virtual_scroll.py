"""
Virtual scrolling implementation for large lists of configuration fields.

Provides smooth scrolling performance by only rendering visible items.
"""

import math
from typing import List, Optional, Callable, Any, Dict
import logging

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class VirtualItem:
    """Represents an item in the virtual list."""

    def __init__(self, data: Any, height: int = 50):
        self.data = data
        self.height = height
        self.widget: Optional[QWidget] = None
        self.is_visible = False
        self.y_position = 0


class ItemPool:
    """Pool of reusable widgets for virtual scrolling."""

    def __init__(
        self, widget_factory: Callable[[Any], QWidget], initial_size: int = 10
    ):
        """
        Initialize the item pool.

        Args:
            widget_factory: Function to create widgets
            initial_size: Initial pool size
        """
        self.widget_factory = widget_factory
        self.available_widgets: List[QWidget] = []
        self.used_widgets: Dict[int, QWidget] = {}  # index -> widget
        self.logger = logging.getLogger(__name__)

        # Pre-create initial widgets
        for _ in range(initial_size):
            widget = self.widget_factory(None)
            widget.hide()
            self.available_widgets.append(widget)

    def get_widget(self, index: int, data: Any) -> QWidget:
        """
        Get a widget for the given index and data.

        Args:
            index: Item index
            data: Item data

        Returns:
            Widget instance
        """
        if index in self.used_widgets:
            widget = self.used_widgets[index]
        else:
            # Get widget from pool or create new one
            if self.available_widgets:
                widget = self.available_widgets.pop()
            else:
                widget = self.widget_factory(data)

            self.used_widgets[index] = widget

        # Update widget with data
        if hasattr(widget, "update_data"):
            widget.update_data(data)

        return widget

    def return_widget(self, index: int) -> None:
        """
        Return a widget to the pool.

        Args:
            index: Item index
        """
        if index in self.used_widgets:
            widget = self.used_widgets[index]
            widget.hide()
            widget.setParent(None)

            self.available_widgets.append(widget)
            del self.used_widgets[index]

    def clear(self) -> None:
        """Clear all widgets from the pool."""
        # Return all used widgets
        for index in list(self.used_widgets.keys()):
            self.return_widget(index)

        # Delete all widgets
        for widget in self.available_widgets:
            widget.deleteLater()

        self.available_widgets.clear()


class VirtualScrollArea(QScrollArea):
    """
    Virtual scrolling area that only renders visible items.

    Provides smooth scrolling performance for large lists.
    """

    # Signals
    item_clicked = pyqtSignal(int, object)  # index, data
    item_double_clicked = pyqtSignal(int, object)  # index, data
    selection_changed = pyqtSignal(int)  # selected_index

    def __init__(self, widget_factory: Callable[[Any], QWidget], parent=None):
        """
        Initialize the virtual scroll area.

        Args:
            widget_factory: Function to create widgets for items
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.widget_factory = widget_factory

        # Virtual list state
        self.items: List[VirtualItem] = []
        self.item_height = 50  # Default item height
        self.visible_range = (0, 0)  # (start_index, end_index)
        self.selected_index = -1

        # Widget pool for recycling
        self.item_pool = ItemPool(widget_factory)

        # Viewport and content
        self.content_widget = QFrame()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Set up scroll area
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Performance settings
        self.viewport_margin = 5  # Extra items to render outside viewport
        self.update_threshold = 10  # Minimum scroll distance before update

        # Update timer to avoid excessive updates
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._delayed_update_visible_items)

        # Connect scroll events
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # Initial setup
        self._setup_spacers()

    def set_items(self, items: List[Any], item_height: int = None) -> None:
        """
        Set the items to display in the virtual list.

        Args:
            items: List of item data
            item_height: Height of each item (uses default if None)
        """
        if item_height is not None:
            self.item_height = item_height

        # Clear current items
        self.clear_items()

        # Create virtual items
        self.items = []
        y_pos = 0
        for data in items:
            virtual_item = VirtualItem(data, self.item_height)
            virtual_item.y_position = y_pos
            self.items.append(virtual_item)
            y_pos += self.item_height

        # Update content height
        total_height = len(self.items) * self.item_height
        self.content_widget.setMinimumHeight(total_height)

        # Update visible items
        self._update_visible_items()

        self.logger.debug(f"Set {len(items)} items with height {self.item_height}")

    def add_item(self, data: Any, index: int = -1) -> None:
        """
        Add an item to the virtual list.

        Args:
            data: Item data
            index: Position to insert (-1 for append)
        """
        virtual_item = VirtualItem(data, self.item_height)

        if index == -1 or index >= len(self.items):
            # Append
            virtual_item.y_position = len(self.items) * self.item_height
            self.items.append(virtual_item)
        else:
            # Insert at position
            self.items.insert(index, virtual_item)
            # Update positions for all items after insertion
            self._recalculate_positions()

        # Update content height
        total_height = len(self.items) * self.item_height
        self.content_widget.setMinimumHeight(total_height)

        # Update visible items
        self._update_visible_items()

    def remove_item(self, index: int) -> bool:
        """
        Remove an item from the virtual list.

        Args:
            index: Index to remove

        Returns:
            True if removed successfully
        """
        if 0 <= index < len(self.items):
            # Return widget to pool if it's visible
            if index in self.item_pool.used_widgets:
                self.item_pool.return_widget(index)

            # Remove item
            self.items.pop(index)

            # Update positions
            self._recalculate_positions()

            # Update content height
            total_height = len(self.items) * self.item_height
            self.content_widget.setMinimumHeight(total_height)

            # Update selection
            if self.selected_index == index:
                self.selected_index = -1
            elif self.selected_index > index:
                self.selected_index -= 1

            # Update visible items
            self._update_visible_items()

            return True

        return False

    def clear_items(self) -> None:
        """Clear all items from the virtual list."""
        # Return all widgets to pool
        self.item_pool.clear()

        # Clear items
        self.items.clear()
        self.selected_index = -1
        self.visible_range = (0, 0)

        # Reset content height
        self.content_widget.setMinimumHeight(0)

        self.logger.debug("Cleared all items")

    def scroll_to_item(self, index: int) -> None:
        """
        Scroll to make the specified item visible.

        Args:
            index: Item index to scroll to
        """
        if 0 <= index < len(self.items):
            item = self.items[index]
            y_position = item.y_position

            # Calculate scroll position to center the item
            viewport_height = self.viewport().height()
            scroll_pos = max(0, y_position - viewport_height // 2)

            self.verticalScrollBar().setValue(scroll_pos)

    def get_selected_item(self) -> Optional[Any]:
        """
        Get the currently selected item data.

        Returns:
            Selected item data or None
        """
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index].data
        return None

    def set_selected_index(self, index: int) -> None:
        """
        Set the selected item index.

        Args:
            index: Index to select (-1 for no selection)
        """
        if index != self.selected_index:
            old_index = self.selected_index
            self.selected_index = index

            # Update visual selection
            self._update_item_selection(old_index)
            self._update_item_selection(index)

            self.selection_changed.emit(index)

    def _setup_spacers(self) -> None:
        """Set up spacer widgets for virtual scrolling."""
        # Top spacer
        self.top_spacer = QWidget()
        self.top_spacer.setFixedHeight(0)
        self.content_layout.addWidget(self.top_spacer)

        # Visible items container
        self.visible_container = QWidget()
        self.visible_layout = QVBoxLayout(self.visible_container)
        self.visible_layout.setContentsMargins(0, 0, 0, 0)
        self.visible_layout.setSpacing(0)
        self.content_layout.addWidget(self.visible_container)

        # Bottom spacer
        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(0)
        self.content_layout.addWidget(self.bottom_spacer)

    def _on_scroll(self, value: int) -> None:
        """Handle scroll bar value changes."""
        # Use timer to avoid excessive updates during scrolling
        self.update_timer.start(16)  # ~60 FPS

    def _delayed_update_visible_items(self) -> None:
        """Update visible items after scroll delay."""
        self._update_visible_items()

    def _update_visible_items(self) -> None:
        """Update which items are visible and rendered."""
        if not self.items:
            return

        # Calculate visible range
        viewport_rect = self.viewport().rect()
        scroll_offset = self.verticalScrollBar().value()

        # Determine which items should be visible
        start_y = scroll_offset - (self.viewport_margin * self.item_height)
        end_y = (
            scroll_offset
            + viewport_rect.height()
            + (self.viewport_margin * self.item_height)
        )

        start_index = max(0, int(start_y // self.item_height))
        end_index = min(len(self.items), int(math.ceil(end_y / self.item_height)))

        new_visible_range = (start_index, end_index)

        # Only update if range changed significantly
        if new_visible_range != self.visible_range:
            self._render_visible_range(new_visible_range)
            self.visible_range = new_visible_range

    def _render_visible_range(self, visible_range: tuple) -> None:
        """
        Render items in the visible range.

        Args:
            visible_range: (start_index, end_index) tuple
        """
        start_index, end_index = visible_range

        # Return widgets that are no longer visible
        for i in list(self.item_pool.used_widgets.keys()):
            if i < start_index or i >= end_index:
                self.item_pool.return_widget(i)

        # Clear visible layout
        while self.visible_layout.count():
            child = self.visible_layout.takeAt(0)
            if child.widget():
                child.widget().hide()

        # Calculate spacer heights
        top_spacer_height = start_index * self.item_height
        bottom_spacer_height = (len(self.items) - end_index) * self.item_height

        self.top_spacer.setFixedHeight(top_spacer_height)
        self.bottom_spacer.setFixedHeight(bottom_spacer_height)

        # Render visible items
        for i in range(start_index, end_index):
            if i < len(self.items):
                item = self.items[i]
                widget = self.item_pool.get_widget(i, item.data)

                # Update widget selection state
                self._update_widget_selection_state(widget, i == self.selected_index)

                # Add to layout
                widget.show()
                self.visible_layout.addWidget(widget)

        self.logger.debug(f"Rendered items {start_index}-{end_index}")

    def _recalculate_positions(self) -> None:
        """Recalculate Y positions for all items."""
        y_pos = 0
        for item in self.items:
            item.y_position = y_pos
            y_pos += item.height

    def _update_item_selection(self, index: int) -> None:
        """Update selection state for a specific item."""
        if index in self.item_pool.used_widgets:
            widget = self.item_pool.used_widgets[index]
            self._update_widget_selection_state(widget, index == self.selected_index)

    def _update_widget_selection_state(self, widget: QWidget, selected: bool) -> None:
        """Update the selection state of a widget."""
        if hasattr(widget, "set_selected"):
            widget.set_selected(selected)
        else:
            # Default selection styling
            if selected:
                widget.setStyleSheet("background-color: #0078d4; color: white;")
            else:
                widget.setStyleSheet("")

    def get_item_count(self) -> int:
        """Get the total number of items."""
        return len(self.items)

    def get_visible_range(self) -> tuple:
        """Get the currently visible item range."""
        return self.visible_range

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        visible_count = self.visible_range[1] - self.visible_range[0]
        pool_size = len(self.item_pool.available_widgets) + len(
            self.item_pool.used_widgets
        )

        return {
            "total_items": len(self.items),
            "visible_items": visible_count,
            "rendered_widgets": len(self.item_pool.used_widgets),
            "pooled_widgets": len(self.item_pool.available_widgets),
            "total_widgets": pool_size,
            "memory_efficiency": f"{(pool_size / max(1, len(self.items))) * 100:.1f}%",
        }


class VirtualListWidget(QWidget):
    """
    High-level virtual list widget with common functionality.

    Provides a simple interface for virtual lists with search and selection.
    """

    # Signals
    item_selected = pyqtSignal(int, object)  # index, data
    item_activated = pyqtSignal(int, object)  # index, data

    def __init__(self, widget_factory: Callable[[Any], QWidget], parent=None):
        """
        Initialize the virtual list widget.

        Args:
            widget_factory: Function to create item widgets
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create virtual scroll area
        self.scroll_area = VirtualScrollArea(widget_factory)
        layout.addWidget(self.scroll_area)

        # Connect signals
        self.scroll_area.selection_changed.connect(self._on_selection_changed)

        # Data
        self.original_items = []
        self.filtered_items = []
        self.current_filter = ""

    def set_items(self, items: List[Any], item_height: int = None) -> None:
        """Set items in the list."""
        self.original_items = items.copy()
        self.filtered_items = items.copy()
        self.scroll_area.set_items(self.filtered_items, item_height)

    def filter_items(self, filter_func: Callable[[Any], bool]) -> None:
        """
        Filter items based on a function.

        Args:
            filter_func: Function that returns True for items to keep
        """
        self.filtered_items = [
            item for item in self.original_items if filter_func(item)
        ]
        self.scroll_area.set_items(self.filtered_items)

    def search_items(self, query: str, search_func: Callable[[Any, str], bool]) -> None:
        """
        Search items based on a query.

        Args:
            query: Search query
            search_func: Function that returns True for matching items
        """
        self.current_filter = query
        if query:
            self.filtered_items = [
                item for item in self.original_items if search_func(item, query)
            ]
        else:
            self.filtered_items = self.original_items.copy()

        self.scroll_area.set_items(self.filtered_items)

    def get_selected_item(self) -> Optional[Any]:
        """Get the selected item."""
        return self.scroll_area.get_selected_item()

    def select_item(self, index: int) -> None:
        """Select an item by index."""
        self.scroll_area.set_selected_index(index)

    def scroll_to_item(self, index: int) -> None:
        """Scroll to an item."""
        self.scroll_area.scroll_to_item(index)

    def _on_selection_changed(self, index: int) -> None:
        """Handle selection changes."""
        if 0 <= index < len(self.filtered_items):
            item_data = self.filtered_items[index]
            self.item_selected.emit(index, item_data)
