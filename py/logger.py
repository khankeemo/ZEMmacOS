# logger.py - Auto Log System with rotation and dual output
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import queue

class Logger:
    """Auto log system with file rotation and UI integration"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure single logger instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Logger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.log_queue = queue.Queue()
        self.console_callback = None
        self.log_dir = self._create_log_dir()
        self.logger = self._setup_logger()
        
        # Start queue processor
        self.running = True
        self._start_queue_processor()
        
    def _create_log_dir(self):
        """Create logs directory if it doesn't exist"""
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(PROJECT_ROOT, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir
    
    def _setup_logger(self):
        """Setup rotating file logger"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(self.log_dir, f"ZEMmacOS_{timestamp}.log")
        
        logger = logging.getLogger("ZEMmacOS")
        logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler with rotation (max 10MB, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Format for file
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        # Store current log file path
        self.current_log_file = log_file
        
        # Clean old logs (keep only last 10)
        self._clean_old_logs()
        
        return logger
    
    def _clean_old_logs(self, keep_count=10):
        """Delete old log files, keep only the most recent ones"""
        try:
            log_files = []
            for f in os.listdir(self.log_dir):
                if f.startswith("ZEMmacOS_") and f.endswith(".log"):
                    file_path = os.path.join(self.log_dir, f)
                    log_files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x[1], reverse=True)
            
            # Delete old ones
            for file_path, _ in log_files[keep_count:]:
                try:
                    os.remove(file_path)
                except:
                    pass
        except:
            pass
    
    def _start_queue_processor(self):
        """Start background thread to process log queue"""
        def process_queue():
            while self.running:
                try:
                    level, message = self.log_queue.get(timeout=0.1)
                    self._write_to_logger(level, message)
                except queue.Empty:
                    continue
                    
        thread = threading.Thread(target=process_queue, daemon=True)
        thread.start()
    
    def _write_to_logger(self, level, message):
        """Write to file logger"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "critical":
            self.logger.critical(message)
        elif level == "success":
            self.logger.info(f"✓ {message}")
            
        # Send to UI console if callback registered
        if self.console_callback:
            try:
                self.console_callback(message, level)
            except:
                pass
    
    def set_console_callback(self, callback):
        """Set callback function for UI console output"""
        self.console_callback = callback
    
    def debug(self, message):
        """Log debug message"""
        self.log_queue.put(("debug", message))
    
    def info(self, message):
        """Log info message"""
        self.log_queue.put(("info", message))
    
    def warning(self, message):
        """Log warning message"""
        self.log_queue.put(("warning", message))
    
    def error(self, message):
        """Log error message"""
        self.log_queue.put(("error", message))
    
    def critical(self, message):
        """Log critical message"""
        self.log_queue.put(("critical", message))
    
    def success(self, message):
        """Log success message"""
        self.log_queue.put(("success", message))
    
    def log_output(self, line, stream="stdout"):
        """Log process output line"""
        self.log_queue.put(("info", f"[{stream.upper()}] {line}"))
    
    def get_log_file_path(self):
        """Get current log file path"""
        return self.current_log_file
    
    def stop(self):
        """Stop logger"""
        self.running = False
        self.info("Logger stopped")
    
    def clear_logs(self, keep_count=5):
        """Manually clear old logs"""
        self._clean_old_logs(keep_count)
        self.info(f"Cleaned logs, kept last {keep_count} files")


# Global logger instance
_global_logger = None

def get_logger():
    """Get global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger()
    return _global_logger