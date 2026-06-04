# console_manager.py - Handles live console streaming
import threading
import queue
from datetime import datetime
import os

class ConsoleManager:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.output_queue = queue.Queue()
        self.running = True
        
        # Setup log file
        self.setup_log_file()
        
        # Start queue processor
        self.start_queue_processor()
        
    def setup_log_file(self):
        """Setup log file for this console session"""
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = os.path.join(logs_dir, f"console_{timestamp}.log")
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")
        
    def start_queue_processor(self):
        def process_queue():
            while self.running:
                try:
                    message, message_type = self.output_queue.get(timeout=0.1)
                    self._append_to_console(message, message_type)
                except queue.Empty:
                    continue
                    
        thread = threading.Thread(target=process_queue, daemon=True)
        thread.start()
        
    def _append_to_console(self, message, message_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Write to log file
        try:
            self.log_file.write(f"[{timestamp}] [{message_type.upper()}] {message}\n")
            self.log_file.flush()
        except:
            pass
        
        # Write to UI
        if self.text_widget:
            try:
                if self.text_widget.winfo_exists():
                    colors = {
                        "info": "#51cf66",
                        "error": "#ff6b6b",
                        "warning": "#ffd43b",
                        "output": "#d4d4d4"
                    }
                    color = colors.get(message_type, "#d4d4d4")
                    
                    self.text_widget.insert(tk.END, f"[{timestamp}] ", "timestamp")
                    self.text_widget.tag_config("timestamp", foreground="#888888")
                    self.text_widget.insert(tk.END, f"{message}\n", message_type)
                    self.text_widget.tag_config(message_type, foreground=color)
                    self.text_widget.see(tk.END)
            except:
                pass
        
    def log(self, message, message_type="info"):
        self.output_queue.put((message, message_type))
        
    def clear(self):
        if self.text_widget:
            try:
                self.text_widget.delete(1.0, tk.END)
            except:
                pass
        self.log("Console cleared", "info")
        
    def stop(self):
        self.running = False
        try:
            self.log_file.close()
        except:
            pass

# Import tkinter for tag_config
import tkinter as tk