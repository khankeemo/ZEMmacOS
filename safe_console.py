# safe_console.py - Safe console wrapper with REAL-TIME progress support
import tkinter as tk
from datetime import datetime

class SafeConsole:
    """Wrapper for console text widget with safe operations and real-time progress updates"""
    
    def __init__(self, text_widget):
        """
        Initialize safe console
        
        Args:
            text_widget: ScrolledText widget to display output
        """
        self._text_widget = text_widget
        self._widget_lock = False
        self._last_progress_line = None  # Track the last progress line for updates
        
    @property
    def text_widget(self):
        """Safely get text widget with existence check"""
        if self._text_widget and self._widget_lock is False:
            try:
                if self._text_widget.winfo_exists():
                    return self._text_widget
            except:
                pass
        return None
    
    def is_valid(self):
        """Check if widget exists and is valid"""
        return self.text_widget is not None
    
    def insert(self, index, text, tags=None):
        """Safely insert text into widget"""
        widget = self.text_widget
        if widget:
            try:
                if tags:
                    widget.insert(index, text, tags)
                else:
                    widget.insert(index, text)
                return True
            except:
                pass
        return False
    
    def delete(self, start, end):
        """Safely delete text from widget"""
        widget = self.text_widget
        if widget:
            try:
                widget.delete(start, end)
                return True
            except:
                pass
        return False
    
    def see(self, index):
        """Safely scroll to index"""
        widget = self.text_widget
        if widget:
            try:
                widget.see(index)
                return True
            except:
                pass
        return False
    
    def tag_config(self, tag_name, **kwargs):
        """Safely configure tag"""
        widget = self.text_widget
        if widget:
            try:
                widget.tag_config(tag_name, **kwargs)
                return True
            except:
                pass
        return False
    
    def clear(self):
        """Safely clear console"""
        if self.delete(1.0, tk.END):
            self.insert(tk.END, "Console cleared.\n", "info")
            self._last_progress_line = None
            return True
        return False
    
    def append(self, message, message_type="info"):
        """Safely append message with timestamp and color"""
        widget = self.text_widget
        if not widget:
            return False
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color mapping
        colors = {
            "info": "#51cf66",
            "error": "#ff6b6b",
            "warning": "#ffd43b",
            "output": "#d4d4d4",
            "debug": "#888888",
            "success": "#00ff88",
            "progress": "#0071e3"
        }
        
        color = colors.get(message_type, "#d4d4d4")
        
        try:
            # Insert timestamp
            widget.insert(tk.END, f"[{timestamp}] ", "timestamp")
            widget.tag_config("timestamp", foreground="#888888")
            
            # Insert message
            widget.insert(tk.END, f"{message}\n", message_type)
            widget.tag_config(message_type, foreground=color)
            
            # Auto-scroll
            widget.see(tk.END)
            
            # Reset progress line tracking when a non-progress message is added
            if message_type != "progress":
                self._last_progress_line = None
                
            return True
        except:
            return False
    
    def update_progress_line(self, message):
        """
        Update the last progress line in console (for live download status)
        This replaces the previous progress line instead of adding a new one
        
        Args:
            message: The progress message to display
            
        Returns:
            bool: True if successful, False otherwise
        """
        widget = self.text_widget
        if not widget:
            return False
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        try:
            # If we have a previous progress line, replace it
            if self._last_progress_line is not None:
                # Delete the last progress line
                widget.delete("end-2l", "end-1c")
            
            # Insert new progress line
            widget.insert(tk.END, f"{formatted_message}\n", "progress")
            widget.tag_config("progress", foreground="#0071e3")
            
            # Store reference to this line
            self._last_progress_line = formatted_message
            
            # Auto-scroll
            widget.see(tk.END)
            return True
        except Exception as e:
            # Fallback: just append normally
            return self.append(message, "progress")
    
    def update_widget(self, new_widget):
        """Update the underlying widget reference (for UI reloads)"""
        self._widget_lock = True
        self._text_widget = new_widget
        self._widget_lock = False
        self._last_progress_line = None
    
    def lock(self):
        """Lock widget updates"""
        self._widget_lock = True
    
    def unlock(self):
        """Unlock widget updates"""
        self._widget_lock = False