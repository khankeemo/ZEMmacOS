import os
import sys
import json
import shutil
from datetime import datetime

class USBCreator:
    REQUIRED_FILES = ["BaseSystem.dmg", "InstallInfo.plist"]
    OPTIONAL_FILES = ["BaseSystem.chunklist", "AppleDiagnostics.dmg", "AppleDiagnostics.chunklist", "InstallESDDmg.pkg"]
    VALIDATION_PATHS = ["", "Contents/SharedSupport", "SharedSupport", "com.apple.installer"]

    def __init__(self, callback=None, progress_callback=None):
        self.callback = callback
        self.progress_callback = progress_callback
        self.selected_path = None
        self.validation_result = None
        self.detected_type = None
        self.validation_root = None
        self.scan_results = []

    def _log(self, message, level="info"):
        if self.callback:
            try: self.callback(message, level)
            except: pass
        else: print(f"[{level.upper()}] {message}")

    def _update_progress(self, current, total, message=""):
        if self.progress_callback:
            try: self.progress_callback(current, total, message)
            except: pass

    def _scan_folder_structure(self, path):
        self._log(f"🔍 Scanning folder structure: {path}", "info")
        self._update_progress(10, 100, "Scanning folder structure...")
        scan_results = {"found_files": [], "validation_candidates": [], "total_size": 0, "file_count": 0}
        try:
            for root, dirs, files in os.walk(path):
                scan_results["file_count"] += len(files)
                if scan_results["file_count"] % 100 == 0:
                    self._update_progress(10 + min(30, scan_results["file_count"] // 10), 100, f"Scanning... found {scan_results['file_count']} files")
                for req_file in self.REQUIRED_FILES:
                    if req_file in files and req_file not in scan_results["found_files"]:
                        scan_results["found_files"].append(req_file)
                        self._log(f"  Found: {os.path.join(root, req_file)}", "success")
                        scan_results["validation_candidates"].append(root)
                for opt_file in self.OPTIONAL_FILES:
                    if opt_file in files and opt_file not in scan_results["found_files"]:
                        scan_results["found_files"].append(opt_file)
                        self._log(f"  Found optional: {opt_file}", "info")
                for file in files:
                    try: scan_results["total_size"] += os.path.getsize(os.path.join(root, file))
                    except: pass
        except Exception as e: self._log(f"Scan error: {e}", "error")
        self._update_progress(40, 100, f"Scan complete. Found {len(scan_results['found_files'])} files")
        return scan_results

    def detect_input_type(self, path, scan_results=None):
        if not path or not os.path.exists(path): return None
        self._log("=" * 50, "info"); self._log("AUTO-DETECTING MACOS INSTALLER TYPE", "info"); self._log("=" * 50, "info")
        if path.endswith('.app') and os.path.isdir(path):
            self._log("✓ Detected: macOS Installer (.app bundle)", "success")
            self._update_progress(50, 100, "Detected: macOS Installer (.app)")
            shared_support = os.path.join(path, "Contents", "SharedSupport")
            if os.path.exists(shared_support):
                self._log(f"  ✓ Found SharedSupport at: {shared_support}", "success")
                self.validation_root = shared_support
            else: self._log("  ⚠️ Warning: SharedSupport not found", "warning")
            return 'app'
        if path.endswith('.pkg') or (os.path.isdir(path) and any(f.endswith('.pkg') for f in os.listdir(path))):
            self._log("✓ Detected: InstallAssistant.pkg", "success")
            self._update_progress(50, 100, "Detected: InstallAssistant.pkg")
            return 'pkg'
        if os.path.isdir(path):
            found_files = scan_results.get("found_files", []) if scan_results else []
            if not found_files:
                for root, dirs, files in os.walk(path):
                    if "BaseSystem.dmg" in files: found_files.append("BaseSystem.dmg"); self.validation_root = root; break
            if "BaseSystem.dmg" in found_files:
                self._log("✓ Detected: RAW macOS Folder (gibMacOS format)", "success")
                self._update_progress(50, 100, "Detected: RAW macOS Folder")
                return 'raw'
        self._log("⚠️ Unknown format - will attempt RAW validation", "warning")
        return 'raw'

    def find_validation_root(self, path):
        self._log(f"🔍 Looking for validation files in: {path}", "info")
        for subpath in self.VALIDATION_PATHS:
            check_path = os.path.join(path, subpath) if subpath else path
            if os.path.exists(check_path):
                files_present = [req for req in self.REQUIRED_FILES if os.path.exists(os.path.join(check_path, req))]
                if files_present:
                    self._log(f"✓ Found validation root: {check_path}", "success")
                    self._log(f"  Files present: {', '.join(files_present)}", "info")
                    return check_path
        self._log("  Performing deep search...", "info")
        for root, dirs, files in os.walk(path):
            if "BaseSystem.dmg" in files: self._log(f"✓ Found BaseSystem.dmg at: {root}", "success"); return root
            if "InstallInfo.plist" in files: self._log(f"✓ Found InstallInfo.plist at: {root}", "success"); return root
        self._log("❌ Could not find validation root", "error")
        return None

    def select_path(self, path):
        if not path or not os.path.exists(path): self._log(f"❌ Path does not exist: {path}", "error"); return False
        self.selected_path = path
        self._log("  ", "output"); self._log("=" * 60, "info"); self._log(f"📂 SELECTED: {path}", "info"); self._log("=" * 60, "info")
        if os.path.isdir(path):
            scan_results = self._scan_folder_structure(path)
            self.detected_type = self.detect_input_type(path, scan_results)
        else: self.detected_type = self.detect_input_type(path)
        if self.detected_type == 'app':
            self.validation_root = os.path.join(path, "Contents", "SharedSupport")
            if not os.path.exists(self.validation_root): self.validation_root = self.find_validation_root(path)
        elif self.detected_type == 'raw': self.validation_root = self.find_validation_root(path)
        else: self.validation_root = path
        self._log("  ", "output"); self._update_progress(60, 100, f"Validation root: {self.validation_root}")
        return True

    def validate_folder(self, path=None):
        if path: self.select_path(path)
        self._log("  ", "output"); self._log("=" * 50, "info"); self._log("VALIDATING MACOS INSTALLER", "info"); self._log("=" * 50, "info")
        self._update_progress(70, 100, "Validating files...")
        if not self.selected_path or not os.path.exists(self.selected_path):
            return {"valid": False, "error": "No path selected", "found": [], "missing": self.REQUIRED_FILES.copy(), "optional_found": [], "input_type": None, "validation_root": None}
        if self.detected_type == 'pkg':
            total_size = self._get_folder_size(self.selected_path)
            result = {"valid": True, "error": None, "found": ["InstallAssistant.pkg"], "missing": [], "optional_found": [], "folder_size": total_size, "folder_size_mb": round(total_size / (1024 * 1024), 1), "folder_size_gb": round(total_size / (1024 * 1024 * 1024), 2), "input_type": "pkg", "validation_root": self.selected_path, "is_pkg": True}
            self.validation_result = result
            self._log(f"✅ PKG detected - ready for installation on macOS", "success")
            self._log(f"📁 Size: {result['folder_size_gb']} GB", "info")
            self._update_progress(100, 100, "Validation complete - PKG ready")
            return result
        if self.detected_type == 'app' and (not self.validation_root or not os.path.exists(self.validation_root)):
            return {"valid": False, "error": "Invalid macOS .app structure (SharedSupport missing)", "found": [], "missing": self.REQUIRED_FILES.copy(), "optional_found": [], "input_type": "app", "validation_root": None}
        if not self.validation_root or not os.path.exists(self.validation_root):
            return {"valid": False, "error": "Validation root not found. Could not locate required files.", "found": [], "missing": self.REQUIRED_FILES.copy(), "optional_found": [], "input_type": self.detected_type, "validation_root": self.validation_root}
        try:
            files = os.listdir(self.validation_root)
            found_files, missing_files, optional_found = [], [], []
            self._log(f"📁 Checking: {self.validation_root}", "info")
            for req_file in self.REQUIRED_FILES:
                if req_file in files: found_files.append(req_file); self._log(f"  ✓ Found: {req_file}", "success")
                else: missing_files.append(req_file); self._log(f"  ✗ Missing: {req_file}", "error")
            for opt_file in self.OPTIONAL_FILES:
                if opt_file in files: optional_found.append(opt_file); self._log(f"  ○ Optional: {opt_file}", "info")
            total_size = self._get_folder_size(self.selected_path)
            result = {"valid": len(missing_files) == 0, "error": None if len(missing_files) == 0 else f"Missing: {', '.join(missing_files)}", "found": found_files, "missing": missing_files, "optional_found": optional_found, "folder_size": total_size, "folder_size_mb": round(total_size / (1024 * 1024), 1), "folder_size_gb": round(total_size / (1024 * 1024 * 1024), 2), "input_type": self.detected_type, "validation_root": self.validation_root, "is_pkg": False}
            self.validation_result = result
            self._log("  ", "output")
            if result["valid"]: self._log(f"✅ VALIDATION PASSED", "success"); self._log(f"   Required files: {len(found_files)}/{len(self.REQUIRED_FILES)}", "success"); self._log(f"   Total size: {result['folder_size_gb']} GB", "info")
            else: self._log(f"❌ VALIDATION FAILED", "error"); self._log(f"   {result['error']}", "error")
            self._update_progress(100, 100, "Validation complete")
            return result
        except Exception as e:
            self._log(f"❌ Validation error: {e}", "error")
            return {"valid": False, "error": str(e), "found": [], "missing": self.REQUIRED_FILES.copy(), "optional_found": [], "input_type": self.detected_type, "validation_root": self.validation_root}

    def _get_folder_size(self, folder_path):
        total, file_count = 0, 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, filename))
                        file_count += 1
                        if file_count % 500 == 0: self._update_progress(75 + min(20, file_count // 100), 100, f"Calculating size... {file_count} files")
                    except: pass
        except: pass
        return total

    def get_platform(self):
        if sys.platform == "darwin": return "macos"
        elif sys.platform == "win32": return "windows"
        return "linux"

    def get_next_steps(self, platform=None):
        if platform is None: platform = self.get_platform()
        if self.detected_type == 'pkg':
            return {"title": "📦 InstallAssistant.pkg Detected", "steps": ["1. Copy this .pkg file to a Mac or macOS Virtual Machine", "2. Double-click the .pkg file to open it", "3. The Installer will copy the macOS Installer to /Applications", "4. After installation, use createinstallmedia to make bootable USB"], "commands": [{"description": "Open InstallAssistant.pkg on macOS", "command": "open InstallAssistant.pkg"}, {"description": "After installation, create bootable USB", "command": 'sudo /Applications/Install\\ macOS.app/Contents/Resources/createinstallmedia --volume /Volumes/MyUSB'}]}
        if self.detected_type == 'app':
            return {"title": "🍎 macOS Installer.app Ready", "steps": ["1. Copy this .app to a Mac (if not already on one)", "2. Open Terminal on macOS", "3. Create bootable USB using createinstallmedia"], "commands": [{"description": "Find USB drive identifier", "command": "diskutil list"}, {"description": "Erase USB drive (replace disk2 with your USB)", "command": "sudo diskutil eraseDisk JHFS+ 'INSTALLER' /dev/disk2"}, {"description": "Create bootable installer", "command": 'sudo /Applications/Install\\ macOS.app/Contents/Resources/createinstallmedia --volume /Volumes/INSTALLER'}]}
        return {"title": "📋 macOS Installer Validated", "steps": ["1. Files have been validated and are ready", "2. Copy this folder to a Mac or macOS Virtual Machine", "3. On macOS, use createinstallmedia to create bootable USB"], "commands": [{"description": "Copy this folder to your Mac", "command": self.selected_path if self.selected_path else "Select a folder first"}, {"description": "On macOS, create bootable USB", "command": 'sudo /Applications/Install\\ macOS.app/Contents/Resources/createinstallmedia --volume /Volumes/MyUSB'}]}

    def get_command_to_copy(self):
        return 'sudo /Applications/Install\\ macOS.app/Contents/Resources/createinstallmedia --volume /Volumes/MyUSB'

    def save_selected_path(self, path, config_file="usb_config.json"):
        try:
            config = {}
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f: config = json.load(f)
            config['last_usb_path'] = path; config['last_updated'] = datetime.now().isoformat()
            with open(config_path, 'w') as f: json.dump(config, f, indent=2)
            return True
        except Exception as e: self._log(f"Failed to save config: {e}", "warning"); return False

    def load_last_path(self, config_file="usb_config.json"):
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f: config = json.load(f)
                return config.get('last_usb_path', '')
        except: pass
        return ''

    def get_scan_summary(self):
        if not self.validation_result: return "No validation performed yet"
        result = self.validation_result
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    SCAN SUMMARY                              ║
╠══════════════════════════════════════════════════════════════╣
║  Type: {result.get('input_type', 'Unknown'):<46} ║
║  Valid: {str(result.get('valid', False)):<47} ║
║  Size: {result.get('folder_size_gb', 0):.2f} GB{' ' * 42} ║
║  Required Files: {len(result.get('found', []))}/{len(self.REQUIRED_FILES):<32} ║
╚══════════════════════════════════════════════════════════════╝
"""