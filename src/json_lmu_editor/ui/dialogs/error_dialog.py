"""
Error dialog for displaying user-friendly error messages with recovery options.

Provides a modern error dialog with expandable details and recovery actions.
"""

from typing import Optional
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QFrame,
    QSizePolicy,
    QApplication,
    QButtonGroup,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor

from ...core.error_handler import ErrorResponse, ErrorSeverity, RecoveryOption


class ErrorDialog(QDialog):
    """Enhanced error dialog with recovery options and expandable details."""

    # Signals
    recovery_selected = pyqtSignal(str)  # recovery_option_name

    def __init__(self, error_response: ErrorResponse, parent=None):
        """
        Initialize the error dialog.

        Args:
            error_response: Error response with message and recovery options
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.error_response = error_response
        self.selected_recovery: Optional[RecoveryOption] = None

        # UI components
        self.details_widget: Optional[QTextEdit] = None
        self.details_visible = False
        self.recovery_buttons: list[QPushButton] = []

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Configure dialog
        self.setWindowTitle(self._get_window_title())
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMaximumWidth(600)

        # Apply severity-based styling
        self._apply_severity_styling()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # Header with icon and message
        header_widget = self._create_header()
        main_layout.addWidget(header_widget)

        # Recovery options
        if self.error_response.recovery_options:
            recovery_widget = self._create_recovery_options()
            main_layout.addWidget(recovery_widget)

        # Details section (collapsible)
        details_widget = self._create_details_section()
        main_layout.addWidget(details_widget)

        # Button bar
        button_bar = self._create_button_bar()
        main_layout.addWidget(button_bar)

        # Auto-resize
        self.adjustSize()

    def _get_window_title(self) -> str:
        """Get appropriate window title based on severity."""
        severity_titles = {
            ErrorSeverity.INFO: "Information",
            ErrorSeverity.WARNING: "Warning",
            ErrorSeverity.ERROR: "Error",
            ErrorSeverity.CRITICAL: "Critical Error",
        }
        return severity_titles.get(self.error_response.severity, "Error")

    def _apply_severity_styling(self) -> None:
        """Apply styling based on error severity."""
        severity_colors = {
            ErrorSeverity.INFO: "#2196F3",  # Blue
            ErrorSeverity.WARNING: "#FF9800",  # Orange
            ErrorSeverity.ERROR: "#F44336",  # Red
            ErrorSeverity.CRITICAL: "#9C27B0",  # Purple
        }

        color = severity_colors.get(self.error_response.severity, "#F44336")

        # Set border color based on severity
        self.setStyleSheet(f"""
            QDialog {{
                border: 2px solid {color};
                border-radius: 8px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)

    def _create_header(self) -> QWidget:
        """Create header with icon and error message."""
        header_widget = QFrame()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 10, 10, 10)

        # Error icon
        icon_label = QLabel()
        icon_pixmap = self._get_severity_icon()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(icon_label)

        # Message text
        message_label = QLabel(self.error_response.user_message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Style the message
        font = QFont()
        font.setPointSize(11)
        message_label.setFont(font)

        header_layout.addWidget(message_label, 1)

        return header_widget

    def _get_severity_icon(self) -> QPixmap:
        """Create an icon based on error severity."""
        # Create a simple colored circle icon
        size = 48
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Color based on severity
        severity_colors = {
            ErrorSeverity.INFO: QColor("#2196F3"),
            ErrorSeverity.WARNING: QColor("#FF9800"),
            ErrorSeverity.ERROR: QColor("#F44336"),
            ErrorSeverity.CRITICAL: QColor("#9C27B0"),
        }

        color = severity_colors.get(self.error_response.severity, QColor("#F44336"))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)

        # Add severity symbol
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)

        if self.error_response.severity == ErrorSeverity.INFO:
            symbol = "i"
        elif self.error_response.severity == ErrorSeverity.WARNING:
            symbol = "!"
        else:
            symbol = "✗"

        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol)
        painter.end()

        return pixmap

    def _create_recovery_options(self) -> QWidget:
        """Create recovery options section."""
        group_box = QGroupBox("What would you like to do?")
        layout = QVBoxLayout(group_box)

        # Create button group for exclusive selection
        self.button_group = QButtonGroup()

        for option in self.error_response.recovery_options:
            button = self._create_recovery_button(option)
            layout.addWidget(button)
            self.recovery_buttons.append(button)
            self.button_group.addButton(button)

            # Set default selection
            if option.is_default:
                button.setChecked(True)
                self.selected_recovery = option

        return group_box

    def _create_recovery_button(self, option: RecoveryOption) -> QPushButton:
        """Create a button for a recovery option."""
        button = QPushButton()
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Button text with description
        button_text = f"{option.name}"
        if option.description:
            button_text += f"\n{option.description}"

        button.setText(button_text)

        # Style the button
        button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                border: 2px solid #ccc;
                border-radius: 6px;
                background-color: #f9f9f9;
            }
            QPushButton:checked {
                border-color: #2196F3;
                background-color: #e3f2fd;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)

        # Connect selection
        button.toggled.connect(
            lambda checked, opt=option: self._on_recovery_selected(opt)
            if checked
            else None
        )

        return button

    def _on_recovery_selected(self, option: RecoveryOption) -> None:
        """Handle recovery option selection."""
        self.selected_recovery = option
        self.recovery_selected.emit(option.name)

    def _create_details_section(self) -> QWidget:
        """Create expandable details section."""
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)

        # Toggle button for details
        self.details_button = QPushButton("▶ Show Details")
        self.details_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.details_button.clicked.connect(self._toggle_details)
        details_layout.addWidget(self.details_button)

        # Details content (initially hidden)
        self.details_widget = QTextEdit()
        self.details_widget.setPlainText(self.error_response.technical_message)
        self.details_widget.setReadOnly(True)
        self.details_widget.setMaximumHeight(200)
        self.details_widget.setVisible(False)

        # Style details widget
        font = QFont("Consolas, Monaco, monospace")
        font.setPointSize(9)
        self.details_widget.setFont(font)

        details_layout.addWidget(self.details_widget)

        return details_frame

    def _toggle_details(self) -> None:
        """Toggle visibility of technical details."""
        self.details_visible = not self.details_visible
        self.details_widget.setVisible(self.details_visible)

        if self.details_visible:
            self.details_button.setText("▼ Hide Details")
        else:
            self.details_button.setText("▶ Show Details")

        # Adjust dialog size
        QTimer.singleShot(50, self.adjustSize)

    def _create_button_bar(self) -> QWidget:
        """Create bottom button bar."""
        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.addStretch()

        # Copy to clipboard button
        copy_button = QPushButton("Copy Error Details")
        copy_button.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(copy_button)

        # OK button (applies selected recovery action)
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self._apply_recovery)
        button_layout.addWidget(self.ok_button)

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        return button_bar

    def _copy_to_clipboard(self) -> None:
        """Copy error details to clipboard."""
        clipboard = QApplication.clipboard()

        error_text = (
            f"LMU Configuration Editor Error Report\n"
            f"=====================================\n\n"
            f"Error Type: {self.error_response.error_type.value}\n"
            f"Severity: {self.error_response.severity.value}\n"
            f"Message: {self.error_response.user_message}\n\n"
            f"Technical Details:\n"
            f"{self.error_response.technical_message}"
        )

        clipboard.setText(error_text)

        # Show brief confirmation
        self.ok_button.setText("Copied!")
        QTimer.singleShot(1000, lambda: self.ok_button.setText("OK"))

    def _apply_recovery(self) -> None:
        """Apply selected recovery action."""
        if self.selected_recovery:
            try:
                # Execute recovery action
                success = self.selected_recovery.action()
                if success:
                    self.accept()
                else:
                    # Recovery failed, but don't close dialog
                    self.ok_button.setText("Recovery Failed")
                    QTimer.singleShot(2000, lambda: self.ok_button.setText("OK"))
            except Exception as e:
                self.logger.error(f"Recovery action failed: {e}")
                self.ok_button.setText("Action Failed")
                QTimer.singleShot(2000, lambda: self.ok_button.setText("OK"))
        else:
            # No recovery selected, just close
            self.accept()

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # ESC key should close dialog
        self.setEscapeKeyPressed = True

    def get_selected_recovery(self) -> Optional[RecoveryOption]:
        """Get the selected recovery option."""
        return self.selected_recovery

    @staticmethod
    def show_error(
        error_response: ErrorResponse, parent=None
    ) -> Optional[RecoveryOption]:
        """
        Show error dialog and return selected recovery option.

        Args:
            error_response: Error response to display
            parent: Parent widget

        Returns:
            Selected recovery option or None if cancelled
        """
        dialog = ErrorDialog(error_response, parent)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_recovery()

        return None


