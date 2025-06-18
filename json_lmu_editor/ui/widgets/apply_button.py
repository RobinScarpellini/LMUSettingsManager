"""
Apply changes button widget.

Provides a stateful button for applying configuration changes.
"""

from PyQt6.QtWidgets import QPushButton, QWidget
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve


class ApplyChangesButton(QPushButton):
    """Button for applying configuration changes with visual state feedback."""

    def __init__(self, parent: QWidget = None):
        """Initialize the apply changes button."""
        super().__init__("Apply Changes", parent)

        # Initial state
        self.change_count = 0
        self.current_state = "disabled"

        # Animation for state changes
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Timer for temporary states
        self.state_timer = QTimer()
        self.state_timer.setSingleShot(True)
        self.state_timer.timeout.connect(self.reset_to_normal_state)

        # Initial setup
        self.update_state(0)

    def update_state(self, change_count: int) -> None:
        """
        Update button state based on change count.

        Args:
            change_count: Number of pending changes
        """
        self.change_count = change_count

        if change_count > 0:
            self.setEnabled(True)
            self.setText(f"Apply Changes ({change_count})")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            self.current_state = "enabled"
        else:
            self.setEnabled(False)
            self.setText("Apply Changes")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    color: #999;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
            """)
            self.current_state = "disabled"

    def set_saving_state(self) -> None:
        """Set button to saving state."""
        self.setEnabled(False)
        self.setText("Saving...")
        self.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.current_state = "saving"

    def set_success_state(self) -> None:
        """Set button to success state temporarily."""
        self.setEnabled(False)
        self.setText("Changes Saved ✓")
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.current_state = "success"

        # Return to normal state after delay
        self.state_timer.start(2000)

    def set_error_state(self, error_message: str = "Save Failed") -> None:
        """
        Set button to error state temporarily.

        Args:
            error_message: Error message to display
        """
        self.setEnabled(True)
        self.setText("Save Failed ✗")
        self.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.current_state = "error"
        self.setToolTip(error_message)

        # Return to normal state after delay
        self.state_timer.start(3000)

    def reset_to_normal_state(self) -> None:
        """Reset button to normal state based on current change count."""
        self.setToolTip("")  # Clear error tooltip
        self.update_state(self.change_count)

    def get_current_state(self) -> str:
        """
        Get the current button state.

        Returns:
            Current state name
        """
        return self.current_state
