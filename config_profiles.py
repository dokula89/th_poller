"""
Profile Management System for Queue Poller
Supports multiple machine profiles with different screen sizes and settings.

Profiles:
- OSx: MacOS machines
- Old Win: This Windows laptop (WINDOWSA)
- New Win: Newer Windows machines
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import socket

# Profile definitions
PROFILES = {
    "OSx": {
        "description": "MacOS machines",
        "default_settings": {
            "pending_window_width_pct": 0.20,
            "pending_window_height_pct": 1.0,
            "parcel_window_width_pct": 0.20,
            "parcel_window_height_pct": 1.0,
            "queue_poller_width": 420,
            "queue_poller_height": 700,
        }
    },
    "Old Win": {
        "description": "Old Windows laptop (WINDOWSA)",
        "default_settings": {
            "pending_window_width_pct": 0.20,
            "pending_window_height_pct": 1.0,
            "parcel_window_width_pct": 0.20,
            "parcel_window_height_pct": 1.0,
            "queue_poller_width": 420,
            "queue_poller_height": 700,
        }
    },
    "New Win": {
        "description": "Newer Windows machines",
        "default_settings": {
            "pending_window_width_pct": 0.20,
            "pending_window_height_pct": 1.0,
            "parcel_window_width_pct": 0.20,
            "parcel_window_height_pct": 1.0,
            "queue_poller_width": 420,
            "queue_poller_height": 700,
        }
    }
}

# Machine name to profile mapping
MACHINE_PROFILE_MAP = {
    "WINDOWSA": "Old Win",
    # Add other machine names as they're discovered
}


class ProfileManager:
    """Manages machine-specific profiles and settings"""
    
    def __init__(self):
        self._profiles_dir = Path(__file__).parent / "profiles"
        self._profiles_dir.mkdir(exist_ok=True)
        
        # Detect current machine
        self._machine_name = socket.gethostname().upper()
        
        # Determine active profile
        self._active_profile = self._detect_profile()
        
        # Load settings
        self._settings: Dict[str, Any] = {}
        self._load_settings()
    
    def _detect_profile(self) -> str:
        """Detect which profile to use based on machine name or saved preference"""
        # Check for saved profile preference
        pref_file = self._profiles_dir / ".active_profile"
        if pref_file.exists():
            try:
                saved_profile = pref_file.read_text().strip()
                if saved_profile in PROFILES:
                    return saved_profile
            except Exception:
                pass
        
        # Check machine name mapping
        if self._machine_name in MACHINE_PROFILE_MAP:
            return MACHINE_PROFILE_MAP[self._machine_name]
        
        # Default based on OS
        import platform
        if platform.system() == "Darwin":
            return "OSx"
        else:
            return "Old Win"  # Default for Windows
    
    def _get_profile_path(self, profile_name: str = None) -> Path:
        """Get the settings file path for a profile"""
        profile = profile_name or self._active_profile
        safe_name = profile.replace(" ", "_").lower()
        return self._profiles_dir / f"{safe_name}_settings.json"
    
    def _load_settings(self):
        """Load settings from profile file"""
        profile_path = self._get_profile_path()
        
        # Start with default settings for this profile
        self._settings = PROFILES.get(self._active_profile, {}).get("default_settings", {}).copy()
        
        # Overlay saved settings
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    saved = json.load(f)
                    self._settings.update(saved)
            except Exception as e:
                print(f"[Profile] Error loading settings: {e}")
    
    def _save_settings(self):
        """Save current settings to profile file"""
        profile_path = self._get_profile_path()
        try:
            with open(profile_path, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"[Profile] Error saving settings: {e}")
    
    @property
    def active_profile(self) -> str:
        """Get the active profile name"""
        return self._active_profile
    
    @property
    def machine_name(self) -> str:
        """Get the current machine name"""
        return self._machine_name
    
    @property
    def available_profiles(self) -> list:
        """Get list of available profile names"""
        return list(PROFILES.keys())
    
    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different profile"""
        if profile_name not in PROFILES:
            return False
        
        self._active_profile = profile_name
        
        # Save preference
        pref_file = self._profiles_dir / ".active_profile"
        try:
            pref_file.write_text(profile_name)
        except Exception:
            pass
        
        # Reload settings for new profile
        self._load_settings()
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any, auto_save: bool = True):
        """Set a setting value and optionally auto-save"""
        self._settings[key] = value
        if auto_save:
            self._save_settings()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._settings.copy()
    
    def update(self, settings: Dict[str, Any], auto_save: bool = True):
        """Update multiple settings at once"""
        self._settings.update(settings)
        if auto_save:
            self._save_settings()
    
    # Convenience methods for common settings
    def get_pending_window_size(self, screen_width: int, screen_height: int) -> tuple:
        """Get pending window dimensions based on profile settings"""
        width_pct = self.get("pending_window_width_pct", 0.20)
        height_pct = self.get("pending_window_height_pct", 1.0)
        return (int(screen_width * width_pct), int(screen_height * height_pct))
    
    def get_parcel_window_size(self, screen_width: int, screen_height: int) -> tuple:
        """Get parcel activity window dimensions based on profile settings"""
        width_pct = self.get("parcel_window_width_pct", 0.20)
        height_pct = self.get("parcel_window_height_pct", 1.0)
        return (int(screen_width * width_pct), int(screen_height * height_pct))
    
    def save_window_geometry(self, window_name: str, x: int, y: int, width: int, height: int):
        """Save window position and size"""
        self.set(f"{window_name}_x", x)
        self.set(f"{window_name}_y", y)
        self.set(f"{window_name}_width", width)
        self.set(f"{window_name}_height", height, auto_save=True)  # Only save on last set
    
    def get_window_geometry(self, window_name: str) -> Optional[tuple]:
        """Get saved window position and size, or None if not saved"""
        x = self.get(f"{window_name}_x")
        y = self.get(f"{window_name}_y")
        width = self.get(f"{window_name}_width")
        height = self.get(f"{window_name}_height")
        
        if all(v is not None for v in [x, y, width, height]):
            return (x, y, width, height)
        return None


# Global instance
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get the global profile manager instance"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def log_profile_info():
    """Log current profile information"""
    pm = get_profile_manager()
    print(f"[Profile] Machine: {pm.machine_name}")
    print(f"[Profile] Active Profile: {pm.active_profile}")
    print(f"[Profile] Available Profiles: {', '.join(pm.available_profiles)}")
