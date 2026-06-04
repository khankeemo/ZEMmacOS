# themes.py
import tkinter as tk
from tkinter import ttk

# ===================================================================
# COLOR PALETTES
# ===================================================================
LIGHT_THEME = {
    "root_bg": "#f5f5f7",
    "sidebar_bg": "#ffffff",
    "content_bg": "#f5f5f7",
    "card_bg": "#ffffff",
    "header_bg": "#f5f5f7",
    "text": "#1d1d1f",
    "muted": "#86868b",
    "border": "#e0e0e0",
    "input_bg": "#ffffff",
    "input_fg": "#1d1d1f",
    "console_bg": "#1e1e1e",
    "console_fg": "#d4d4d4",
    "accent": "#0071e3",
    "accent_hover": "#005bbf",
    "success": "#34c759",
    "warning": "#ff9f0a",
    "error": "#ff3b30",
    "btn_primary_fg": "#ffffff",
    "btn_secondary_fg": "#1d1d1f",
    "btn_secondary_bg": "#e5e5ea"
}

DARK_THEME = {
    "root_bg": "#1a1a1a",
    "sidebar_bg": "#2d2d2d",
    "content_bg": "#1a1a1a",
    "card_bg": "#2d2d2d",
    "header_bg": "#1a1a1a",
    "text": "#ffffff",
    "muted": "#8e8e93",
    "border": "#3a3a3a",
    "input_bg": "#3a3a3a",
    "input_fg": "#ffffff",
    "console_bg": "#111111",
    "console_fg": "#d4d4d4",
    "accent": "#0a84ff",
    "accent_hover": "#409cff",
    "success": "#32d74b",
    "warning": "#ff9f0a",
    "error": "#ff453a",
    "btn_primary_fg": "#ffffff",
    "btn_secondary_fg": "#ffffff",
    "btn_secondary_bg": "#3a3a3a"
}

# ===================================================================
# THEME APPLICATION ENGINE
# ===================================================================
def apply_theme(app, mode):
    """
    Recursively applies theme colors to the entire application.
    Args:
        app: The main application instance (ZEMmacOSApp)
        mode: 'light' or 'dark'
    """
    # 1. Update App Color Dictionary
    if mode == "dark":
        new_colors = DARK_THEME.copy()
        app.theme_mode = "dark"
    else:
        new_colors = LIGHT_THEME.copy()
        app.theme_mode = "light"

    app.colors.update(new_colors)

    # 2. Configure TTK Styles Dynamically
    style = ttk.Style()
    
    # Frame Styles
    style.configure("TFrame", background=new_colors["root_bg"])
    style.configure("Sidebar.TFrame", background=new_colors["sidebar_bg"])
    style.configure("Card.TFrame", background=new_colors["card_bg"])
    
    # Label Styles
    style.configure("TLabel", background=new_colors["root_bg"], foreground=new_colors["text"])
    style.configure("Sidebar.TLabel", background=new_colors["sidebar_bg"], foreground=new_colors["text"])
    style.configure("Muted.TLabel", background=new_colors["root_bg"], foreground=new_colors["muted"])
    
    # Button Styles (Preserve Semantic Colors)
    style.configure("TButton", background=new_colors["accent"], foreground=new_colors["btn_primary_fg"])
    style.map("TButton",
              background=[('active', new_colors["accent_hover"])],
              foreground=[('active', new_colors["btn_primary_fg"])])
              
    # Entry/Combobox Styles
    style.configure("TEntry", fieldbackground=new_colors["input_bg"], foreground=new_colors["input_fg"])
    style.configure("TCombobox", fieldbackground=new_colors["input_bg"], foreground=new_colors["input_fg"])
    
    # Notebook Style - Main Application
    style.configure("TNotebook", background=new_colors["content_bg"], borderwidth=0)
    style.configure("TNotebook.Tab", 
                   padding=[15, 8],
                   font=("SF Pro Text", 11, "bold"),
                   background=new_colors["card_bg"],
                   foreground=new_colors["text"])
    style.map("TNotebook.Tab",
              background=[("selected", new_colors["accent"]),
                         ("active", new_colors["accent_hover"])],
              foreground=[("selected", "#ffffff"),
                         ("active", new_colors["text"])],
              expand=[("selected", [1, 1, 1, 0])])
    
    # Notebook Style - Modal/License Manager (Improved readability)
    style.configure("Modal.TNotebook", background=new_colors["card_bg"], borderwidth=0)
    style.configure("Modal.TNotebook.Tab", 
                   padding=[15, 10],
                   font=("SF Pro Text", 11, "bold"),
                   background=new_colors["card_bg"],
                   foreground=new_colors["text"])
    style.map("Modal.TNotebook.Tab",
              background=[("selected", new_colors["accent"]),
                         ("active", new_colors["accent_hover"])],
              foreground=[("selected", "#ffffff"),
                         ("active", new_colors["text"])],
              focus=[("selected", new_colors["accent"])])

    # 3. Recursively Update Tkinter Widgets
    _update_widget_colors(app.root, new_colors)

    # 4. Force Refresh Current Page
    if hasattr(app, 'current_view'):
        if hasattr(app, 'update_license_badge'):
            app.update_license_badge()
        
        # Refresh notebook tabs if they exist
        for widget in app.root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.configure(style="TNotebook")
        
        app.root.update_idletasks()


