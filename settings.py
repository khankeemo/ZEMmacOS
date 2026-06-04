# settings.py
import os
import json
import tkinter as tk
from tkinter import messagebox

from themes import apply_theme

# Get base directory for dynamic paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "theme": "light",
    "download_directory": "",
    "catalog": "publicrelease",
    "download_threads": 8,
    "window_width": 1200,
    "window_height": 800,
    "license_api_url": "https://api.websmithdigital.com",
    "license_api_timeout": 15,
    "offline_grace_hours": 72,
}


class SettingsManager:
    """Manages application settings via config.json"""
    
    def __init__(self):
        self.config_path = os.path.join(BASE_DIR, "config.json")
        self.settings = self.load()
        
    def _get_default_download_dir(self):
        return os.path.join(os.path.expanduser("~"), "Downloads", "macOS")

    def load(self):
        """Load settings from file or return defaults"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in loaded:
                            loaded[key] = value
                    return loaded
            except (json.JSONDecodeError, OSError):
                pass
        return DEFAULT_CONFIG.copy()

    def save(self, data=None):
        """Save settings to file"""
        if data:
            self.settings.update(data)
        
        if not self.settings.get("download_directory"):
            self.settings["download_directory"] = self._get_default_download_dir()
            
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            return True
        except OSError:
            return False

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def reset_defaults(self):
        self.settings = DEFAULT_CONFIG.copy()
        self.save()


class AppSettingsService:
    """Professional settings service layer - handles all settings business logic"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.settings_manager = app_instance.settings
    
    def load_ui_values(self):
        """Load settings into UI controls"""
        try:
            if hasattr(self.app, 'settings_download_dir'):
                self.app.settings_download_dir.delete(0, tk.END)
                self.app.settings_download_dir.insert(0, self.settings_manager.get("download_directory", ""))
            if hasattr(self.app, 'settings_catalog_var'):
                self.app.settings_catalog_var.set(self.settings_manager.get("catalog", "publicrelease"))
            if hasattr(self.app, 'threads_var'):
                self.app.threads_var.set(str(self.settings_manager.get("download_threads", 8)))
        except Exception as e:
            self.app.log(f"Error loading settings to UI: {e}", "error")
    
    def save_ui_values(self):
        """Save UI values to settings"""
        dl_dir = self.app.settings_download_dir.get().strip() if hasattr(self.app, 'settings_download_dir') else ""
        catalog = self.app.settings_catalog_var.get() if hasattr(self.app, 'settings_catalog_var') else "publicrelease"
        threads = int(self.app.threads_var.get()) if hasattr(self.app, 'threads_var') else 8
        
        self.settings_manager.set("download_directory", dl_dir)
        self.settings_manager.set("catalog", catalog)
        self.settings_manager.set("download_threads", threads)
        
        self.app.log("Settings saved", "info")
        return True
    
    def validate_settings(self):
        """Validate current settings values"""
        dl_dir = self.settings_manager.get("download_directory", "")
        if not dl_dir or not os.path.exists(dl_dir):
            return False, "Download directory does not exist"
        
        threads = self.settings_manager.get("download_threads", 8)
        if threads not in [4, 8, 16, 32]:
            return False, "Invalid thread count"
        
        catalog = self.settings_manager.get("catalog", "publicrelease")
        if catalog not in ["publicrelease", "public", "customer", "developer"]:
            return False, "Invalid catalog type"
        
        return True, "Valid"
    
    def check_first_run_directory(self):
        """Check if download directory is set, prompt if not"""
        dl_dir = self.settings_manager.get("download_directory")
        if not dl_dir or dl_dir == "":
            messagebox.showwarning(
                "Setup Required",
                "Please select a default download location for macOS installers.",
            )
            self.app.show_settings()
            return False
        return True
    
    def get_download_directory(self):
        """Get validated download directory"""
        dl_dir = self.settings_manager.get("download_directory")
        if not dl_dir:
            dl_dir = self.settings_manager._get_default_download_dir()
        return dl_dir
    
    def apply_saved_theme(self):
        """Load and apply saved theme from settings"""
        saved_theme = self.settings_manager.get("theme", "light")
        if saved_theme == "dark":
            self.app.theme_mode = "dark"
            apply_theme(self.app, "dark")
        else:
            self.app.theme_mode = "light"
            apply_theme(self.app, "light")
        
        # Update theme toggle button text
        if hasattr(self.app, 'theme_toggle_btn'):
            self.app.theme_toggle_btn.config(text="☀️ Switch to Light" if self.app.theme_mode == "dark" else "🌙 Switch to Dark")
        
        return self.app.theme_mode
    
    def toggle_and_save_theme(self):
        """Toggle theme and save to settings"""
        if self.app.theme_mode == "light":
            self.app.theme_mode = "dark"
            apply_theme(self.app, "dark")
            new_text = "☀️ Switch to Light"
        else:
            self.app.theme_mode = "light"
            apply_theme(self.app, "light")
            new_text = "🌙 Switch to Dark"
        
        if hasattr(self.app, 'theme_toggle_btn'):
            self.app.theme_toggle_btn.config(text=new_text)
        
        # Save theme preference
        self.settings_manager.set("theme", self.app.theme_mode)
        
        # Refresh current view
        if hasattr(self.app, 'current_view'):
            if self.app.current_view == "dashboard":
                self.app.show_dashboard()
            elif self.app.current_view == "library":
                self.app.show_library()
            elif self.app.current_view == "settings":
                self.app.show_settings()
        
        return self.app.theme_mode
    
    def sanitize_thread_count(self, value):
        """Sanitize thread count to valid values"""
        try:
            val = int(value)
            if val < 4:
                return 4
            if val > 32:
                return 32
            return val
        except (ValueError, TypeError):
            return 8
    
    def sanitize_catalog(self, value):
        """Sanitize catalog selection"""
        valid = ["publicrelease", "public", "customer", "developer"]
        if value in valid:
            return value
        return "publicrelease"
    
    def get_catalog_url(self):
        """Get catalog URL based on selection"""
        catalog = self.settings_manager.get("catalog", "publicrelease")
        catalog_urls = {
            "publicrelease": "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
            "public": "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
            "customer": "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
            "developer": "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
        }
        return catalog_urls.get(catalog, catalog_urls["publicrelease"])


if __name__ == "__main__":
    print("\n" + "="*50)
    print("   Settings Module Test")
    print("="*50)
    
    # Test SettingsManager
    manager = SettingsManager()
    print(f"\nConfig Path: {manager.config_path}")
    print(f"Current Settings: {manager.settings}")
    
    # Test get/set
    manager.set("test_key", "test_value")
    print(f"Test Key: {manager.get('test_key')}")
    
    # Clean up test
    if "test_key" in manager.settings:
        del manager.settings["test_key"]
        manager.save()
    
    print("\nSettings module ready")