"""
Search widget for finding configuration fields.

Provides real-time search functionality with clear button and result navigation.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut, QFont
import logging
from typing import Optional

from ...core.optimizations.search_indexer import SearchIndexer


class SearchWidget(QWidget):
    """Widget for searching configuration fields."""

    # Signals
    search_requested = pyqtSignal(str)
    search_cleared = pyqtSignal()
    result_navigation = pyqtSignal(int)  # 1 for next, -1 for previous

    def __init__(self, parent=None):
        """Initialize the search widget."""
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        # Search state
        self.current_results = []
        self.current_index = -1

        # Search indexer for performance
        self.search_indexer: Optional[SearchIndexer] = None

        # Debounce timer for search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Row 1: Label and Navigation buttons (moved to right side)
        row1_layout = QHBoxLayout()
        
        search_label = QLabel("Search")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12) # Match Configuration Manager title font size
        search_label.setFont(font)
        row1_layout.addWidget(search_label, 0) # Label takes minimal space
        
        row1_layout.addStretch(10) # Main stretch, takes up most space
        
        self.prev_button = QPushButton("◀")
        self.prev_button.setEnabled(False)
        self.prev_button.setToolTip("Previous result (Shift+F3)")
        self.prev_button.setFixedSize(28, 28)
        row1_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("▶")
        self.next_button.setEnabled(False)
        self.next_button.setToolTip("Next result (F3)")
        self.next_button.setFixedSize(28, 28)
        row1_layout.addWidget(self.next_button)

        main_layout.addLayout(row1_layout)

        # Row 2: Input and Clear
        row2_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search setting names...")
        # self.search_input.setClearButtonEnabled(True) # Standard clear button removed, using custom
        self.search_input.setMaximumHeight(35)
        row2_layout.addWidget(self.search_input, 1) # Stretch factor

        self.clear_button = QPushButton("✕") # Using a cross character
        self.clear_button.setEnabled(False)
        self.clear_button.setToolTip("Clear search (Escape)")
        self.clear_button.setFixedSize(28, 28)
        row2_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(row2_layout)
        
        # Row 3: Result count text (moved under the textfield)
        row3_layout = QHBoxLayout()
        
        self.result_label = QLabel("")
        self.result_label.setMinimumWidth(80)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row3_layout.addWidget(self.result_label, 1)
        
        main_layout.addLayout(row3_layout)
        
        # Remove fixed height for the entire widget, let it size by content
        # self.setFixedHeight(40)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # Search input changes
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.navigate_next)

        # Navigation buttons
        self.prev_button.clicked.connect(self.navigate_previous)
        self.next_button.clicked.connect(self.navigate_next)

        # Clear button
        self.clear_button.clicked.connect(self.clear_search)

        # Keyboard shortcuts
        next_shortcut = QShortcut(QKeySequence("F3"), self)
        next_shortcut.activated.connect(self.navigate_next)

        prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        prev_shortcut.activated.connect(self.navigate_previous)

        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.clear_search)

    def on_search_text_changed(self, text: str) -> None:
        """
        Handle search text changes with debouncing.

        Args:
            text: Current search text
        """
        # Stop previous timer
        self.search_timer.stop()

        if text.strip():
            if len(text) >= 2:  # Minimum search length
                # Start timer for debounced search
                self.search_timer.start(300)  # 300ms delay
            else:
                self.result_label.setText("Type at least 2 characters")
                self.update_navigation_buttons(False)
        else:
            # Clear search
            self.clear_search()

    def perform_search(self) -> None:
        """Perform the actual search."""
        query = self.search_input.text().strip()
        if not query or len(query) < 2:
            return

        # Emit search signal
        self.search_requested.emit(query)

        # Enable clear button
        self.clear_button.setEnabled(True)

    def update_search_results(self, results: list) -> None:
        """
        Update search results and navigation state.

        Args:
            results: List of search result field paths
        """
        self.current_results = results
        self.current_index = 0 if results else -1

        # Update result counter and navigation
        self.update_result_counter()
        self.update_navigation_buttons(len(results) > 0)

    def update_result_counter(self) -> None:
        """Update the result counter display."""
        if self.current_results:
            if len(self.current_results) == 1:
                self.result_label.setText("1/1 result")
            else:
                current_pos = self.current_index + 1 if self.current_index >= 0 else 1
                self.result_label.setText(
                    f"{current_pos}/{len(self.current_results)} results"
                )
        else:
            query = self.search_input.text().strip()
            if query:
                self.result_label.setText("No results")
            else:
                self.result_label.setText("")

    def update_navigation_buttons(self, enabled: bool) -> None:
        """
        Update navigation button states.

        Args:
            enabled: Whether navigation should be enabled
        """
        has_results = enabled and len(self.current_results) > 0
        self.prev_button.setEnabled(has_results)
        self.next_button.setEnabled(has_results)

        # Update button tooltips with position info
        if has_results and len(self.current_results) > 1:
            position_text = f"({self.current_index + 1}/{len(self.current_results)})"
            self.prev_button.setToolTip(f"Previous result {position_text} (Shift+F3)")
            self.next_button.setToolTip(f"Next result {position_text} (F3)")
        else:
            self.prev_button.setToolTip("Previous result (Shift+F3)")
            self.next_button.setToolTip("Next result (F3)")

    def navigate_previous(self) -> None:
        """Navigate to previous search result."""
        if not self.current_results:
            return

        self.current_index = (self.current_index - 1) % len(self.current_results)
        self.update_result_counter()
        self.update_navigation_buttons(True)
        self.result_navigation.emit(-1)

    def navigate_next(self) -> None:
        """Navigate to next search result."""
        if not self.current_results:
            return

        self.current_index = (self.current_index + 1) % len(self.current_results)
        self.update_result_counter()
        self.update_navigation_buttons(True)
        self.result_navigation.emit(1)

    def clear_search(self) -> None:
        """Clear the search."""
        self.search_input.clear()
        self.result_label.setText("")
        self.current_results = []
        self.current_index = -1
        self.update_navigation_buttons(False)
        self.clear_button.setEnabled(False)

        # Emit clear signal
        self.search_cleared.emit()

    def focus_search(self) -> None:
        """Focus the search input."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def get_current_result(self) -> str:
        """
        Get the currently selected search result.

        Returns:
            Current result field path or empty string
        """
        if self.current_results and 0 <= self.current_index < len(self.current_results):
            return self.current_results[self.current_index]
        return ""

    def set_search_indexer(self, indexer: SearchIndexer) -> None:
        """
        Set the search indexer for improved performance.

        Args:
            indexer: Search indexer instance
        """
        self.search_indexer = indexer
        self.logger.debug("Search indexer configured")

    def get_search_suggestions(self, query: str) -> list:
        """
        Get search suggestions for the current query.

        Args:
            query: Current search query

        Returns:
            List of search suggestions
        """
        if self.search_indexer and len(query) >= 2:
            return self.search_indexer.get_search_suggestions(query)
        return []