def _get_widget_role(widget):
    """Determines the semantic role of a widget based on its attributes or hierarchy."""
    w_name = str(widget).lower()
    
    # Sidebar Detection
    if "sidebar" in w_name or getattr(widget, '_role', None) == 'sidebar':
        return 'sidebar'
        
    # Console Detection
    if "console" in w_name or getattr(widget, '_role', None) == 'console':
        return 'console'
        
    # Card/Panel Detection
    if "card" in w_name or "panel" in w_name or getattr(widget, '_role', None) == 'card':
        return 'card'
        
    # Default Content
    return 'content'


def _update_widget_colors(widget, colors):
    """Recursively updates colors for a widget and its children based on role."""
    try:
        role = _get_widget_role(widget)
        w_type = widget.winfo_class()
        
        # Determine Background/Foreground based on Role
        if role == 'sidebar':
            bg = colors['sidebar_bg']
            fg = colors['text']
        elif role == 'console':
            bg = colors['console_bg']
            fg = colors['console_fg']
        elif role == 'card':
            bg = colors['card_bg']
            fg = colors['text']
        else:  # Content/Root
            bg = colors['root_bg']
            fg = colors['text']

        # Apply to Tkinter Widgets
        if w_type in ("Frame", "Labelframe"):
            widget.config(bg=bg)
            
        elif w_type == "Label":
            widget.config(bg=bg, fg=fg)
            
        elif w_type == "Button":
            current_bg = widget.cget('bg')
            if current_bg in [LIGHT_THEME['accent'], DARK_THEME['accent'], 
                              LIGHT_THEME['success'], DARK_THEME['success'], 
                              LIGHT_THEME['warning'], DARK_THEME['warning'], 
                              LIGHT_THEME['error'], DARK_THEME['error']]:
                widget.config(fg="#ffffff")
            else:
                widget.config(bg=colors['btn_secondary_bg'], fg=colors['btn_secondary_fg'])
                
        elif w_type == "Entry":
            widget.config(bg=colors['input_bg'], fg=colors['input_fg'], insertbackground=colors['text'])
            
        elif w_type == "Text":
            if role != 'console':
                widget.config(bg=colors['input_bg'], fg=colors['input_fg'], insertbackground=colors['text'])
            else:
                widget.config(bg=colors['console_bg'], fg=colors['console_fg'], insertbackground="white")
                 
        elif w_type == "Listbox":
            widget.config(bg=colors['console_bg'], fg=colors['console_fg'], selectbackground=colors['accent'])
            
        elif w_type == "Canvas":
            widget.config(bg=bg)
            
        elif w_type == "Toplevel":
            widget.config(bg=bg)
            
        elif isinstance(widget, ttk.Notebook):
            # Update notebook style dynamically
            if "modal" in str(widget).lower():
                widget.configure(style="Modal.TNotebook")
            else:
                widget.configure(style="TNotebook")

    except Exception:
        pass

    # Recurse through children
    for child in widget.winfo_children():
        _update_widget_colors(child, colors)


def apply_theme_to_window(window, colors):
    """Applies theme to a standalone popup window."""
    try:
        bg = colors['root_bg']
        window.config(bg=bg)
        
        # Update notebook style if present
        for child in window.winfo_children():
            if isinstance(child, ttk.Notebook):
                child.configure(style="Modal.TNotebook")
            _update_widget_colors(child, colors)
    except:
        pass


if __name__ == "__main__":
    print("\n" + "="*50)
    print("   Themes Module Test")
    print("="*50)
    
    print("\nLight Theme Colors:")
    for key, value in LIGHT_THEME.items():
        print(f"  {key}: {value}")
    
    print("\nDark Theme Colors:")
    for key, value in DARK_THEME.items():
        print(f"  {key}: {value}")
    
    print("\nThemes module ready")