# cleaner.py - Deletes __pycache__, temp files, and logs
import os
import shutil
import sys
import tempfile
from pathlib import Path
import glob

class Cleaner:
    def __init__(self, console_manager=None):
        """
        Initialize cleaner
        
        Args:
            console_manager: Optional ConsoleManager for logging
        """
        self.console = console_manager
        
    def log(self, message, message_type="info"):
        """Log message to console if available"""
        if self.console:
            self.console.log(message, message_type)
        else:
            print(f"[{message_type.upper()}] {message}")
            
    def clear_pycache(self, start_path="."):
        """
        Delete all __pycache__ folders
        
        Args:
            start_path: Root directory to start searching from
            
        Returns:
            Number of folders deleted
        """
        count = 0
        deleted = []
        
        for root, dirs, files in os.walk(start_path):
            if "__pycache__" in dirs:
                pycache_path = os.path.join(root, "__pycache__")
                try:
                    shutil.rmtree(pycache_path)
                    count += 1
                    deleted.append(pycache_path)
                    self.log(f"Removed: {pycache_path}")
                except Exception as e:
                    self.log(f"Failed to remove {pycache_path}: {str(e)}", "error")
                    
        self.log(f"Removed {count} __pycache__ folder(s)")
        return count
        
    def clear_pyc_files(self, start_path="."):
        """
        Delete all .pyc and .pyo files
        
        Args:
            start_path: Root directory to start searching from
            
        Returns:
            Number of files deleted
        """
        count = 0
        extensions = [".pyc", ".pyo"]
        
        for root, dirs, files in os.walk(start_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        count += 1
                        self.log(f"Removed: {file_path}")
                    except Exception as e:
                        self.log(f"Failed to remove {file_path}: {str(e)}", "error")
                        
        self.log(f"Removed {count} .pyc/.pyo file(s)")
        return count
        
    def clear_temp_files(self, patterns=None):
        """
        Clear temporary files matching patterns
        
        Args:
            patterns: List of patterns to match (default: ['*.tmp', '*.temp', '*.log'])
            
        Returns:
            Number of files deleted
        """
        if patterns is None:
            patterns = ['*.tmp', '*.temp', '*.log']
            
        count = 0
        
        for pattern in patterns:
            for file in Path(".").glob(pattern):
                try:
                    file.unlink()
                    count += 1
                    self.log(f"Removed: {file}")
                except Exception as e:
                    self.log(f"Failed to remove {file}: {str(e)}", "error")
                    
        self.log(f"Removed {count} temp file(s)")
        return count
        
    def clear_logs(self, delete_all=False, keep_count=5):
        """
        Clear log files
        
        Args:
            delete_all: If True, delete ALL log files (ignore keep_count)
            keep_count: Number of recent log files to keep (only if delete_all=False)
            
        Returns:
            Number of files deleted
        """
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        if not os.path.exists(logs_dir):
            self.log("No logs directory found", "warning")
            return 0
            
        count = 0
        try:
            # Get all log files
            log_files = []
            for f in os.listdir(logs_dir):
                if f.endswith(".log"):
                    file_path = os.path.join(logs_dir, f)
                    log_files.append((file_path, os.path.getmtime(file_path)))
            
            if delete_all:
                # Delete ALL log files
                for file_path, _ in log_files:
                    try:
                        os.remove(file_path)
                        count += 1
                        self.log(f"Deleted log: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.log(f"Failed to delete {file_path}: {str(e)}", "error")
                self.log(f"Deleted ALL {count} log file(s)")
            else:
                # Sort by modification time (newest first)
                log_files.sort(key=lambda x: x[1], reverse=True)
                
                # Delete old ones
                for file_path, _ in log_files[keep_count:]:
                    try:
                        os.remove(file_path)
                        count += 1
                        self.log(f"Removed old log: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.log(f"Failed to remove {file_path}: {str(e)}", "error")
                        
                self.log(f"Cleaned {count} old log files, kept {min(keep_count, len(log_files))} recent")
            
        except Exception as e:
            self.log(f"Failed to clear logs: {str(e)}", "error")
            
        return count
        
    def clear_system_temp(self):
        """
        Clear system temp directory (user-specific)
        
        Returns:
            Number of files/folders deleted
        """
        temp_dir = tempfile.gettempdir()
        count = 0
        
        self.log(f"Cleaning system temp directory: {temp_dir}")
        
        for item in Path(temp_dir).iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
            except Exception:
                pass  # Skip files in use
                
        self.log(f"Cleaned {count} items from system temp")
        return count
        
    def clear_all(self, include_system_temp=False, keep_logs=5):
        """
        Clear all temporary files and folders
        
        Args:
            include_system_temp: Whether to clear system temp directory
            keep_logs: Number of recent log files to keep
            
        Returns:
            Dictionary with counts of deleted items
        """
        results = {
            "pycache_folders": self.clear_pycache(),
            "pyc_files": self.clear_pyc_files(),
            "temp_files": self.clear_temp_files(),
            "logs": self.clear_logs(delete_all=False, keep_count=keep_logs)
        }
        
        if include_system_temp:
            results["system_temp"] = self.clear_system_temp()
            
        total = sum(results.values())
        self.log(f"Total cleaned: {total} item(s)")
        
        return results
        
    def clear_gibmacos_temp(self):
        """
        Clear gibMacOS specific temporary files
        """
        # Clear macOS Downloads temp files
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        downloads_dir = os.path.join(PROJECT_ROOT, "macOS Downloads")
        if os.path.exists(downloads_dir):
            # Remove incomplete downloads (files with .part extension)
            for file in Path(downloads_dir).glob("*.part"):
                try:
                    file.unlink()
                    self.log(f"Removed incomplete download: {file}")
                except Exception as e:
                    self.log(f"Failed to remove {file}: {str(e)}", "error")
                    
        # Clear any .plist cache files
        for file in Path(".").glob("*.plist"):
            if "cache" in file.name.lower():
                try:
                    file.unlink()
                    self.log(f"Removed cache file: {file}")
                except Exception as e:
                    self.log(f"Failed to remove {file}: {str(e)}", "error")

def main():
    """Standalone cleaner with console output"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean temporary files")
    parser.add_argument("--all", action="store_true", help="Clear all temp files")
    parser.add_argument("--pycache", action="store_true", help="Clear __pycache__ folders")
    parser.add_argument("--pyc", action="store_true", help="Clear .pyc/.pyo files")
    parser.add_argument("--temp", action="store_true", help="Clear temp files")
    parser.add_argument("--logs", action="store_true", help="Clear old log files")
    parser.add_argument("--delete-all-logs", action="store_true", help="Delete ALL log files")
    parser.add_argument("--system", action="store_true", help="Clear system temp")
    parser.add_argument("--keep-logs", type=int, default=5, help="Number of log files to keep")
    
    args = parser.parse_args()
    
    cleaner = Cleaner()
    
    if args.all:
        cleaner.clear_all(include_system_temp=args.system, keep_logs=args.keep_logs)
    else:
        if args.pycache:
            cleaner.clear_pycache()
        if args.pyc:
            cleaner.clear_pyc_files()
        if args.temp:
            cleaner.clear_temp_files()
        if args.logs:
            if args.delete_all_logs:
                cleaner.clear_logs(delete_all=True)
            else:
                cleaner.clear_logs(keep_count=args.keep_logs)
        if args.system:
            cleaner.clear_system_temp()
            
        if not any([args.pycache, args.pyc, args.temp, args.logs, args.system]):
            # Default behavior: clear __pycache__, .pyc, and logs (keep last 5)
            cleaner.clear_pycache()
            cleaner.clear_pyc_files()
            cleaner.clear_logs(keep_count=5)
            
if __name__ == "__main__":
    main()