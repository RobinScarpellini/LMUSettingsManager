"""
Configuration comparison dialog.

Displays differences between current and selected configuration.
"""

from typing import List, Dict, Any, Optional
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QHeaderView,
    QAbstractItemView,
    QTextEdit,
    QSplitter,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ...core.comparison_engine import ComparisonEngine, Difference, DifferenceType


class ComparisonDialog(QDialog):
    """Dialog for comparing two configurations."""

    def __init__(
        self,
        current_config: Dict[str, Any],
        selected_config: Dict[str, Any],
        current_name: str = "Current Configuration",
        selected_name: str = "Selected Configuration",
        parent=None,
    ):
        """
        Initialize the comparison dialog.

        Args:
            current_config: Current configuration data
            selected_config: Selected configuration data
            current_name: Name of current configuration
            selected_name: Name of selected configuration
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        # Configuration data
        self.current_config = current_config
        self.selected_config = selected_config
        self.current_name = current_name
        self.selected_name = selected_name

        # Comparison engine
        self.comparison_engine = ComparisonEngine()
        self.differences: List[Difference] = []

        # UI components
        self.comparison_table: Optional[QTableWidget] = None
        self.filter_checkbox: Optional[QCheckBox] = None
        self.summary_label: Optional[QLabel] = None
        self.details_text: Optional[QTextEdit] = None
        self.export_button: Optional[QPushButton] = None
        self.close_button: Optional[QPushButton] = None

        self.setup_ui()
        self.load_comparison_data()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Configuration Comparison")
        self.setModal(True)
        self.resize(900, 600)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(f"Comparing: {self.current_name} vs {self.selected_name}")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        layout.addWidget(title_label)

        # Summary group
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_label = QLabel()
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_group)

        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Comparison table group
        table_group = QGroupBox("Differences")
        table_layout = QVBoxLayout(table_group)

        # Filter controls
        filter_layout = QHBoxLayout()

        self.filter_checkbox = QCheckBox("Show only differences")
        self.filter_checkbox.setChecked(True)
        filter_layout.addWidget(self.filter_checkbox)

        filter_layout.addStretch()

        self.export_button = QPushButton("Copy to Clipboard")
        filter_layout.addWidget(self.export_button)

        table_layout.addLayout(filter_layout)

        # Comparison table
        self.comparison_table = QTableWidget()
        self.setup_table()
        table_layout.addWidget(self.comparison_table)

        splitter.addWidget(table_group)

        # Details panel
        details_group = QGroupBox("Field Details")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_group)

        # Set splitter proportions
        splitter.setSizes([400, 150])

        layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.setDefault(True)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def setup_table(self) -> None:
        """Set up the comparison table."""
        self.comparison_table.setColumnCount(4)
        self.comparison_table.setHorizontalHeaderLabels(
            ["Setting Name", self.current_name, self.selected_name, "Category"]
        )

        # Configure table properties
        self.comparison_table.setAlternatingRowColors(True)
        self.comparison_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.comparison_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Configure column widths
        header = self.comparison_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Setting Name
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )  # Current
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )  # Selected
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )  # Category

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # Filter checkbox
        self.filter_checkbox.stateChanged.connect(self.apply_filter)

        # Table selection
        self.comparison_table.itemSelectionChanged.connect(self.show_field_details)

        # Buttons
        self.export_button.clicked.connect(self.export_to_clipboard)
        self.close_button.clicked.connect(self.accept)

    def load_comparison_data(self) -> None:
        """Load and display comparison data."""
        # Perform comparison
        self.differences = self.comparison_engine.compare_configurations(
            self.current_config,
            self.selected_config
        )

        # Update summary
        self.update_summary()

        # Populate table
        self.populate_table()

    def update_summary(self) -> None:
        """Update the summary information."""
        summary = self.comparison_engine.get_difference_summary(self.differences)

        summary_text = (
            f"Total differences: {summary['total']}\n"
            f"• Value changes: {summary['value_changed']}\n"
            f"• Type changes: {summary['type_changed']}\n"
            f"• Fields added: {summary['field_added']}\n"
            f"• Fields removed: {summary['field_removed']}"
        )

        self.summary_label.setText(summary_text)

        # Color code the summary based on number of differences
        if summary["total"] == 0:
            self.summary_label.setStyleSheet("color: green;")
        elif summary["total"] < 10:
            self.summary_label.setStyleSheet("color: orange;")
        else:
            self.summary_label.setStyleSheet("color: red;")

    def populate_table(self) -> None:
        """Populate the comparison table with differences."""
        # Filter differences if needed
        differences_to_show = (
            self.differences
            if not self.filter_checkbox.isChecked()
            else [
                d
                for d in self.differences
                if d.difference_type != DifferenceType.VALUE_CHANGED
                or d.value1 != d.value2
            ]
        )

        self.comparison_table.setRowCount(len(differences_to_show))

        for row, diff in enumerate(differences_to_show):
            # Setting name
            name_item = QTableWidgetItem(diff.field_name)
            name_item.setToolTip(diff.field_path)
            self.comparison_table.setItem(row, 0, name_item)

            # Current value
            current_value = self.comparison_engine.format_value_for_display(
                diff.value1, diff.field_type
            )
            current_item = QTableWidgetItem(current_value)
            current_item.setToolTip(str(diff.value1))

            # Selected value
            selected_value = self.comparison_engine.format_value_for_display(
                diff.value2, diff.field_type
            )
            selected_item = QTableWidgetItem(selected_value)
            selected_item.setToolTip(str(diff.value2))

            # Color code based on difference type
            if diff.difference_type == DifferenceType.VALUE_CHANGED:
                current_item.setBackground(QColor(255, 255, 200))  # Light yellow
                selected_item.setBackground(QColor(255, 255, 200))
            elif diff.difference_type == DifferenceType.FIELD_ADDED:
                selected_item.setBackground(QColor(200, 255, 200))  # Light green
                current_item.setBackground(QColor(240, 240, 240))  # Light gray
            elif diff.difference_type == DifferenceType.FIELD_REMOVED:
                current_item.setBackground(QColor(255, 200, 200))  # Light red
                selected_item.setBackground(QColor(240, 240, 240))  # Light gray
            elif diff.difference_type == DifferenceType.TYPE_CHANGED:
                current_item.setBackground(QColor(255, 220, 220))  # Light red
                selected_item.setBackground(QColor(220, 220, 255))  # Light blue

            self.comparison_table.setItem(row, 1, current_item)
            self.comparison_table.setItem(row, 2, selected_item)

            # Category
            category_item = QTableWidgetItem(diff.category)
            self.comparison_table.setItem(row, 3, category_item)

            # Store difference object for details view
            name_item.setData(Qt.ItemDataRole.UserRole, diff)

    def apply_filter(self) -> None:
        """Apply or remove filter to show only differences."""
        self.populate_table()

    def show_field_details(self) -> None:
        """Show details for the selected field."""
        current_row = self.comparison_table.currentRow()
        if current_row < 0:
            self.details_text.clear()
            return

        # Get difference object
        name_item = self.comparison_table.item(current_row, 0)
        if not name_item:
            return

        diff = name_item.data(Qt.ItemDataRole.UserRole)
        if not diff:
            return

        # Format details
        details = f"Field: {diff.field_path}\n"
        details += f"Category: {diff.category}\n"
        details += f"Type: {diff.field_type.value}\n"
        details += (
            f"Difference: {diff.difference_type.value.replace('_', ' ').title()}\n\n"
        )

        if diff.description:
            details += f"Description: {diff.description}\n\n"

        details += f"{self.current_name}: {diff.value1}\n"
        details += f"{self.selected_name}: {diff.value2}"

        self.details_text.setPlainText(details)

    def export_to_clipboard(self) -> None:
        """Export comparison results to clipboard."""
        try:
            # Generate text report
            report = "Configuration Comparison Report\n"
            report += f"{'=' * 50}\n"
            report += f"Current: {self.current_name}\n"
            report += f"Selected: {self.selected_name}\n"
            report += f"Generated: {QTimer().singleShot.__self__.currentDateTime().toString()}\n\n"

            # Add summary
            summary = self.comparison_engine.get_difference_summary(self.differences)
            report += "Summary:\n"
            report += f"Total differences: {summary['total']}\n"
            report += f"Value changes: {summary['value_changed']}\n"
            report += f"Type changes: {summary['type_changed']}\n"
            report += f"Fields added: {summary['field_added']}\n"
            report += f"Fields removed: {summary['field_removed']}\n\n"

            # Add differences table
            if self.differences:
                report += "Differences:\n"
                report += f"{'-' * 50}\n"

                for diff in self.differences:
                    report += f"Field: {diff.field_path}\n"
                    report += f"Category: {diff.category}\n"
                    report += f"Type: {diff.difference_type.value.replace('_', ' ').title()}\n"
                    report += f"{self.current_name}: {diff.value1}\n"
                    report += f"{self.selected_name}: {diff.value2}\n"
                    if diff.description:
                        report += f"Description: {diff.description}\n"
                    report += "\n"
            else:
                report += "No differences found.\n"

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(report)

            # Show confirmation
            QMessageBox.information(
                self,
                "Export Successful",
                "Comparison report has been copied to the clipboard.",
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Failed to export comparison report:\n\n{str(e)}",
            )

    def filter_differences(self, differences: List[Difference]) -> List[Difference]:
        """
        Filter differences based on current filter settings.

        Args:
            differences: List of differences to filter

        Returns:
            Filtered list of differences
        """
        if not self.filter_checkbox.isChecked():
            return differences

        # Show only actual differences (exclude identical values)
        return [d for d in differences if d.value1 != d.value2]
