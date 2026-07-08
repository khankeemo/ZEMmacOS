import tkinter as tk
from tkinter import ttk
import platform
import subprocess

LIGHT_THEME = {
    "root_bg": "#f5f5f7",
    "sidebar_bg": "#ffffff",
    "content_bg": "#f5f5f7",
    "card_bg": "#ffffff",
    "header_bg": "#f5f5f7",
    "text": "#1d1d1f",
    "text_secondary": "#6e6e73",
    "muted": "#86868b",
    "border": "#e0e0e0",
    "border_light": "#f0f0f0",
    "input_bg": "#ffffff",
    "input_fg": "#1d1d1f",
    "input_border": "#c7c7cc",
    "console_bg": "#1e1e1e",
    "console_fg": "#d4d4d4",
    "accent": "#0071e3",
    "accent_hover": "#0077ed",
    "accent_active": "#006edb",
    "success": "#34c759",
    "success_bg": "#e8f8ed",
    "success_text": "#1a7a2e",
    "warning": "#ff9f0a",
    "warning_bg": "#fff4e5",
    "warning_text": "#b26500",
    "error": "#ff3b30",
    "error_bg": "#fde8e8",
    "error_text": "#a31a1a",
    "info": "#0071e3",
    "info_bg": "#e8f4fd",
    "info_text": "#004080",
    "btn_primary_fg": "#ffffff",
    "btn_secondary_fg": "#1d1d1f",
    "btn_secondary_bg": "#e5e5ea",
    "btn_secondary_hover": "#d1d1d6",
    "nav_active_bg": "#0071e3",
    "nav_active_fg": "#ffffff",
    "nav_hover_bg": "#f0f0f0",
    "nav_inactive_fg": "#6e6e73",
    "progress_bg": "#e9e9ed",
    "progress_fill": "#0071e3",
    "shadow_color": "#a0a0a0",
    "scrollbar_bg": "#e9e9ed",
    "scrollbar_fg": "#bcbcbc",
    "toast_success_bg": "#34c759",
    "toast_error_bg": "#ff3b30",
    "toast_warning_bg": "#ff9f0a",
    "toast_info_bg": "#0071e3",
    "toast_text": "#ffffff",
    "sidebar_width": 220,
    "card_radius": 14,
    "button_radius": 9,
    "input_radius": 8,
}

DARK_THEME = {
    "root_bg": "#1a1a1a",
    "sidebar_bg": "#252525",
    "content_bg": "#1a1a1a",
    "card_bg": "#2c2c2e",
    "header_bg": "#1a1a1a",
    "text": "#f5f5f7",
    "text_secondary": "#a1a1a6",
    "muted": "#8e8e93",
    "border": "#3a3a3c",
    "border_light": "#333335",
    "input_bg": "#3a3a3c",
    "input_fg": "#f5f5f7",
    "input_border": "#48484a",
    "console_bg": "#111111",
    "console_fg": "#d4d4d4",
    "accent": "#0a84ff",
    "accent_hover": "#409cff",
    "accent_active": "#0071e3",
    "success": "#32d74b",
    "success_bg": "#1a3a1a",
    "success_text": "#6bdb7b",
    "warning": "#ff9f0a",
    "warning_bg": "#3a2a0a",
    "warning_text": "#ffcc66",
    "error": "#ff453a",
    "error_bg": "#3a1a1a",
    "error_text": "#ff7066",
    "info": "#0a84ff",
    "info_bg": "#1a2a3a",
    "info_text": "#66bbff",
    "btn_primary_fg": "#ffffff",
    "btn_secondary_fg": "#f5f5f7",
    "btn_secondary_bg": "#3a3a3c",
    "btn_secondary_hover": "#48484a",
    "nav_active_bg": "#0a84ff",
    "nav_active_fg": "#ffffff",
    "nav_hover_bg": "#3a3a3c",
    "nav_inactive_fg": "#8e8e93",
    "progress_bg": "#3a3a3c",
    "progress_fill": "#0a84ff",
    "shadow_color": "#000000",
    "scrollbar_bg": "#3a3a3c",
    "scrollbar_fg": "#555557",
    "toast_success_bg": "#32d74b",
    "toast_error_bg": "#ff453a",
    "toast_warning_bg": "#ff9f0a",
    "toast_info_bg": "#0a84ff",
    "toast_text": "#ffffff",
    "sidebar_width": 220,
    "card_radius": 14,
    "button_radius": 9,
    "input_radius": 8,
}

_THEME_CACHE = {"current_mode": "light"}


def detect_system_theme():
    """Detect Windows dark mode setting"""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception:
            pass
    return "light"


