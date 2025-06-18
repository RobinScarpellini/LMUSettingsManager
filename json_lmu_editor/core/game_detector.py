"""
Game installation detection for Le Mans Ultimate.

This module handles automatic detection of LMU installation through Steam registry
scanning with fallback to manual selection.
"""

import sys
import re
from pathlib import Path
from typing import Optional, List
import logging


class GameDetector:
    """Detects Le Mans Ultimate game installation."""

    GAME_NAME = "Le Mans Ultimate"
    # REQUIRED_FILES are now checked explicitly due to different subdirectories
    # REQUIRED_FILES = ["Settings.JSON", "Config_DX11.ini"]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def find_game_installation(self) -> Optional[Path]:
        """
        Find Le Mans Ultimate installation directory.

        Returns:
            Path to game installation or None if not found
        """
        # Check if we're on Windows (Steam registry only available on Windows)
        if sys.platform != "win32":
            self.logger.info("Non-Windows platform detected, skipping Steam registry")
            return None

        try:
            steam_path = self.find_steam_installation()
            if not steam_path:
                self.logger.info("Steam installation not found")
                return None

            library_folders = self.get_steam_library_folders(steam_path)
            game_path = self.find_game_in_libraries(library_folders)

            if game_path and self.validate_game_installation(game_path):
                self.logger.info(f"Game found at: {game_path}")
                return game_path

        except Exception as e:
            self.logger.error(f"Error during game detection: {e}")

        return None

    def find_steam_installation(self) -> Optional[Path]:
        """
        Find Steam installation path from Windows registry.

        Returns:
            Path to Steam installation or None if not found
        """
        if sys.platform != "win32":
            return None

        try:
            import winreg

            # Try 64-bit registry first
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
            ]

            for hkey, subkey in registry_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                        steam_path = Path(steam_path)
                        if steam_path.exists():
                            self.logger.debug(f"Steam found at: {steam_path}")
                            return steam_path
                except (FileNotFoundError, OSError):
                    continue

        except ImportError:
            self.logger.warning("winreg module not available")

        return None

    def get_steam_library_folders(self, steam_path: Path) -> List[Path]:
        """
        Parse Steam library folders from libraryfolders.vdf.

        Args:
            steam_path: Path to Steam installation

        Returns:
            List of library folder paths
        """
        libraries = [steam_path / "steamapps"]  # Default library

        library_file = steam_path / "steamapps" / "libraryfolders.vdf"
        if not library_file.exists():
            self.logger.warning("libraryfolders.vdf not found")
            return libraries

        try:
            with open(library_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse VDF format for library paths
            # Look for "path" entries in the VDF
            path_pattern = r'"path"\s*"([^"]+)"'
            matches = re.findall(path_pattern, content)

            for match in matches:
                lib_path = Path(match) / "steamapps"
                if lib_path.exists() and lib_path not in libraries:
                    libraries.append(lib_path)
                    self.logger.debug(f"Found library: {lib_path}")

        except Exception as e:
            self.logger.error(f"Error parsing libraryfolders.vdf: {e}")

        return libraries

    def find_game_in_libraries(self, library_folders: List[Path]) -> Optional[Path]:
        """
        Search for Le Mans Ultimate in Steam library folders.

        Args:
            library_folders: List of Steam library paths

        Returns:
            Path to game installation or None if not found
        """
        for library in library_folders:
            common_path = library / "common"
            if not common_path.exists():
                continue

            # Look for exact game folder name
            game_path = common_path / self.GAME_NAME
            if game_path.exists() and game_path.is_dir():
                self.logger.debug(f"Found game directory: {game_path}")
                return game_path

            # Also check for variations (some games have different folder names)
            for folder in common_path.iterdir():
                if folder.is_dir() and "le mans" in folder.name.lower():
                    self.logger.debug(f"Found potential game directory: {folder}")
                    return folder

        return None

    def validate_game_installation(self, game_path: Path) -> bool:
        """
        Validate that the path contains a valid LMU installation.

        Args:
            game_path: Path to potential game directory

        Returns:
            True if valid installation, False otherwise
        """
        if not game_path.exists() or not game_path.is_dir():
            return False

        # Check for UserData directory
        user_data_dir = game_path / "UserData"
        if not user_data_dir.exists() or not user_data_dir.is_dir():
            self.logger.debug(f"UserData directory not found in {game_path}")
            return False

        # Check for Config_DX11.ini in UserData
        config_dx11_path = user_data_dir / "Config_DX11.ini"
        if not config_dx11_path.exists() or not config_dx11_path.is_file():
            self.logger.debug(
                f"Required file Config_DX11.ini not found in {user_data_dir}"
            )
            return False

        # Check for player subdirectory in UserData
        player_dir = user_data_dir / "player"
        if not player_dir.exists() or not player_dir.is_dir():
            self.logger.debug(f"UserData/player directory not found in {user_data_dir}")
            return False
            
        # Check for Settings.JSON in UserData/player
        settings_json_path = player_dir / "Settings.JSON"
        if not settings_json_path.exists() or not settings_json_path.is_file():
            self.logger.debug(
                f"Required file Settings.JSON not found in {player_dir}"
            )
            return False

        return True

    def get_user_data_directory(self, game_path: Path) -> Path:
        """
        Get the UserData directory for the game.

        Args:
            game_path: Path to game installation

        Returns:
            Path to UserData directory
        """
        return game_path / "UserData"
