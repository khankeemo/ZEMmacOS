# state_manager.py - Global state management
import os
import json
from datetime import datetime

class StateManager:
    """Global application state manager"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Application state
        self.current_page = "dashboard"
        self.selected_macos_index = None
        self.selected_macos_product = None
        self.selected_macos_title = None
        
        # Process state
        self.process_running = False
        self.current_process_pid = None
        self.process_start_time = None
        
        # Settings
        self.download_directory = os.path.join(os.path.expanduser("~"), "Downloads", "macOS")
        self.current_catalog = "publicrelease"
        self.show_all_disks = False
        self.caffeinate_downloads = True
        
        # UI State
        self.console_widget_ref = None
        self.version_list_data = []
        
        # Load saved settings
        self.load_settings()
        
        # Callback listeners
        self._listeners = {}
    
    def load_settings(self):
        """Load settings from config file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.download_directory = config.get("download_directory", self.download_directory)
                    self.current_catalog = config.get("catalog", self.current_catalog)
                    self.show_all_disks = config.get("show_all_disks", self.show_all_disks)
            except:
                pass
    
    def save_settings(self):
        """Save settings to config file"""
        config = {
            "download_directory": self.download_directory,
            "catalog": self.current_catalog,
            "show_all_disks": self.show_all_disks,
            "caffeinate_downloads": self.caffeinate_downloads
        }
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except:
            return False
    
    def set_selected_macos(self, index, product=None, title=None):
        """Set selected macOS version"""
        self.selected_macos_index = index
        self.selected_macos_product = product
        self.selected_macos_title = title
        self._notify_listeners("macos_selected", {
            "index": index,
            "product": product,
            "title": title
        })
    
    def set_process_state(self, running, pid=None):
        """Set process running state"""
        self.process_running = running
        self.current_process_pid = pid
        self.process_start_time = datetime.now() if running else None
        self._notify_listeners("process_state", {
            "running": running,
            "pid": pid
        })
    
    def set_console_widget(self, widget):
        """Set console widget reference (safe)"""
        self.console_widget_ref = widget
    
    def set_version_list(self, data):
        """Set version list data"""
        self.version_list_data = data
        self._notify_listeners("version_list", data)
    
    def add_listener(self, event, callback):
        """Add event listener"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def remove_listener(self, event, callback):
        """Remove event listener"""
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)
    
    def _notify_listeners(self, event, data=None):
        """Notify all listeners of an event"""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    callback(data)
                except:
                    pass
    
    def reset(self):
        """Reset state (keep settings)"""
        self.selected_macos_index = None
        self.selected_macos_product = None
        self.selected_macos_title = None
        self.process_running = False
        self.current_process_pid = None
        self.process_start_time = None


# Global state instance
_global_state = None

def get_state():
    """Get global state manager"""
    global _global_state
    if _global_state is None:
        _global_state = StateManager()
    return _global_state