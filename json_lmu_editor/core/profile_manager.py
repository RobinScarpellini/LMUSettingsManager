"""
Profile Management System for LMU Settings Manager.

Handles creating, saving, and managing user profiles in Documents/LMU Settings Manager.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging


class ProfileMetadata:
    """Metadata for a profile."""
    
    def __init__(self, name: str, created_date: datetime, last_modified: datetime, description: str = ""):
        self.name = name
        self.created_date = created_date
        self.last_modified = last_modified
        self.description = description
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "created_date": self.created_date.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProfileMetadata':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            created_date=datetime.fromisoformat(data["created_date"]),
            last_modified=datetime.fromisoformat(data["last_modified"]),
            description=data.get("description", "")
        )


class ProfileManager:
    """Manages user profiles in Documents/LMU Settings Manager."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Create profiles directory in user's Documents folder
        self.profiles_dir = Path.home() / "Documents" / "LMU Settings Manager"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Active profile tracking file
        self.active_profile_file = self.profiles_dir / "active_profile.json"
        
        self.logger.info(f"Profile manager initialized with directory: {self.profiles_dir}")
    
    def get_profiles_directory(self) -> Path:
        """Get the profiles directory path."""
        return self.profiles_dir
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        profiles = []
        for item in self.profiles_dir.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                profiles.append(item.name)
        return sorted(profiles)
    
    def get_profile_metadata(self, profile_name: str) -> Optional[ProfileMetadata]:
        """Get metadata for a profile."""
        profile_dir = self.profiles_dir / profile_name
        metadata_file = profile_dir / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ProfileMetadata.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load metadata for profile {profile_name}: {e}")
            return None
    
    def create_profile(self, profile_name: str, json_file: Path, ini_file: Path, description: str = "") -> bool:
        """
        Create a new profile from current settings files.
        
        Args:
            profile_name: Name of the profile
            json_file: Path to settings.json file
            ini_file: Path to Config_DX11.ini file
            description: Optional description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create profile directory
            profile_dir = self.profiles_dir / profile_name
            profile_dir.mkdir(exist_ok=True)
            
            # Copy files
            if json_file.exists():
                shutil.copy2(json_file, profile_dir / "settings.json")
            if ini_file.exists():
                shutil.copy2(ini_file, profile_dir / "Config_DX11.ini")
            
            # Create metadata
            now = datetime.now()
            metadata = ProfileMetadata(profile_name, now, now, description)
            
            metadata_file = profile_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            self.logger.info(f"Profile '{profile_name}' created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create profile '{profile_name}': {e}")
            return False
    
    def update_profile(self, profile_name: str, json_file: Path, ini_file: Path) -> bool:
        """
        Update an existing profile with current settings.
        
        Args:
            profile_name: Name of the profile
            json_file: Path to settings.json file
            ini_file: Path to Config_DX11.ini file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_dir = self.profiles_dir / profile_name
            if not profile_dir.exists():
                return False
            
            # Copy files
            if json_file.exists():
                shutil.copy2(json_file, profile_dir / "settings.json")
            if ini_file.exists():
                shutil.copy2(ini_file, profile_dir / "Config_DX11.ini")
            
            # Update metadata
            metadata = self.get_profile_metadata(profile_name)
            if metadata:
                metadata.last_modified = datetime.now()
                metadata_file = profile_dir / "metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata.to_dict(), f, indent=2)
            
            self.logger.info(f"Profile '{profile_name}' updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update profile '{profile_name}': {e}")
            return False
    
    def load_profile(self, profile_name: str, json_file: Path, ini_file: Path) -> bool:
        """
        Load a profile to the game settings files.
        
        Args:
            profile_name: Name of the profile
            json_file: Target path for settings.json
            ini_file: Target path for Config_DX11.ini
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_dir = self.profiles_dir / profile_name
            if not profile_dir.exists():
                return False
            
            # Copy files
            profile_json = profile_dir / "settings.json"
            profile_ini = profile_dir / "Config_DX11.ini"
            
            if profile_json.exists():
                shutil.copy2(profile_json, json_file)
            if profile_ini.exists():
                shutil.copy2(profile_ini, ini_file)
            
            # Set as active profile
            self.set_active_profile(profile_name)
            
            self.logger.info(f"Profile '{profile_name}' loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load profile '{profile_name}': {e}")
            return False
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        Delete a profile.
        
        Args:
            profile_name: Name of the profile to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_dir = self.profiles_dir / profile_name
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
                
                # Clear active profile if it was the deleted one
                if self.get_active_profile() == profile_name:
                    self.clear_active_profile()
                
                self.logger.info(f"Profile '{profile_name}' deleted successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete profile '{profile_name}': {e}")
            return False
    
    def set_active_profile(self, profile_name: str) -> None:
        """Set the active profile."""
        try:
            active_data = {
                "profile_name": profile_name,
                "last_activated": datetime.now().isoformat()
            }
            
            with open(self.active_profile_file, 'w', encoding='utf-8') as f:
                json.dump(active_data, f, indent=2)
                
            self.logger.info(f"Active profile set to '{profile_name}'")
            
        except Exception as e:
            self.logger.error(f"Failed to set active profile '{profile_name}': {e}")
    
    def get_active_profile(self) -> Optional[str]:
        """Get the name of the active profile."""
        try:
            if not self.active_profile_file.exists():
                return None
                
            with open(self.active_profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("profile_name")
                
        except Exception as e:
            self.logger.error(f"Failed to get active profile: {e}")
            return None
    
    def clear_active_profile(self) -> None:
        """Clear the active profile."""
        try:
            if self.active_profile_file.exists():
                self.active_profile_file.unlink()
            self.logger.info("Active profile cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear active profile: {e}")
    
    def compare_with_active_profile(self, json_file: Path, ini_file: Path) -> Tuple[bool, Optional[str], List[str]]:
        """
        Compare current settings with active profile.
        
        Args:
            json_file: Current settings.json file
            ini_file: Current Config_DX11.ini file
            
        Returns:
            Tuple of (files_match, active_profile_name, differences)
        """
        active_profile = self.get_active_profile()
        if not active_profile:
            return True, None, []
        
        profile_dir = self.profiles_dir / active_profile
        if not profile_dir.exists():
            return True, active_profile, []
        
        differences = []
        
        # Compare JSON file
        profile_json = profile_dir / "settings.json"
        if profile_json.exists() and json_file.exists():
            if not self._files_identical(json_file, profile_json):
                differences.append("settings.json")
        elif profile_json.exists() != json_file.exists():
            differences.append("settings.json (missing)")
        
        # Compare INI file
        profile_ini = profile_dir / "Config_DX11.ini"
        if profile_ini.exists() and ini_file.exists():
            if not self._files_identical(ini_file, profile_ini):
                differences.append("Config_DX11.ini")
        elif profile_ini.exists() != ini_file.exists():
            differences.append("Config_DX11.ini (missing)")
        
        files_match = len(differences) == 0
        return files_match, active_profile, differences
    
    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content."""
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                return f1.read() == f2.read()
        except Exception:
            return False
    
    def get_profile_files(self, profile_name: str) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Get the file paths for a profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Tuple of (json_file_path, ini_file_path) or (None, None) if not found
        """
        profile_dir = self.profiles_dir / profile_name
        if not profile_dir.exists():
            return None, None
        
        json_file = profile_dir / "settings.json"
        ini_file = profile_dir / "Config_DX11.ini"
        
        return (json_file if json_file.exists() else None,
                ini_file if ini_file.exists() else None)