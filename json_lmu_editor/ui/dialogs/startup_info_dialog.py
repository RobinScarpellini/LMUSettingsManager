"""
Dialog to display startup configuration information and allow browsing.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from pathlib import Path
from typing import Optional


class StartupInfoDialog(QDialog):
    """
    A dialog to show the user what configuration files were loaded at startup
    and provide an option to browse for a different game folder.
    """

    browse_requested = pyqtSignal()  # Signal to tell MainWindow to open browse dialog

    def __init__(
        self,
        json_path: Optional[Path],
        ini_path: Optional[Path],
        game_path_used: Optional[Path],
        is_example: bool,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Startup Configuration")
        self.setMinimumWidth(500)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)

        title_label = QLabel("Configuration Loaded")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title_label)

        # Info section
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0,0,0,0)
        info_layout.setSpacing(5)

        if is_example:
            status_text = "Loaded example configuration files."
            if game_path_used: # Should be the 'example' folder path
                 status_text += f"\nLocation: {game_path_used.resolve()}"
            info_layout.addWidget(QLabel(status_text))
        elif json_path and ini_path and game_path_used:
            info_layout.addWidget(QLabel(f"<b>Game Installation Path:</b><br>{game_path_used.resolve()}"))
            info_layout.addWidget(QLabel(f"<b>Settings.JSON Loaded:</b><br>{json_path.resolve()}"))
            info_layout.addWidget(QLabel(f"<b>Config_DX11.ini Loaded:</b><br>{ini_path.resolve()}"))
        else:
            info_layout.addWidget(QLabel("No game configuration files were loaded automatically."))
            info_layout.addWidget(QLabel("You can try to locate your game folder manually."))
        
        self.layout.addWidget(info_widget)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(separator)

        # Buttons
        button_layout = QHBoxLayout()

        self.browse_button = QPushButton("Browse for Game Folder...")
        self.browse_button.clicked.connect(self.on_browse_clicked)
        button_layout.addWidget(self.browse_button)

        button_layout.addStretch(1)

        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.layout.addLayout(button_layout)

    def on_browse_clicked(self):
        """Emits browse_requested and closes this dialog."""
        self.browse_requested.emit()
        self.accept() # Close this dialog, MainWindow will handle browsing

    @staticmethod
    def show_startup_info(
        json_path: Optional[Path],
        ini_path: Optional[Path],
        game_path_used: Optional[Path], # The base game path from which files were derived
        is_example: bool,
        parent: Optional[QWidget] = None
    ) -> bool:
        """
        Static method to create and show the dialog.

        Returns:
            True if OK was clicked, False if dialog was closed otherwise (or browse).
            The browse_requested signal handles the browse action.
        """
        dialog = StartupInfoDialog(json_path, ini_path, game_path_used, is_example, parent)
        # We don't directly return the browse action here, it's handled by signal
        return dialog.exec() == QDialog.DialogCode.Accepted