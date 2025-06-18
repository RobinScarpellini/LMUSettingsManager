"""
Application runner for the LMU Configuration Editor GUI.

Provides the main entry point for running the graphical user interface.
"""

import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .main_window import MainWindow
from ..main import setup_logging # Import the setup_logging function


def setup_application() -> QApplication:
    """
    Set up the Qt application with proper configuration.

    Returns:
        Configured QApplication instance
    """
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("LMU Configuration Editor")
    app.setApplicationDisplayName("LMU Configuration Editor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LMU Config Editor")
    app.setOrganizationDomain("lmu-config-editor.local")

    # Set application style
    app.setStyle("Fusion")  # Use Fusion style for consistent look across platforms

    # Set light theme palette
    from PyQt6.QtGui import QPalette, QColor

    palette = QPalette()

    # Set light theme colors
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    app.setPalette(palette)

    return app


def run_gui(debug_mode: bool = False) -> int:
    """
    Run the LMU Configuration Editor GUI application.

    Args:
        debug_mode: If True, forces loading of example files for testing

    Returns:
        Application exit code
    """
    # Call the centralized logging setup
    setup_logging()

    logger = logging.getLogger(__name__) # Get logger after setup
    logger.info(f"Starting LMU Configuration Editor GUI (Debug mode: {debug_mode})")

    try:
        # Create application
        app = setup_application()

        # Create and show main window
        main_window = MainWindow(debug_mode=debug_mode)
        main_window.show()

        # Run application
        logger.info("GUI application started successfully")
        return app.exec()

    except Exception as e:
        logger.error(f"Failed to start GUI application: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_gui())