def apply_theme(app, mode):
    if mode == "system":
        mode = detect_system_theme()
    new_colors = DARK_THEME.copy() if mode == "dark" else LIGHT_THEME.copy()
    app.theme_mode = mode
    app.colors.update(new_colors)
    _THEME_CACHE["current_mode"] = mode

    style = ttk.Style()
    style.theme_use("clam")
    bg = new_colors["root_bg"]
    card_bg = new_colors["card_bg"]
    text = new_colors["text"]
    muted = new_colors["muted"]
    accent = new_colors["accent"]
    input_bg = new_colors["input_bg"]
    input_fg = new_colors["input_fg"]
    border = new_colors["border"]
    success = new_colors["success"]
    warning = new_colors["warning"]
    error = new_colors["error"]

    style.configure(".", background=bg, foreground=text, fieldbackground=input_bg)

    style.configure("TFrame", background=bg)
    style.configure("Card.TFrame", background=card_bg)
    style.configure("Sidebar.TFrame", background=new_colors["sidebar_bg"])

    style.configure("TLabel", background=bg, foreground=text)
    style.configure("Card.TLabel", background=card_bg, foreground=text)
    style.configure("Muted.TLabel", background=bg, foreground=muted)
    style.configure("CardMuted.TLabel", background=card_bg, foreground=muted)
    style.configure("H1.TLabel", background=bg, foreground=text, font=("SF Pro Display", 24, "bold"))
    style.configure("H2.TLabel", background=card_bg, foreground=text, font=("SF Pro Text", 14, "bold"))

    style.configure("TButton", background=accent, foreground="#ffffff", borderwidth=0, focuscolor="none")
    style.map("TButton", background=[("active", new_colors["accent_hover"])])
    style.configure("Secondary.TButton", background=new_colors["btn_secondary_bg"], foreground=new_colors["btn_secondary_fg"], borderwidth=0)
    style.map("Secondary.TButton", background=[("active", new_colors["btn_secondary_hover"])])
    style.configure("Success.TButton", background=success, foreground="#ffffff", borderwidth=0)
    style.map("Success.TButton", background=[("active", "#2db84a")])
    style.configure("Warning.TButton", background=warning, foreground="#ffffff", borderwidth=0)
    style.map("Warning.TButton", background=[("active", "#e08e00")])
    style.configure("Error.TButton", background=error, foreground="#ffffff", borderwidth=0)
    style.map("Error.TButton", background=[("active", "#cc2a1f")])

    style.configure("TEntry", fieldbackground=input_bg, foreground=input_fg, borderwidth=1, relief="solid")
    style.map("TEntry", fieldbackground=[("focus", input_bg)])

    style.configure("TCombobox", fieldbackground=input_bg, foreground=input_fg, background=input_bg, arrowcolor=text)
    style.map("TCombobox", fieldbackground=[("readonly", input_bg)])

    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", padding=[14, 8], font=("SF Pro Text", 11), background=card_bg, foreground=text)
    style.map("TNotebook.Tab", background=[("selected", accent), ("active", new_colors["accent_hover"])],
              foreground=[("selected", "#ffffff"), ("active", text)])

    style.configure("Horizontal.TProgressbar", background=accent, troughcolor=new_colors["progress_bg"], borderwidth=0, thickness=8)

    style.configure("TSeparator", background=border)

    style.configure("TCheckbutton", background=bg, foreground=text)
    style.configure("TRadiobutton", background=bg, foreground=text)
    style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", text)])
    style.map("TRadiobutton", background=[("active", bg)], foreground=[("active", text)])

    _update_widget_colors(app.root, new_colors)

    if hasattr(app, "current_view"):
        for widget in app.root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.configure(style="TNotebook")
        app.root.update_idletasks()


def _update_widget_colors(widget, colors):
    try:
        w_type = widget.winfo_class()
        role = getattr(widget, "_role", None)

        if role == "sidebar":
            bg, fg = colors["sidebar_bg"], colors["text"]
        elif role == "card":
            bg, fg = colors["card_bg"], colors["text"]
        elif role == "console":
            bg, fg = colors["console_bg"], colors["console_fg"]
        elif role == "header":
            bg, fg = colors["header_bg"], colors["text"]
        elif role and role.startswith("toast"):
            bg, fg = colors["toast_info_bg"], colors["toast_text"]
        else:
            bg, fg = colors["root_bg"], colors["text"]

        if w_type in ("Frame", "Labelframe"):
            widget.config(bg=bg)
        elif w_type == "Label":
            widget.config(bg=bg, fg=fg)
        elif w_type == "Button":
            try:
                current_bg = widget.cget("bg")
                accent_set = {colors["accent"], colors["success"], colors["warning"], colors["error"],
                              LIGHT_THEME["accent"], DARK_THEME["accent"],
                              LIGHT_THEME["success"], DARK_THEME["success"],
                              LIGHT_THEME["warning"], DARK_THEME["warning"],
                              LIGHT_THEME["error"], DARK_THEME["error"]}
                if current_bg in accent_set:
                    widget.config(fg="#ffffff")
                else:
                    widget.config(bg=colors["btn_secondary_bg"], fg=colors["btn_secondary_fg"])
            except:
                widget.config(bg=colors["btn_secondary_bg"], fg=colors["btn_secondary_fg"])
        elif w_type == "Entry":
            widget.config(bg=colors["input_bg"], fg=colors["input_fg"], insertbackground=colors["text"])
        elif w_type == "Text":
            if role == "console":
                widget.config(bg=colors["console_bg"], fg=colors["console_fg"], insertbackground="white")
            else:
                widget.config(bg=colors["input_bg"], fg=colors["input_fg"], insertbackground=colors["text"])
        elif w_type == "Listbox":
            widget.config(bg=colors["input_bg"], fg=colors["input_fg"], selectbackground=colors["accent"])
        elif w_type == "Canvas":
            widget.config(bg=bg)
        elif w_type == "Toplevel":
            widget.config(bg=bg)
    except:
        pass

    for child in widget.winfo_children():
        _update_widget_colors(child, colors)
