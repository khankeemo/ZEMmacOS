# update.py
import os
import sys
import json
import webbrowser
import urllib.request
import urllib.error
from datetime import datetime
import socket

# Get base directory for dynamic paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppUpdater:
    """Update checker that fetches version from website and opens browser on update"""
    
    def __init__(self):
        self.current_version = self._get_current_version()
        self.version_url = "https://www.websmithdigital.com/version.txt"
        self.update_url = "https://www.websmithdigital.com"
    
    def _get_current_version(self) -> str:
        """
        Read current version from project_manifest.json.
        
        Supported keys in priority order:
        - version
        - product_version
        - branding.version
        
        Returns:
            version string or "3.0.0" as default
        """
        try:
            # Determine base path for frozen executable or development
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = BASE_DIR
            
            manifest_path = os.path.join(base_path, "project_manifest.json")
            
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    
                    # Priority order for version key
                    if "version" in manifest:
                        return str(manifest["version"])
                    elif "product_version" in manifest:
                        return str(manifest["product_version"])
                    elif "branding" in manifest and "version" in manifest["branding"]:
                        return str(manifest["branding"]["version"])
            
            return "3.0.0"
            
        except Exception:
            return "3.0.0"
    
    def _parse_version(self, version_str: str) -> tuple:
        """
        Parse version string into tuple of integers for proper comparison.
        
        Examples:
            "3.0" -> (3, 0)
            "3.10" -> (3, 10)
            "3.0.1" -> (3, 0, 1)
            "3.0.0-beta" -> (3, 0, 0)  # strips suffix
        
        Returns:
            tuple of integers for comparison
        """
        if not version_str:
            return (0,)
        
        # Remove any non-numeric prefix/suffix (e.g., "v3.0", "3.0-beta")
        import re
        match = re.search(r'(\d+(?:\.\d+)*)', version_str)
        if match:
            version_str = match.group(1)
        
        # Split into integer parts
        parts = version_str.split('.')
        return tuple(int(p) for p in parts if p.isdigit())
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings with proper numeric comparison.
        
        Args:
            v1: First version string
            v2: Second version string
        
        Returns:
            1 if v1 > v2
            -1 if v1 < v2
            0 if equal
        """
        v1_parts = self._parse_version(v1)
        v2_parts = self._parse_version(v2)
        
        # Compare part by part
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_val = v1_parts[i] if i < len(v1_parts) else 0
            v2_val = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_val > v2_val:
                return 1
            elif v1_val < v2_val:
                return -1
        
        return 0
    
    def _fetch_remote_version(self) -> str:
        """
        Fetch version string from remote server.
        
        Returns:
            version string from first non-empty line
        
        Raises:
            Exception with description on failure
        """
        try:
            req = urllib.request.Request(
                self.version_url,
                headers={'User-Agent': 'ZEMmacOS-Updater/3.0'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read().decode('utf-8').strip()
                # Get first non-empty line
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                if lines:
                    return lines[0]
                raise Exception("Empty response from server")
                
        except urllib.error.HTTPError as e:
            # HTTPError has code attribute
            if e.code == 404:
                raise Exception("Version check endpoint not available (404)")
            else:
                raise Exception(f"HTTP error: {e.code}")
        except urllib.error.URLError as e:
            # URLError has reason attribute, no code
            if hasattr(e, 'reason'):
                reason_str = str(e.reason).lower()
                if "timed out" in reason_str or "timeout" in reason_str:
                    raise Exception("Connection timeout - please check your internet")
                elif "getaddrinfo" in reason_str or "name resolution" in reason_str:
                    raise Exception("Cannot resolve server address - please check your internet")
                else:
                    raise Exception(f"Network error: {e.reason}")
            else:
                raise Exception(f"Connection failed: {str(e)}")
        except socket.timeout:
            raise Exception("Connection timeout - please check your internet")
        except Exception as e:
            raise Exception(f"Failed to fetch version: {str(e)}")
    
    def check_for_updates(self):
        """
        Check for updates by fetching remote version.
        
        Returns:
            dict with update info containing:
            - update_available: bool or None
            - latest_version: str or None
            - current_version: str
            - message: str
            - show_website_option: bool (optional)
            - error: str (optional)
        """
        try:
            remote_version = self._fetch_remote_version()
            
            # Validate remote version format
            if not remote_version or not any(c.isdigit() for c in remote_version):
                return {
                    "update_available": None,
                    "error": "Invalid version format from server",
                    "show_website_option": True,
                    "current_version": self.current_version
                }
            
            comparison = self._compare_versions(remote_version, self.current_version)
            
            if comparison > 0:
                # Remote is newer
                return {
                    "update_available": True,
                    "latest_version": remote_version,
                    "current_version": self.current_version,
                    "message": f"New version {remote_version} available!",
                    "show_website_option": True
                }
            elif comparison == 0:
                # Same version
                return {
                    "update_available": False,
                    "latest_version": remote_version,
                    "current_version": self.current_version,
                    "message": "You are running the latest version.",
                    "show_website_option": False
                }
            else:
                # Local is newer (development build)
                return {
                    "update_available": False,
                    "latest_version": remote_version,
                    "current_version": self.current_version,
                    "message": "You are using a newer development build.",
                    "show_website_option": False
                }
                
        except Exception as e:
            error_msg = str(e)
            
            # Network errors - show friendly message with website option
            if "Network error" in error_msg or "Connection" in error_msg or "timeout" in error_msg.lower():
                return {
                    "update_available": None,
                    "error": "Unable to check for updates right now.\n\nPlease check your internet connection.",
                    "show_website_option": True,
                    "current_version": self.current_version
                }
            elif "404" in error_msg:
                return {
                    "update_available": None,
                    "error": "Version check endpoint not available.\n\nPlease visit website to check for updates manually.",
                    "show_website_option": True,
                    "current_version": self.current_version
                }
            else:
                return {
                    "update_available": None,
                    "error": f"Update check failed: {error_msg}\n\nPlease visit website to check for updates manually.",
                    "show_website_option": True,
                    "current_version": self.current_version
                }
    
    def open_update_website(self):
        """Open the update website in default browser"""
        try:
            webbrowser.open(self.update_url)
            return True
        except Exception:
            return False
    
    def get_current_version(self):
        """Return current application version"""
        return self.current_version


if __name__ == "__main__":
    print("\n" + "="*50)
    print("   Update Module Test")
    print("="*50)
    
    print("\n--- Version Parsing Test ---")
    updater = AppUpdater()
    print(f"Parse '3.10' -> {updater._parse_version('3.10')}")
    print(f"Parse '3.2' -> {updater._parse_version('3.2')}")
    print(f"Compare 3.10 > 3.2: {updater._compare_versions('3.10', '3.2') > 0}")
    print(f"Compare 3.0.1 > 3.0.0: {updater._compare_versions('3.0.1', '3.0.0') > 0}")
    
    print(f"\nCurrent Version: {updater.get_current_version()}")
    
    print("\n--- Update Check Test ---")
    result = updater.check_for_updates()
    print(f"Result: {result}")
    
    print("\nUpdate module ready")