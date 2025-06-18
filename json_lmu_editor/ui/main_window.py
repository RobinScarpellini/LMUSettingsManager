"""
Main window for the LMU Configuration Editor.

Provides the main application window with tabbed interface, search, and configuration management.
"""

import sys
from pathlib import Path
from typing import Optional, List
import logging

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QLabel,
    QPushButton,
    QDialog,
    QSizePolicy, # Added for setting panel policies
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings, QUrl
from PyQt6.QtGui import QAction, QKeySequence, QDesktopServices, QResizeEvent

from ..core.models.configuration_model import ConfigurationModel
from ..core.game_detector import GameDetector
from ..core.configuration_manager import ConfigurationManager
from ..core.comparison_engine import ComparisonEngine
from ..core.import_export import ConfigurationPorter
from ..utils.settings_manager import SettingsManager
from .widgets.search_widget import SearchWidget
from .widgets.category_tabs import CategoryTabWidget
from .widgets.config_panel import ConfigurationPanel
from .widgets.apply_button import ApplyChangesButton
from .dialogs.save_dialog import SaveConfigurationDialog
from .dialogs.compare_dialog import ComparisonDialog
from .shortcuts.shortcut_manager import ShortcutManager
from ..core.error_handler import ErrorHandler, ErrorContext
from .dialogs.error_dialog import ErrorDialog
from .dialogs.startup_info_dialog import StartupInfoDialog # Added import
from .dialogs.profile_sync_dialog import ProfileSyncDialog, ProfileSyncChoice
from ..core.optimizations.search_indexer import SearchIndexer
from ..core.optimizations.lazy_loader import LazyLoader
from ..core.profile_manager import ProfileManager