class ErrorNotification(QFrame):
    """Non-modal error notification for minor errors."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, parent=None
    ):
        """
        Initialize error notification.

        Args:
            message: Error message to display
            severity: Error severity
            parent: Parent widget
        """
        super().__init__(parent)

        self.setup_ui(message, severity)

        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_notification)

    def setup_ui(self, message: str, severity: ErrorSeverity) -> None:
        """Set up the notification UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Severity indicator
        indicator = QLabel("●")
        severity_colors = {
            ErrorSeverity.INFO: "#2196F3",
            ErrorSeverity.WARNING: "#FF9800",
            ErrorSeverity.ERROR: "#F44336",
            ErrorSeverity.CRITICAL: "#9C27B0",
        }
        color = severity_colors.get(severity, "#F44336")
        indicator.setStyleSheet(f"color: {color}; font-size: 16px;")
        layout.addWidget(indicator)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label, 1)

        # Close button
        close_button = QPushButton("✕")
        close_button.setMaximumSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                border: none;
                font-weight: bold;
                background: transparent;
            }
            QPushButton:hover {
                background-color: rgba(0,0,0,0.1);
                border-radius: 2px;
            }
        """)
        close_button.clicked.connect(self.hide_notification)
        layout.addWidget(close_button)

        # Style the notification
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color}20;
                border: 1px solid {color};
                border-radius: 4px;
            }}
        """)

    def show_notification(self, timeout: int = 5000) -> None:
        """
        Show the notification.

        Args:
            timeout: Auto-hide timeout in milliseconds
        """
        self.show()
        if timeout > 0:
            self.hide_timer.start(timeout)

    def hide_notification(self) -> None:
        """Hide the notification."""
        self.hide()
        self.hide_timer.stop()