class MainWindow(QMainWindow):
    """Main application window."""

    # Signals
    configuration_loaded = pyqtSignal()
    changes_applied = pyqtSignal()
    search_triggered = pyqtSignal(str)

    def __init__(self, debug_mode: bool = False):
        """Initialize the main window.

        Args:
            debug_mode: If True, forces loading of example files for testing
        """
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.debug_mode = debug_mode

        # Core components
        self.config_model = ConfigurationModel()
        self.game_detector = GameDetector()
        self.settings_manager = SettingsManager()
        self.config_manager: Optional[ConfigurationManager] = None
        self.comparison_engine = ComparisonEngine()
        self.config_porter = ConfigurationPorter()
        self.profile_manager = ProfileManager()

        # UI components
        self.central_widget: Optional[QWidget] = None
        self.search_widget: Optional[SearchWidget] = None
        self.category_tabs: Optional[CategoryTabWidget] = None
        self.config_panel: Optional[ConfigurationPanel] = None
        self.apply_button: Optional[ApplyChangesButton] = None
        self.status_label: Optional[QLabel] = None

        # Shortcut manager
        self.shortcut_manager: Optional[ShortcutManager] = None

        # Error handler
        self.error_handler = ErrorHandler()

        # Performance optimizations
        self.search_indexer = SearchIndexer()
        self.lazy_loader = LazyLoader()

        # Settings
        self.qt_settings = QSettings("LMUConfigEditor", "MainWindow")

        # Active configuration tracking
        self.current_loaded_config_name: Optional[str] = None
        self.current_loaded_config_is_profile: bool = False

        # Initialize UI
        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()
        self.load_window_geometry()

        # Initialize with game detection
        QTimer.singleShot(100, self.initialize_configuration)

    def setup_ui(self) -> None:
        """Set up the user interface."""
        title = "LMU Configuration Editor"
        if self.debug_mode:
            title += " - Debug Mode"
        self.setWindowTitle(title)
        self.setMinimumSize(1024, 768) # Increased minimum size
        self.resize(1200, 800)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar - Item 8: Removing toolbar to see if it's the source of the top bar
        # self.create_toolbar()

        # Create central widget
        self.create_central_widget()

        # Create status bar - REMOVED as per feedback
        # self.create_status_bar()

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Open game folder action
        open_action = QAction("&Open Game Folder...", self)
        # open_action.setShortcut(QKeySequence("Ctrl+O")) # Removed shortcut
        open_action.setStatusTip("Browse for Le Mans Ultimate installation")
        open_action.triggered.connect(self.browse_for_game)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Reload configuration action
        reload_action = QAction("&Reload Configuration", self)
        # reload_action.setShortcut(QKeySequence("F5")) # Removed shortcut
        reload_action.setStatusTip("Reload configuration files from disk")
        reload_action.triggered.connect(self.reload_configuration)
        file_menu.addAction(reload_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        # exit_action.setShortcut(QKeySequence("Ctrl+Q")) # Removed shortcut
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Revert all changes action
        revert_action = QAction("&Revert All Changes", self)
        # revert_action.setShortcut(QKeySequence("Ctrl+Z")) # Removed shortcut
        revert_action.setStatusTip("Revert all pending changes")
        revert_action.triggered.connect(self.revert_all_changes)
        edit_menu.addAction(revert_action)

        # Apply changes action
        apply_action = QAction("&Apply Changes", self)
        apply_action.setShortcut(QKeySequence("Ctrl+S")) # Kept shortcut
        apply_action.setStatusTip("Apply all pending changes")
        apply_action.triggered.connect(self.apply_changes)
        edit_menu.addAction(apply_action)

        # Configuration menu
        config_menu = menubar.addMenu("&Configuration")

        # Save configuration action
        save_config_action = QAction("&Save Configuration As...", self)
        # save_config_action.setShortcut(QKeySequence("Ctrl+Shift+S")) # Removed shortcut
        save_config_action.setStatusTip("Save current configuration with custom name")
        save_config_action.triggered.connect(self.save_configuration)
        config_menu.addAction(save_config_action)

        config_menu.addSeparator()

        # Export configuration action
        export_action = QAction("&Export Configuration...", self)
        export_action.setStatusTip("Export selected configuration to .lmuconfig file")
        export_action.triggered.connect(self.export_configuration)
        config_menu.addAction(export_action)

        # Import configuration action
        import_action = QAction("&Import Configuration...", self)
        import_action.setStatusTip("Import configuration from .lmuconfig file")
        import_action.triggered.connect(self.import_configuration)
        config_menu.addAction(import_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        # About action
        about_action = QAction("&About", self)
        about_action.setStatusTip("About LMU Configuration Editor")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self) -> None:
        """Create the toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setVisible(
            False
        )  # Item 8: Hide the toolbar if it's the source of the top bar

        # Apply button is now in config_panel
        self.apply_button = (
            ApplyChangesButton()
        )  # Instantiated here, passed to config_panel
        # toolbar.addWidget(self.apply_button) # Original location

        # toolbar.addSeparator() # Separator is removed as both buttons are moved.

        # Add reload action - Now moved to config_panel
        # reload_action = QAction('Reload', self)
        # reload_action.setStatusTip('Reload configuration files')
        # reload_action.triggered.connect(self.reload_configuration)
        # toolbar.addAction(reload_action)

    def create_central_widget(self) -> None:
        """Create the central widget with tabs and configuration panel."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(5, 0, 5, 5)  # Set top margin to 0
        
        # Search widget will be moved to ConfigPanel
        # self.search_widget = SearchWidget()
        # main_layout.addWidget(self.search_widget)
        
        # Splitter for tabs and config panel
        self.splitter = QSplitter(Qt.Orientation.Horizontal) # Store as self.splitter
        sp_splitter = self.splitter.sizePolicy()
        sp_splitter.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        sp_splitter.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.splitter.setSizePolicy(sp_splitter)
        self.splitter.setHandleWidth(1) # Make handle thin for a static look
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cccccc;
            }
        """)
        # Prevent users from moving the splitter handle initially if a fixed proportion is desired
        # However, to make it responsive to window size and maintain proportion,
        # disabling the handle might not be necessary if stretch factors are set correctly.
        # Let's keep it disabled for now to maintain the "fixed proportion" feel programmatically.
        # If user resizing is desired later, this can be removed.
        # for i in range(self.splitter.count()):
        #     handle = self.splitter.handle(i)
        #     if handle:
        #         handle.setDisabled(True) # Keep disabled to enforce programmatic sizing
                
        main_layout.addWidget(self.splitter)
        
        # Category tabs (left side)
        self.category_tabs = CategoryTabWidget()
        sp_tabs = self.category_tabs.sizePolicy()
        sp_tabs.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        sp_tabs.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.category_tabs.setSizePolicy(sp_tabs)
        self.splitter.addWidget(self.category_tabs)

        # Configuration panel (right side)
        if not self.apply_button:  # Should be instantiated above
            self.apply_button = ApplyChangesButton()
        # Pass search_indexer to ConfigPanel
        self.config_panel = ConfigurationPanel(
            apply_button_widget=self.apply_button,
            search_indexer=self.search_indexer
        )
        sp_panel = self.config_panel.sizePolicy()
        sp_panel.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        sp_panel.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.config_panel.setSizePolicy(sp_panel)
        self.splitter.addWidget(self.config_panel)
        
        # Set splitter stretch factors for responsive proportional sizing
        # Left panel (index 0) gets 84% of the space
        # Right panel (index 1) gets 16% of the space
        self.splitter.setStretchFactor(0, 84)
        self.splitter.setStretchFactor(1, 16)
        
        # Explicitly set initial sizes to guide the proportion,
        # but stretch factors will govern resizing.
        # total_width = self.width() # or a default like 1200
        # left_width = int(total_width * 0.82)
        # right_width = int(total_width * 0.18)
        # self.splitter.setSizes([left_width, right_width])
        # Using setSizes might override stretchFactor behavior on initial load.
        # It's often better to let stretchFactor dictate from the start.
        # If initial appearance is off, then setSizes can be used carefully.
        # For now, relying on stretch factors.

        self.splitter.setCollapsible(0, False)  # Don't allow collapsing tabs
        self.splitter.setCollapsible(1, False)  # Don't allow collapsing config panel
        
        # Ensure the handle remains non-movable by the user if that's the intent
        # This needs to be done AFTER widgets are added.
        # We'll iterate through handles and disable them.
        # This is a bit of a workaround as QSplitter is designed to be user-interactive.
        # A more robust way for fixed panels would be not using QSplitter or subclassing.
        # For now, disabling handles after setup.
        QTimer.singleShot(0, lambda: self.disable_splitter_handles(self.splitter))


    def disable_splitter_handles(self, splitter: QSplitter):
        """Disable all handles of the splitter."""
        for i in range(1, splitter.count()): # Iterate from 1 up to count-1 for handles
            handle = splitter.handle(i)
            if handle:
                # Disable mouse events on the handle
                handle.setDisabled(True)
                # Optionally, make it visually less prominent or hide it
                # handle.setStyleSheet("QSplitter::handle { background-color: transparent; width: 0px; }")


    # def create_status_bar(self) -> None: # REMOVED as per feedback
    #     """Create the status bar."""
    #     status_bar = self.statusBar()
    #
    #     # Status label
    #     self.status_label = QLabel("Ready")
    #     status_bar.addWidget(self.status_label)
    #
    #     # Game path label (right side)
    #     self.game_path_label = QLabel("No game path")
    #     status_bar.addPermanentWidget(self.game_path_label)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        # Connect model changes to UI updates
        self.config_model.add_observer(self.on_model_changed)

        # Connect search - This will be handled by ConfigPanel now
        # if self.search_widget:
        #     self.search_widget.search_requested.connect(self.perform_search)
        #     self.search_widget.search_cleared.connect(self.clear_search)
        
        # Connect apply button
        if self.apply_button:
            self.apply_button.clicked.connect(self.apply_changes)

        # Connect configuration panel
        if self.config_panel:
            self.config_panel.load_requested.connect(self.load_configuration_from_panel)
            self.config_panel.save_requested.connect(self.save_configuration)
            self.config_panel.compare_requested.connect(self.compare_configuration)
            self.config_panel.delete_requested.connect(self.delete_configuration)
            self.config_panel.reload_config_requested.connect(
                self.reload_configuration
            )  # Added connection
            
            # Connect new signals from ConfigPanel for search
            self.config_panel.search_requested_from_panel.connect(self.on_search_performed)
            self.config_panel.search_cleared_from_panel.connect(self.clear_search)
            self.config_panel.search_navigation_from_panel.connect(self.on_search_navigation)
            self.config_panel.open_settings_location_requested.connect(self.open_settings_json_location)

        # Connect search result updates and navigation - This will be handled by ConfigPanel now
        # if self.search_widget:
        #     self.search_widget.search_requested.connect(self.on_search_performed)
        #     self.search_widget.result_navigation.connect(self.on_search_navigation)

    def setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        self.shortcut_manager = ShortcutManager(self)
        self.shortcut_manager.register_shortcuts()

        # Connect shortcut manager signals
        self.shortcut_manager.shortcut_triggered.connect(self.on_shortcut_triggered)

    def initialize_configuration(self) -> None:
        """Initialize configuration by detecting game and loading files."""
        # self.status_label.setText("Looking for configuration files...") # REMOVED status_label
        self.logger.info("Looking for configuration files...")  # Log instead

        # Check for debug mode or example files
        example_dir = Path("example")
        json_example = example_dir / "Settings.JSON"
        ini_example = example_dir / "Config_DX11.ini"

        if self.debug_mode:
            # Debug mode: force loading example files
            if json_example.exists() and ini_example.exists():
                self.logger.info(
                    "Loading example configuration files (debug mode)..."
                )
                self.load_configuration_files(
                    json_example, ini_example, is_example=True
                )
                return
            else:
                # Example files not found in debug mode
                QMessageBox.critical(
                    self,
                    "Debug Mode Error",
                    "Debug mode requested but example files not found.\n\n"
                    f"Expected files:\n"
                    f"• {json_example}\n"
                    f"• {ini_example}\n\n"
                    "Proceeding to game detection.", # Changed message
                )
        # Removed automatic loading of example files in normal mode.
        # elif json_example.exists() and ini_example.exists():
        #     # Normal mode: check for example files to ensure the app works correctly
        #     self.logger.info("Loading example configuration files...")
        #     self.load_configuration_files(json_example, ini_example, is_example=True)
        #     return

        # Try to find game installation
        # self.status_label.setText("Detecting game installation...") # REMOVED status_label
        self.logger.info("Detecting game installation...")  # Log instead
        game_path = None

        # First try saved path
        saved_path = self.settings_manager.load_game_path()
        if saved_path and self.game_detector.validate_game_installation(saved_path):
            game_path = saved_path
        else:
            # Try auto-detection
            detected_path = self.game_detector.find_game_installation()
            if detected_path:
                game_path = detected_path
                self.settings_manager.save_game_path(game_path)

        if game_path:
            self.load_configuration(game_path)
        else:
            # self.status_label.setText("Game not found - use File > Open Game Folder") # REMOVED status_label
            self.logger.warning(
                "Game not found - use File > Open Game Folder"
            )  # Log instead
            # self.game_path_label.setText("No game path") # REMOVED game_path_label
            # Show message about manual selection
            QMessageBox.information(
                self,
                "Game Not Found",
                "Le Mans Ultimate installation was not found automatically.\n\n"
                "Please use File > Open Game Folder to manually select your game installation.",
            )
            # Show startup info dialog even if game not found initially
            self.show_startup_info_dialog(None, None, None, False)


    def load_configuration_files(
        self, json_file: Path, ini_file: Path, is_example: bool = False
    ) -> None:
        """
        Load configuration from specific JSON and INI files.

        Args:
            json_file: Path to JSON settings file
            ini_file: Path to INI config file
            is_example: Whether these are example files
        """
        try:
            # self.status_label.setText("Loading configuration...") # REMOVED status_label
            self.logger.info("Loading configuration...")  # Log instead

            # Check if files exist
            if not json_file.exists():
                raise FileNotFoundError(f"JSON file not found: {json_file}")
            if not ini_file.exists():
                raise FileNotFoundError(f"INI file not found: {ini_file}")

            # Load configuration
            if self.config_model.load_configuration(json_file, ini_file):
                # Initialize configuration manager if not using example files (DISABLED - using ProfileManager instead)
                # if not is_example:
                #     config_dir = json_file.parent
                #     self.config_manager = ConfigurationManager(config_dir)

                # Update UI
                self.populate_categories()
                self.update_apply_button()

                if not is_example:
                    self.update_saved_profiles()

                # Update status
                field_count = len(self.config_model.field_states)
                status_text = f"Loaded {field_count} fields"
                if is_example:
                    if self.debug_mode:
                        status_text += " from example files (debug mode)"
                    else:
                        status_text += " from example files"
                # self.status_label.setText(status_text) # REMOVED status_label
                self.logger.info(status_text)  # Log instead

                # if is_example: # REMOVED game_path_label
                #     if self.debug_mode:
                #         self.game_path_label.setText("Example Configuration (Debug Mode)")
                #     else:
                #         self.game_path_label.setText("Example Configuration")
                # else:
                #     self.game_path_label.setText(str(json_file.parent.parent))

                # Initialize search indexer
                self.search_indexer.build_index(self.config_model)
                # SearchWidget is now in ConfigPanel, which will handle setting the indexer
                # if self.search_widget:
                #     self.search_widget.set_search_indexer(self.search_indexer)
                
                # Update configuration panel
                if self.config_panel:
                    display_path = (
                        "Example Configuration"
                        if is_example
                        else str(json_file.parent.parent.parent) # game root path
                    )
                    if is_example:
                        self.current_loaded_config_name = "Example Configuration"
                        self.current_loaded_config_is_profile = True
                    else:
                        self.current_loaded_config_name = display_path
                        self.current_loaded_config_is_profile = False
                    
                    self.config_panel.update_current_info(
                        self.current_loaded_config_name,
                        self.config_model.change_count,
                        self.current_loaded_config_is_profile
                    )

                # Emit signal
                self.configuration_loaded.emit()

                self.logger.info(
                    f"Successfully loaded configuration from {json_file} and {ini_file}"
                )
                
                # Check profile synchronization (only for actual game files, not examples)
                if not is_example:
                    self.check_profile_sync(json_file, ini_file)
                
                # Determine game_path_used for the dialog
                game_path_used = None
                if not is_example and self.config_model.json_file_path:
                    # For actual game files, game_path is two levels up from settings.json's parent
                    # UserData/player/Settings.JSON -> UserData -> Game Root
                    game_path_used = self.config_model.json_file_path.parent.parent.parent
                elif is_example and self.config_model.json_file_path:
                     game_path_used = self.config_model.json_file_path.parent # 'example' folder

                self.show_startup_info_dialog(json_file, ini_file, game_path_used, is_example)
            else:
                raise Exception("Failed to load configuration files")
                self.show_startup_info_dialog(None, None, None, False) # Show dialog on failure too

        except Exception as e:
            # Use error handler for better user experience
            context = ErrorContext(
                operation="load configuration",
                file_path=json_file.parent,
                user_action="initialize application",
            )

            error_response = self.error_handler.handle_error(e, context)
            selected_recovery = ErrorDialog.show_error(error_response, self)

            if selected_recovery and selected_recovery.name == "Browse for File":
                # User wants to browse for game folder
                self.browse_for_game()
            else:
                # self.status_label.setText("Failed to load configuration") # REMOVED status_label
                self.logger.error("Failed to load configuration")  # Log instead
                self.show_startup_info_dialog(None, None, json_file.parent if json_file else None, False)


    def load_configuration(self, game_path: Path) -> None:
        """
        Load configuration from game path.

        Args:
            game_path: Path to game installation
        """
        try:
            # Get UserData directory
            user_data_dir = self.game_detector.get_user_data_directory(game_path)
            if not user_data_dir:
                self.logger.error(f"Could not determine UserData directory for {game_path}")
                QMessageBox.critical(
                    self,
                    "Configuration Error",
                    f"Could not determine the UserData directory for the game at:\n{game_path}",
                )
                return

            json_file = user_data_dir / "player" / "Settings.JSON"
            ini_file = user_data_dir / "Config_DX11.ini"

            # Use the new method to load configuration files
            self.load_configuration_files(json_file, ini_file, is_example=False)

        except Exception as e:
            # Use error handler for better user experience
            context = ErrorContext(
                operation="load configuration",
                file_path=game_path,
                user_action="initialize application",
            )

            error_response = self.error_handler.handle_error(e, context)
            selected_recovery = ErrorDialog.show_error(error_response, self)

            if selected_recovery and selected_recovery.name == "Browse for File":
                # User wants to browse for game folder
                self.browse_for_game()
            else:
                # self.status_label.setText("Failed to load configuration") # REMOVED status_label
                self.logger.error("Failed to load configuration")  # Log instead
                self.show_startup_info_dialog(None, None, game_path, False)

    def populate_categories(self) -> None:
        """Populate the category tabs with configuration data."""
        if self.category_tabs is None or self.config_model is None:
            self.logger.warning("populate_categories: category_tabs or config_model is None. Skipping.")
            return
        
        self.logger.info("populate_categories: Fetching categories from model...")
        categories = self.config_model.get_categories()
        self.logger.info(f"populate_categories: Fetched {len(categories) if categories else 'no'} categories. Populating tabs...")
        self.category_tabs.populate_categories(categories, self.config_model)
        self.logger.info("populate_categories: Tabs populated.")
    
    def browse_for_game(self) -> None:
        """Browse for game installation folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Le Mans Ultimate Installation Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            game_path = Path(folder)
            if self.game_detector.validate_game_installation(game_path):
                self.settings_manager.save_game_path(game_path)
                self.load_configuration(game_path)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Game Folder",
                    "The selected folder does not appear to contain a valid "
                    "Le Mans Ultimate installation.\n\n"
                    "Please select the main game folder that contains the "
                    "UserData/player directory with settings.json and Config_DX11.ini files.",
                )

    def reload_configuration(self) -> None:
        """Reload configuration from disk."""
        if self.config_model.has_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Reloading will discard them.\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.logger.info("Reloading configuration...")
        # Get current game path and reload
        game_path = self.settings_manager.load_game_path()
        if game_path:
            self.logger.info(f"Reloading from saved game path: {game_path}")
            self.load_configuration(game_path)
        else:
            self.logger.info("No saved game path, re-initializing configuration.")
            self.initialize_configuration()
        self.logger.info("Configuration reload process finished.")

    def perform_search(self, query: str) -> None:
        """
        Perform search and highlight results.

        Args:
            query: Search query
        """
        if not self.config_model:
            return

        # Use search indexer for better performance
        if self.search_indexer.index:
            search_results = self.search_indexer.search_with_index(query)
            results = [result.field_path for result in search_results]
            # Sort results by tab order and field order within tabs
            results = self._sort_results_by_tab_order(results)
        else:
            # Fallback to model search
            results = self.config_model.search_fields(query)
            results = self._sort_results_by_tab_order(results)

        if self.category_tabs:
            self.category_tabs.highlight_search_results(results)

        # Update search widget with results
        search_widget = self.config_panel.search_widget if self.config_panel else None
        if search_widget:
            search_widget.update_search_results(results)
            # Sync navigation position with category tabs
            if self.category_tabs and results:
                current, total = self.category_tabs.get_current_search_position()
                search_widget.current_index = current - 1 if current > 0 else 0

        # Update status
        # self.status_label.setText(f"Search: {len(results)} results for '{query}'") # REMOVED status_label
        self.logger.info(f"Search: {len(results)} results for '{query}'")  # Log instead

    def on_search_performed(self, query: str) -> None:
        """Handle search performed from search widget."""
        self.perform_search(query)

    def on_search_navigation(self, direction: int) -> None:
        """
        Handle search navigation from search widget.

        Args:
            direction: 1 for next, -1 for previous
        """
        if not self.category_tabs:
            return

        if direction > 0:
            success = self.category_tabs.navigate_to_next_result()
        else:
            success = self.category_tabs.navigate_to_previous_result()

        search_widget = self.config_panel.search_widget if self.config_panel else None
        if success and search_widget:
            # Update search widget with current position
            current, total = self.category_tabs.get_current_search_position()
            if total > 0:
                search_widget.current_index = current - 1
                search_widget.current_results = (
                    self.category_tabs.highlighted_fields
                )
                search_widget.update_result_counter()
                search_widget.update_navigation_buttons(True)

    def clear_search(self) -> None:
        """Clear search results."""
        if self.category_tabs:
            self.category_tabs.clear_search_results()
        # self.status_label.setText("Search cleared") # REMOVED status_label
        self.logger.info("Search cleared")  # Log instead

    def _sort_results_by_tab_order(self, results: List[str]) -> List[str]:
        """
        Sort search results by tab order and field order within tabs.

        Args:
            results: List of field paths

        Returns:
            Sorted list of field paths
        """
        if not self.category_tabs or not self.config_model:
            return results

        # Get all categories with their field lists in original order
        categories = self.config_model.get_categories()

        # Create a mapping of field_path to (tab_index, field_index_in_tab)
        field_order_map = {}

        # Get tab order and map to original category names
        for tab_index in range(self.category_tabs.count()):
            tab_name = self.category_tabs.tabText(tab_index)

            # Find matching category in the configuration model
            category_field_list = None

            # Special handling for DX11 tab
            if tab_name == "Config_DX11.ini":
                # Collect all DX11 fields
                dx11_fields = []
                for category_name, field_list in categories.items():
                    if "DX11" in category_name:
                        dx11_fields.extend(field_list)
                category_field_list = dx11_fields
            elif tab_name == "Misc":
                # Collect all fields from categories with less than 8 fields
                misc_fields = []
                for category_name, field_list in categories.items():
                    if "DX11" not in category_name and len(field_list) < 8:
                        misc_fields.extend(field_list)
                category_field_list = misc_fields
            else:
                # Handle JSON categories
                for category_name, field_list in categories.items():
                    if "DX11" not in category_name:  # Skip DX11 categories
                        # Extract original category name from the full category name
                        original_category = category_name
                        if original_category.startswith("JSON - "):
                            original_category = original_category[7:]

                        # Convert to PascalCase for comparison
                        pascal_category = "".join(
                            word.capitalize()
                            for word in original_category.replace("_", " ")
                            .replace("-", " ")
                            .split()
                        )

                        # Match with tab name
                        if tab_name == pascal_category:
                            category_field_list = field_list
                            break

            if category_field_list:
                # Map each field in this category to its position
                for field_index, field_path in enumerate(category_field_list):
                    if field_path in results:
                        field_order_map[field_path] = (tab_index, field_index)

        # Sort results using the order mapping
        def sort_key(field_path):
            return field_order_map.get(
                field_path, (999, 999)
            )  # Put unmapped fields at end

        return sorted(results, key=sort_key)

    def apply_changes(self) -> None:
        """Apply all pending changes."""
        if not self.config_model.has_changes:
            return

        try:
            self.apply_button.set_saving_state()
            success, error_msg = self.config_model.apply_changes()

            if success:
                self.apply_button.set_success_state()
                # self.status_label.setText("Changes applied successfully") # REMOVED status_label
                self.logger.info("Changes applied successfully")  # Log instead
                self.changes_applied.emit()
                
                # Update active profile if one exists
                self.update_active_profile_after_changes()

                # Reset button state after delay
                QTimer.singleShot(2000, self.update_apply_button)
            else:
                self.apply_button.set_error_state(error_msg or "Unknown error")

                # Use error handler for apply failures
                context = ErrorContext(
                    operation="apply changes", user_action="save configuration changes"
                )

                # Create a mock exception for the error handler
                apply_error = Exception(
                    error_msg or "Unknown error occurred while applying changes"
                )
                error_response = self.error_handler.handle_error(apply_error, context)

                selected_recovery = ErrorDialog.show_error(error_response, self)
                if selected_recovery and selected_recovery.name == "Retry":
                    # User wants to retry
                    QTimer.singleShot(1000, self.apply_changes)

        except Exception as e:
            self.apply_button.set_error_state(f"Error: {e}")

            # Use error handler for exceptions
            context = ErrorContext(
                operation="apply changes", user_action="save configuration changes"
            )

            error_response = self.error_handler.handle_error(e, context)
            selected_recovery = ErrorDialog.show_error(error_response, self)

            if selected_recovery and selected_recovery.name == "Retry":
                # User wants to retry
                QTimer.singleShot(1000, self.apply_changes)

    def revert_all_changes(self) -> None:
        """Revert all pending changes."""
        if not self.config_model.has_changes:
            return

        reply = QMessageBox.question(
            self,
            "Revert Changes",
            f"Are you sure you want to revert all {self.config_model.change_count} pending changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            reverted_count = self.config_model.revert_all_changes()
            # self.status_label.setText(f"Reverted {reverted_count} changes") # REMOVED status_label
            self.logger.info(f"Reverted {reverted_count} changes")  # Log instead

    def update_saved_profiles(self) -> None:
        """Update the list of saved profiles in the panel."""
        if not self.config_panel:
            return

        try:
            saved_profiles = self.profile_manager.list_profiles()
            self.config_panel.populate_saved_configurations(saved_profiles)
        except Exception as e:
            self.logger.error(f"Error updating saved profiles: {e}")

    def save_configuration(self) -> None:
        """Save current configuration as a profile."""
        if not self.config_model.json_file_path or not self.config_model.ini_file_path:
            QMessageBox.warning(
                self,
                "No Configuration Loaded",
                "No configuration files are currently loaded. Please load a game configuration first.",
            )
            return

        try:
            # Get existing profiles
            existing_configs = self.profile_manager.list_profiles()

            # Show save dialog
            dialog = SaveConfigurationDialog(existing_configs, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config_name = dialog.get_configuration_name()
                # config_description = dialog.get_configuration_description() # Description removed

                if config_name:
                    # Save profile
                    json_file = self.config_model.json_file_path
                    ini_file = self.config_model.ini_file_path
                    
                    if self.profile_manager.create_profile(config_name, json_file, ini_file):
                        # Set as active profile
                        self.profile_manager.set_active_profile(config_name)
                        
                        self.logger.info(f"Saved profile: {config_name}")
                        self.update_saved_profiles()
                        
                        # Update UI to show the new active profile
                        if self.config_panel:
                            self.current_loaded_config_name = config_name
                            self.current_loaded_config_is_profile = True
                            self.config_panel.update_current_info(
                                config_name, self.config_model.change_count, is_profile=True
                            )
                        
                        QMessageBox.information(
                            self,
                            "Profile Saved",
                            f"Profile '{config_name}' has been saved and set as active."
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Save Failed",
                            f"Failed to save profile '{config_name}'",
                        )
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Error saving configuration:\n\n{str(e)}"
            )

    def load_configuration_from_panel(self, config_name: str) -> None:
        """
        Load a saved profile.

        Args:
            config_name: Name of profile to load
        """

        # Check for unsaved changes
        if self.config_model.has_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have {self.config_model.change_count} unsaved changes.\n\n"
                "Loading a different profile will discard them.\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            # Load profile to current game files
            if not self.config_model.json_file_path or not self.config_model.ini_file_path:
                QMessageBox.warning(
                    self,
                    "No Configuration Loaded",
                    "No game configuration is currently loaded. Please load a game first."
                )
                return
                
            json_file = self.config_model.json_file_path
            ini_file = self.config_model.ini_file_path
            
            success = self.profile_manager.load_profile(config_name, json_file, ini_file)

            if success:
                # Reload the configuration model with updated files
                if self.config_model.load_configuration(json_file, ini_file):
                    # Update UI
                    self.populate_categories()
                    self.update_apply_button()

                    self.logger.info(f"Loaded profile: {config_name}")

                    # Update configuration panel
                    if self.config_panel:
                        self.current_loaded_config_name = config_name
                        self.current_loaded_config_is_profile = True
                        self.config_panel.update_current_info(
                            config_name, self.config_model.change_count, is_profile=True
                        )
                        
                    QMessageBox.information(
                        self,
                        "Profile Loaded",
                        f"Profile '{config_name}' has been loaded and set as active."
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Load Error",
                        f"Failed to reload configuration model after loading profile '{config_name}'",
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Load Failed",
                    f"Failed to load profile '{config_name}'",
                )

        except Exception as e:
            QMessageBox.critical(
                self, "Load Error", f"Error loading configuration:\n\n{str(e)}"
            )

    def compare_configuration(self, config_name: str) -> None:
        """
        Compare current configuration with selected one.

        Args:
            config_name: Name of configuration to compare with
        """
        if not self.config_manager:
            return

        try:
            # Get paths to configuration files
            json_path, ini_path = self.config_manager.get_configuration_files(
                config_name
            )

            if not json_path.exists() or not ini_path.exists():
                QMessageBox.warning(
                    self,
                    "Configuration Not Found",
                    f"Configuration files for '{config_name}' not found.",
                )
                return

            # Load selected configuration data
            from ..core.parsers.json_parser import JsonWithCommentsParser
            from ..core.parsers.ini_parser import IniParser

            json_parser = JsonWithCommentsParser()
            ini_parser = IniParser()

            selected_json = json_parser.parse_file(json_path)
            selected_ini = ini_parser.parse_file(ini_path)

            # Combine current and selected configuration data
            current_data = {}
            selected_data = {}

            # Build current data with current values (including modifications)
            for field_path in self.config_model.field_states.keys():
                field_info = self.config_model.get_field_info(field_path)
                if field_info:
                    # Create a copy of field_info with current value
                    from copy import copy
                    current_field_info = copy(field_info)
                    current_field_info.value = self.config_model.get_field_value(field_path)
                    current_data[field_path] = current_field_info

            # Add selected configuration JSON fields
            if selected_json:
                selected_data.update(selected_json.fields)

            # Add selected configuration INI fields (with prefix)
            if selected_ini:
                for field_path, field_info in selected_ini.fields.items():
                    selected_data[f"ini.{field_path}"] = field_info

            # Show comparison dialog
            dialog = ComparisonDialog(
                current_data, selected_data, "Current Configuration", config_name, self
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Comparison Error", f"Error comparing configurations:\n\n{str(e)}"
            )

    def delete_configuration(self, config_name: str) -> None:
        """
        Delete a saved configuration.

        Args:
            config_name: Name of configuration to delete
        """
        if not self.config_manager:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Configuration",
            f"Are you sure you want to delete the configuration '{config_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.config_manager.delete_configuration(config_name):
                    # self.status_label.setText(f"Deleted configuration: {config_name}") # REMOVED status_label
                    self.logger.info(
                        f"Deleted configuration: {config_name}"
                    )  # Log instead
                    self.update_saved_configurations()
                else:
                    QMessageBox.critical(
                        self,
                        "Delete Failed",
                        f"Failed to delete configuration '{config_name}'",
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Delete Error", f"Error deleting configuration:\n\n{str(e)}"
                )

    def export_configuration(self) -> None:
        """Export a saved configuration to .lmuconfig file."""
        if not self.config_manager or not self.config_panel:
            QMessageBox.warning(
                self,
                "No Configuration Manager",
                "Configuration manager not initialized. Please load a game configuration first.",
            )
            return

        # Get selected configuration
        selected_config = self.config_panel.get_selected_configuration()
        if not selected_config:
            QMessageBox.information(
                self,
                "No Configuration Selected",
                "Please select a configuration to export from the list.",
            )
            return

        # Get export file path
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export Configuration '{selected_config}'",
            f"{selected_config}.lmuconfig",
            "LMU Configuration Files (*.lmuconfig);;All Files (*)",
        )

        if export_path:
            try:
                if self.config_porter.export_configuration(
                    self.config_manager, selected_config, Path(export_path)
                ):
                    QMessageBox.information(
                        self,
                        "Export Successful",
                        f"Configuration '{selected_config}' has been exported to:\n{export_path}",
                    )
                    # self.status_label.setText(f"Exported configuration: {selected_config}") # REMOVED status_label
                    self.logger.info(
                        f"Exported configuration: {selected_config}"
                    )  # Log instead
                else:
                    QMessageBox.critical(
                        self,
                        "Export Failed",
                        f"Failed to export configuration '{selected_config}'",
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error", f"Error exporting configuration:\n\n{str(e)}"
                )

    def import_configuration(self) -> None:
        """Import a configuration from .lmuconfig file."""
        if not self.config_manager:
            QMessageBox.warning(
                self,
                "No Configuration Manager",
                "Configuration manager not initialized. Please load a game configuration first.",
            )
            return

        # Get import file path
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            "",
            "LMU Configuration Files (*.lmuconfig);;All Files (*)",
        )

        if import_path:
            try:
                # Validate import file
                validation = self.config_porter.validate_import_file(Path(import_path))
                if not validation.is_valid:
                    QMessageBox.critical(
                        self,
                        "Invalid Import File",
                        f"Cannot import configuration:\n\n{validation.error_message}",
                    )
                    return

                # Get configuration name from metadata
                original_name = validation.metadata.get(
                    "configuration_name", "imported_config"
                )
                description = validation.metadata.get("description", "")

                # Show import confirmation
                message = f"Import configuration '{original_name}'?"
                if description:
                    message += f"\n\nDescription: {description}"

                existing_configs = self.config_manager.get_saved_configurations()
                if original_name in existing_configs:
                    message += "\n\nNote: A configuration with this name already exists and will be renamed."

                reply = QMessageBox.question(
                    self,
                    "Confirm Import",
                    message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Import configuration
                    success, result = self.config_porter.import_configuration(
                        Path(import_path), self.config_manager
                    )

                    if success:
                        imported_name = result
                        QMessageBox.information(
                            self,
                            "Import Successful",
                            f"Configuration imported successfully as '{imported_name}'",
                        )
                        # self.status_label.setText(f"Imported configuration: {imported_name}") # REMOVED status_label
                        self.logger.info(
                            f"Imported configuration: {imported_name}"
                        )  # Log instead
                        self.update_saved_configurations()
                    else:
                        QMessageBox.critical(
                            self,
                            "Import Failed",
                            f"Failed to import configuration:\n\n{result}",
                        )

            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error", f"Error importing configuration:\n\n{str(e)}"
                )

    # Keyboard shortcut methods
    def on_shortcut_triggered(self, action_name: str, shortcut_key: str) -> None:
        """
        Handle shortcut triggered event.

        Args:
            action_name: Name of the action
            shortcut_key: Key sequence that was pressed
        """
        self.logger.debug(f"Shortcut triggered: {action_name} ({shortcut_key})")
        # self.status_label.setText(f"Shortcut: {action_name}") # REMOVED status_label
        self.logger.info(f"Shortcut: {action_name}")  # Log instead

    def next_category_tab(self) -> None:
        """Switch to next category tab."""
        if self.category_tabs:
            current_index = self.category_tabs.currentIndex()
            count = self.category_tabs.count()
            if count > 0:
                next_index = (current_index + 1) % count
                self.category_tabs.setCurrentIndex(next_index)

    def prev_category_tab(self) -> None:
        """Switch to previous category tab."""
        if self.category_tabs:
            current_index = self.category_tabs.currentIndex()
            count = self.category_tabs.count()
            if count > 0:
                prev_index = (current_index - 1) % count
                self.category_tabs.setCurrentIndex(prev_index)

    def goto_tab_1(self) -> None:
        """Switch to first tab."""
        if self.category_tabs and self.category_tabs.count() > 0:
            self.category_tabs.setCurrentIndex(0)

    def goto_tab_2(self) -> None:
        """Switch to second tab."""
        if self.category_tabs and self.category_tabs.count() > 1:
            self.category_tabs.setCurrentIndex(1)

    def goto_tab_3(self) -> None:
        """Switch to third tab."""
        if self.category_tabs and self.category_tabs.count() > 2:
            self.category_tabs.setCurrentIndex(2)

    def goto_tab_4(self) -> None:
        """Switch to fourth tab."""
        if self.category_tabs and self.category_tabs.count() > 3:
            self.category_tabs.setCurrentIndex(3)

    def goto_tab_5(self) -> None:
        """Switch to fifth tab."""
        if self.category_tabs and self.category_tabs.count() > 4:
            self.category_tabs.setCurrentIndex(4)

    def compare_current_config(self) -> None:
        """Compare current configuration with selected one."""
        if self.config_panel:
            selected_config = self.config_panel.get_selected_configuration()
            if selected_config:
                self.compare_configuration(selected_config)
            else:
                # self.status_label.setText("No configuration selected for comparison") # REMOVED status_label
                self.logger.info(
                    "No configuration selected for comparison"
                )  # Log instead

    def show_help(self) -> None:
        """Show help information."""
        if not self.shortcut_manager:
            return

        # Create help dialog with shortcut list
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)

        # Create help text
        help_text = QTextEdit()
        help_text.setReadOnly(True)

        shortcuts_html = "<h2>Keyboard Shortcuts</h2><table border='1' cellpadding='5'>"
        shortcuts_html += "<tr><th>Action</th><th>Shortcut</th></tr>"

        # Group shortcuts by category
        categories = {
            "File Operations": [
                "save_config",
                "save_config_as",
                "open_game",
                "reload",
                "quit",
            ],
            "Edit Operations": [
                "find",
                "find_next",
                "find_previous",
                "revert_all",
                "apply_changes",
            ],
            "Navigation": [
                "next_tab",
                "prev_tab",
                "tab_1",
                "tab_2",
                "tab_3",
                "tab_4",
                "tab_5",
            ],
            "Configuration": ["export_config", "import_config", "compare_config"],
            "General": ["escape", "help"],
        }

        for category, actions in categories.items():
            shortcuts_html += f"<tr><td colspan='2'><b>{category}</b></td></tr>"
            for action in actions:
                description = self.shortcut_manager.get_shortcut_description(action)
                shortcut = self.shortcut_manager.get_shortcut_text(action)
                if description and shortcut:
                    shortcuts_html += f"<tr><td>{description}</td><td><code>{shortcut}</code></td></tr>"

        shortcuts_html += "</table>"
        help_text.setHtml(shortcuts_html)
        layout.addWidget(help_text)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def on_model_changed(self, event: str, *args) -> None:
        """
        Handle model change events.

        Args:
            event: Event name
            *args: Event arguments
        """
        if event == "field_changed":
            self.update_apply_button()
            field_path = args[0] if args else "unknown"
            # self.status_label.setText(f"Modified: {field_path}") # REMOVED status_label
            self.logger.info(f"Modified: {field_path}")  # Log instead
        elif event == "field_reverted":
            self.update_apply_button()
            field_path = args[0] if args else "unknown"
            # self.status_label.setText(f"Reverted: {field_path}") # REMOVED status_label
            self.logger.info(f"Reverted: {field_path}")  # Log instead
        elif event == "all_changes_reverted":
            self.update_apply_button()
            count = args[0] if args else 0
            # self.status_label.setText(f"Reverted {count} changes") # REMOVED status_label
            self.logger.info(f"Reverted {count} changes")  # Log instead
        elif event == "changes_applied":
            self.update_apply_button()
            # Update configuration panel with new change count
            if self.config_panel:
                config_id = self.current_loaded_config_name
                is_prof = self.current_loaded_config_is_profile
                if not config_id: # Fallback, should ideally not happen
                    config_id = str(self.config_manager.config_dir.parent) if self.config_manager else "Unknown"
                    is_prof = False
                self.config_panel.update_current_info(
                    config_id,
                    self.config_model.change_count,
                    is_prof
                )
            # Refresh field widgets to show non-modified state
            if self.category_tabs:
                self.category_tabs.refresh_all_fields()

    def update_apply_button(self) -> None:
        """Update the apply button state."""
        if self.apply_button:
            self.apply_button.update_state(self.config_model.change_count)

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About LMU Configuration Editor",
            "LMU Configuration Editor v1.0.0\n\n"
            "A desktop application for managing Le Mans Ultimate game configuration files.\n\n"
            "Phase 2: User Interface Foundation\n"
            "Built with PyQt6 and Python 3.12+",
        )

    def load_window_geometry(self) -> None:
        """Load window geometry from settings."""
        geometry = self.qt_settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.qt_settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

    def save_window_geometry(self) -> None:
        """Save window geometry to settings."""
        self.qt_settings.setValue("geometry", self.saveGeometry())
        self.qt_settings.setValue("windowState", self.saveState())

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle window resize event to maintain splitter ratio."""
        if hasattr(self, 'splitter') and self.splitter and self.splitter.count() == 2:
            # Allow a very small delay for the layout to settle before calculating sizes
            # This can sometimes help if direct resize calculations are off due to pending layout updates
            QTimer.singleShot(0, self._adjust_splitter_sizes)
        super().resizeEvent(event)

    def _adjust_splitter_sizes(self) -> None:
        """Adjusts splitter sizes. Called by resizeEvent via QTimer."""
        if hasattr(self, 'splitter') and self.splitter and self.splitter.count() == 2:
            # Check if widgets are visible and have a width, otherwise splitter width might be 0
            if self.splitter.width() > 0 :
                total_width = self.splitter.width()
                
                # Get current sizes to respect minimums if possible, though stretch factors should handle this
                # current_sizes = self.splitter.sizes()
                
                left_width = int(total_width * 0.84)
                right_width = total_width - left_width # Ensure total width is maintained

                # Ensure minimum sizes are respected (QSplitter does this implicitly, but good to be aware)
                # min_left = self.category_tabs.minimumSizeHint().width() if self.category_tabs else 0
                # min_right = self.config_panel.minimumSizeHint().width() if self.config_panel else 0
                # if left_width < min_left:
                #     left_width = min_left
                #     right_width = total_width - left_width
                # if right_width < min_right and total_width - left_width >= min_right : # check if right can meet min
                #      right_width = min_right
                #      left_width = total_width - right_width
                # elif right_width < min_right: # if right cannot meet min, adjust left to give right its min
                #      left_width = total_width - min_right
                #      right_width = min_right


                if left_width > 0 and right_width > 0:
                     # Check if current sizes are already very close to target to avoid jitter
                    current_sizes = self.splitter.sizes()
                    if abs(current_sizes[0] - left_width) > 2 or abs(current_sizes[1] - right_width) > 2:
                        self.splitter.setSizes([left_width, right_width])
                # self.logger.debug(f"Splitter resize: total={total_width}, L={left_width}, R={right_width}, current={self.splitter.sizes()}")


    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Check for unsaved changes
        if self.config_model.has_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have {self.config_model.change_count} unsaved changes.\n\n"
                "Do you want to apply them before closing?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Apply changes
                success, error_msg = self.config_model.apply_changes()
                if not success:
                    QMessageBox.critical(
                        self,
                        "Apply Changes Failed",
                        f"Failed to apply changes:\n\n{error_msg}\n\n"
                        "Application will close without saving changes.",
                    )
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        # Save window geometry
        self.save_window_geometry()

        # Accept the close event
        event.accept()

    def open_settings_json_location(self) -> None:
        """Open the folder containing settings.json in the file explorer."""
        if self.config_model and self.config_model.json_file_path:
            settings_dir = self.config_model.json_file_path.parent
            if settings_dir.exists() and settings_dir.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_dir)))
                self.logger.info(f"Opened settings folder: {settings_dir}")
            else:
                self.logger.warning(f"Settings folder does not exist or is not a directory: {settings_dir}")
                QMessageBox.warning(
                    self,
                    "Folder Not Found",
                    f"The settings folder could not be found or is not accessible:\n{settings_dir}"
                )
        else:
            self.logger.warning("Cannot open settings folder: config model or json_file_path not available.")
            QMessageBox.information(
                self,
                "Location Unavailable",
                "Settings.JSON path is not currently loaded. Please load a configuration first."
            )

    def show_startup_info_dialog(self, json_path: Optional[Path], ini_path: Optional[Path], game_path_used: Optional[Path], is_example: bool) -> None:
        """Shows the startup information dialog."""
        dialog = StartupInfoDialog(json_path, ini_path, game_path_used, is_example, self)
        dialog.browse_requested.connect(self.browse_for_game)
        dialog.exec()

    def check_profile_sync(self, json_file: Path, ini_file: Path) -> None:
        """
        Check if current settings match the active profile and handle conflicts.
        
        Args:
            json_file: Current settings.json file
            ini_file: Current Config_DX11.ini file
        """
        try:
            files_match, active_profile, differences = self.profile_manager.compare_with_active_profile(
                json_file, ini_file
            )
            
            if not files_match and active_profile and differences:
                self.logger.info(f"Profile sync conflict detected with profile '{active_profile}': {differences}")
                
                # Show sync dialog
                choice = ProfileSyncDialog.show_sync_dialog(active_profile, differences, self)
                
                if choice == ProfileSyncChoice.UPDATE_PROFILE:
                    # Update profile with current settings
                    if self.profile_manager.update_profile(active_profile, json_file, ini_file):
                        self.logger.info(f"Profile '{active_profile}' updated with current settings")
                        QMessageBox.information(
                            self,
                            "Profile Updated",
                            f"Profile '{active_profile}' has been updated with your current settings."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Update Failed",
                            f"Failed to update profile '{active_profile}'. Please check the logs."
                        )
                
                elif choice == ProfileSyncChoice.UPDATE_SETTINGS:
                    # Update settings with profile
                    if self.profile_manager.load_profile(active_profile, json_file, ini_file):
                        self.logger.info(f"Settings updated with profile '{active_profile}'")
                        # Reload the configuration to reflect changes
                        self.reload_configuration()
                        QMessageBox.information(
                            self,
                            "Settings Updated",
                            f"Your settings have been updated with profile '{active_profile}'."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Update Failed",
                            f"Failed to load profile '{active_profile}'. Please check the logs."
                        )
                
                elif choice == ProfileSyncChoice.IGNORE:
                    # Clear active profile to avoid repeated conflicts
                    self.profile_manager.clear_active_profile()
                    self.logger.info("Profile sync conflict ignored, active profile cleared")
                
                # If user cancelled, do nothing
            
        except Exception as e:
            self.logger.error(f"Error during profile sync check: {e}")

    def update_active_profile_after_changes(self) -> None:
        """Update the active profile after changes are applied to game files."""
        try:
            active_profile = self.profile_manager.get_active_profile()
            if not active_profile:
                return  # No active profile, nothing to update
            
            # Get current game file paths
            if not self.config_model.json_file_path or not self.config_model.ini_file_path:
                self.logger.warning("Cannot update active profile: game file paths not available")
                return
            
            json_file = self.config_model.json_file_path
            ini_file = self.config_model.ini_file_path
            
            # Update the profile with current settings
            if self.profile_manager.update_profile(active_profile, json_file, ini_file):
                self.logger.info(f"Active profile '{active_profile}' updated automatically after applying changes")
            else:
                self.logger.error(f"Failed to update active profile '{active_profile}' after applying changes")
                
        except Exception as e:
            self.logger.error(f"Error updating active profile after changes: {e}")

def run_application() -> int:
    """
    Run the LMU Configuration Editor application.

    Returns:
        Exit code
    """
    app = QApplication(sys.argv)
    app.setApplicationName("LMU Configuration Editor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LMU Config Editor")

    # Create and show main window
    window = MainWindow()
    window.show()

    return app.exec()
