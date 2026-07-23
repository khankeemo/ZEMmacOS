import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import math
import os
import sys
import time
from PIL import Image, ImageTk, ImageDraw
from safe_console import SafeConsole
from modern_widgets import ModernCard, ModernProgressBar, StatusBadge, ThemeToggle, DebugConsole

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _create_roundrect(canvas, x1, y1, x2, y2, r=8, **kwargs):
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r,
                      start=90, extent=90, **kwargs)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r,
                      start=0, extent=90, **kwargs)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2,
                      start=180, extent=90, **kwargs)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2,
                      start=270, extent=90, **kwargs)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)


class ZEMmacOSUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZEMmacOS")
        self.root.geometry("1260x820")
        self.root.minsize(1000, 700)

        self.current_view = "dashboard"
        self.theme_mode = "light"
        self.colors = {}

        self._fetch_callback = None
        self._download_callback = None
        self._clear_callback = None
        self._settings_callback = None
        self._pause_callback = None
        self._resume_callback = None
        self._cancel_callback = None
        self._copy_callback = None
        self._clean_callback = None
        self._clean_logs_callback = None
        self._theme_toggle_callback = None
        self._check_updates_callback = None
        self._nav_buttons = {}
        self._toast_widgets = []
        self._license_badge = None
        self._dashboard_license_widgets = {}
        self._lock_overlay = None
        self._live_log_viewer = None

        self._init_light_colors()
        self.setup_styles()
        self._main_ui_built = False

    def _init_light_colors(self):
        self.colors = {
            "root_bg": "#f5f5f7", "sidebar_bg": "#ffffff", "content_bg": "#f5f5f7",
            "card_bg": "#ffffff", "header_bg": "#f5f5f7", "text": "#1d1d1f",
            "text_secondary": "#6e6e73", "muted": "#86868b", "border": "#e0e0e0",
            "border_light": "#f0f0f0", "input_bg": "#ffffff", "input_fg": "#1d1d1f",
            "input_border": "#c7c7cc", "console_bg": "#1e1e1e", "console_fg": "#d4d4d4",
            "accent": "#0071e3", "accent_hover": "#0077ed", "accent_active": "#006edb",
            "success": "#34c759", "success_bg": "#e8f8ed", "success_text": "#1a7a2e",
            "warning": "#ff9f0a", "warning_bg": "#fff4e5", "warning_text": "#b26500",
            "error": "#ff3b30", "error_bg": "#fde8e8", "error_text": "#a31a1a",
            "info": "#0071e3", "info_bg": "#e8f4fd", "info_text": "#004080",
            "btn_primary_fg": "#ffffff", "btn_secondary_fg": "#1d1d1f",
            "btn_secondary_bg": "#e5e5ea", "btn_secondary_hover": "#d1d1d6",
            "nav_active_bg": "#0071e3", "nav_active_fg": "#ffffff",
            "nav_hover_bg": "#f0f0f0", "nav_inactive_fg": "#6e6e73",
            "progress_bg": "#e9e9ed", "progress_fill": "#0071e3",
            "shadow_color": "#a0a0a0",
            "toast_info_bg": "#0071e3", "toast_success_bg": "#34c759",
            "toast_error_bg": "#ff3b30", "toast_warning_bg": "#ff9f0a",
            "toast_text": "#ffffff",
        }

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TNotebook", background=self.colors["content_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=[12, 8], font=("SF Pro Text", 11),
                        background=self.colors["card_bg"], foreground=self.colors["text"])
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])],
                  foreground=[("selected", "#ffffff")])

    def load_logo(self):
        if hasattr(self, "_logo_loaded") and self._logo_loaded:
            return
        self._logo_loaded = True
        self.logo_image = None
        logo_path = os.path.join(BASE_DIR, "public", "images", "logo.png")
        try:
            if os.path.exists(logo_path):
                img = Image.open(logo_path).convert("RGBA").resize((56, 56), Image.Resampling.LANCZOS)
                mask = Image.new("L", (56, 56), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((1, 1, 54, 54), fill=255)
                result = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
                result.paste(img, (0, 0), mask)
                self.logo_image = ImageTk.PhotoImage(result)
                if hasattr(self, "logo_label"):
                    self.logo_label.config(image=self.logo_image, bg=self.colors["sidebar_bg"])
            elif hasattr(self, "logo_label"):
                self.logo_label.config(text="Z", font=("SF Pro Display", 24, "bold"),
                                       fg=self.colors["accent"], bg=self.colors["sidebar_bg"])
        except Exception:
            pass

    def build_main_ui(self):
        if self._main_ui_built:
            return
        self.create_ui()
        self.load_logo()
        self._main_ui_built = True

    def create_ui(self):
        main_container = tk.Frame(self.root, bg=self.colors["root_bg"])
        main_container.pack(fill=tk.BOTH, expand=True)
        self.create_sidebar(main_container)
        self.create_content_area(main_container)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.colors["sidebar_bg"], width=self.colors.get("sidebar_width", 220))
        sidebar._role = "sidebar"
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self.sidebar_frame = sidebar

        logo_frame = tk.Frame(sidebar, bg=self.colors["sidebar_bg"])
        logo_frame.pack(fill=tk.X, pady=28)
        self.logo_label = tk.Label(logo_frame, text="", bg=self.colors["sidebar_bg"])
        self.logo_label.pack()
        tk.Label(logo_frame, text="ZEMmacOS", font=("SF Pro Display", 18, "bold"),
                 fg=self.colors["text"], bg=self.colors["sidebar_bg"]).pack(pady=4)
        tk.Label(logo_frame, text="macOS Download Manager", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["sidebar_bg"]).pack()

        sep = tk.Frame(sidebar, bg=self.colors["border"], height=1)
        sep.pack(fill=tk.X, padx=18, pady=12)

        nav_items = [
            ("dashboard", "Dashboard"),
            ("library", "Library"),
            ("settings", "Settings"),
        ]
        for key, label in nav_items:
            btn = tk.Button(
                sidebar, text=label,
                command=lambda k=key: self._nav_click(k),
                font=("SF Pro Text", 12),
                fg=self.colors["nav_inactive_fg"],
                bg=self.colors["sidebar_bg"],
                activebackground=self.colors["nav_hover_bg"],
                activeforeground=self.colors["text"],
                bd=0, anchor="w", padx=24, pady=10,
                cursor="hand2",
            )
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.colors["nav_hover_bg"])
                     if b.cget("bg") != self.colors["nav_active_bg"] else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors["sidebar_bg"])
                     if b.cget("bg") != self.colors["nav_active_bg"] else None)
            btn.bind('<Return>', lambda e, k=key: self._nav_click(k))
            btn.bind('<KP_Enter>', lambda e, k=key: self._nav_click(k))
            self._nav_buttons[key] = btn

        self._update_nav("dashboard")

        footer = tk.Frame(sidebar, bg=self.colors["sidebar_bg"])
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 12))

        sep = tk.Frame(footer, bg=self.colors["border"], height=1)
        sep.pack(fill=tk.X, padx=16, pady=(0, 10))

        footer_lines = [
            ("Powered by Websmith Digital\u2122", ("SF Pro Text", 8, "bold"), True),
            ("Universal License Controller", ("SF Pro Text", 7), False),
            ("Protected by Brevo and Websmith", ("SF Pro Text", 7), False),
            ("Kolkata, West Bengal, India", ("SF Pro Text", 7), False),
        ]
        for text, font, clickable in footer_lines:
            lbl = tk.Label(
                footer,
                text=text,
                font=font,
                fg=self.colors.get("muted", "#86868b"),
                bg=self.colors["sidebar_bg"],
                cursor="hand2" if clickable else "",
                anchor=tk.CENTER,
            )
            lbl.pack(fill=tk.X, pady=(0, 1))
            if clickable:
                lbl.bind("<Button-1>", lambda e: self._on_about_clicked())

    def _on_about_clicked(self):
        from WSD_SDKToolkit_ZEMMACOS import UniversalLicenseCenter
        import os
        from pathlib import Path
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = Path(base) / 'WSD_SDKToolkit_ZEMMACOS' / 'config' / 'api-config.json'
        center = UniversalLicenseCenter(config_path=str(config_path))
        center.show()

    def _nav_click(self, key):
        views = {
            "dashboard": self.show_dashboard,
            "library": self.show_library,
            "settings": self.show_settings,
        }
        self._update_nav(key)
        if key in views:
            views[key]()

    def _update_nav(self, active_key):
        for key, btn in self._nav_buttons.items():
            if key == active_key:
                btn.config(bg=self.colors["nav_active_bg"], fg=self.colors["nav_active_fg"])
            else:
                btn.config(bg=self.colors["sidebar_bg"], fg=self.colors["nav_inactive_fg"])

    def create_content_area(self, parent):
        self.content_area = tk.Frame(parent, bg=self.colors["content_bg"])
        self.content_area._role = "content"
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # ---- Toast Notifications ----

    def show_toast(self, message, toast_type="info", duration=3000):
        cmap = {
            "info": (self.colors["toast_info_bg"], self.colors["toast_text"]),
            "success": (self.colors["toast_success_bg"], self.colors["toast_text"]),
            "error": (self.colors["toast_error_bg"], self.colors["toast_text"]),
            "warning": (self.colors["toast_warning_bg"], self.colors["toast_text"]),
        }
        bg, fg = cmap.get(toast_type, cmap["info"])

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=bg)
        toast._role = f"toast_{toast_type}"

        tk.Label(toast, text=message, font=("SF Pro Text", 11),
                 fg=fg, bg=bg, padx=22, pady=11).pack()

        toast.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width() - toast.winfo_width() - 22
        y = self.root.winfo_y() + 22
        toast.geometry(f"+{x}+{y}")
        toast.attributes("-alpha", 0.0)

        self._toast_widgets.append(toast)

        def fade_in(w, step):
            try:
                a = min(1.0, step * 0.08)
                w.attributes("-alpha", a)
                if a < 1.0:
                    self.root.after(20, lambda: fade_in(w, step + 1))
            except:
                pass

        def fade_out(w, remaining):
            if remaining <= 0:
                try:
                    w.destroy()
                except:
                    pass
                return
            try:
                a = min(1.0, remaining / 300)
                w.attributes("-alpha", a)
            except:
                pass
            self.root.after(50, lambda: fade_out(w, remaining - 50))

        self.root.after(50, lambda: fade_in(toast, 0))
        self.root.after(duration, lambda: fade_out(toast, 300))

    # -----------------------------------------------------------------
    # CUSTOM MODAL DIALOG HELPERS
    # -----------------------------------------------------------------
    def _make_modal_dialog(self, w, h, close_cb=None):
        c = self.colors
        d = tk.Toplevel(self.root)
        d.title("")
        d.overrideredirect(True)
        d.transient(self.root)
        d.resizable(False, False)
        if close_cb:
            d.protocol("WM_DELETE_WINDOW", close_cb)

        canvas = tk.Canvas(d, width=w, height=h, bg=c["card_bg"],
                           highlightthickness=0)
        canvas.pack()
        _create_roundrect(canvas, 0, 0, w, h, r=16,
                          fill=c["card_bg"], outline=c["border"], width=1)
        d.update_idletasks()
        d.tk.call("tk::PlaceWindow", d, "center")
        d.lift()
        d.focus_force()
        d.grab_set()
        d.wait_visibility()
        return d, canvas

    def _make_dialog_button(self, parent, text, bg, fg, cmd, x, y, w, h):
        btn = tk.Button(parent, text=text, font=("SF Pro Text", 10, "bold"),
                        fg=fg, bg=bg, bd=0, cursor="hand2",
                        activebackground=self.colors.get("btn_secondary_hover", "#555"),
                        command=cmd)
        btn.place(x=x, y=y, width=w, height=h)
        return btn

    # -----------------------------------------------------------------
    # NETWORK LOSS DIALOG
    # -----------------------------------------------------------------
    def _show_network_dialog(self, retry_count, on_pause_callback=None):
        if hasattr(self, "_net_dialog") and self._net_dialog and self._net_dialog.winfo_exists():
            self._update_network_dialog(retry_count)
            return
        c = self.colors
        W, H = 250, 280

        d, canvas = self._make_modal_dialog(W, H)
        self._net_dialog = d
        self._net_canvas = canvas
        self._net_countdown_value = 30

        cx = W // 2

        # Wi-Fi signal icon (3 arcs + ground line, with X overlay)
        icon_y = 50
        for r, w in [(22, 3.0), (16, 2.5), (10, 2.0)]:
            canvas.create_arc(cx - r, icon_y - r, cx + r, icon_y + r,
                              start=225, extent=90, fill="",
                              outline=c["warning"], width=w)
        canvas.create_line(cx - 24, icon_y + 4, cx + 24, icon_y + 4,
                           fill=c["warning"], width=3, capstyle="round")

        # Red X overlay
        xs = 9
        x_off = -6
        canvas.create_line(cx - xs, icon_y - xs + x_off,
                           cx + xs, icon_y + xs + x_off,
                           fill=c["error"], width=3, capstyle="round")
        canvas.create_line(cx + xs, icon_y - xs + x_off,
                           cx - xs, icon_y + xs + x_off,
                           fill=c["error"], width=3, capstyle="round")

        # Title
        canvas.create_text(cx, 100, text="Connection Lost",
                           font=("SF Pro Display", 15, "bold"),
                           fill=c["text"], anchor="center")

        # Auto retry
        canvas.create_text(cx, 130, text="Auto retry: 30 s",
                           font=("SF Pro Text", 11),
                           fill=c["muted"], anchor="center")

        # Attempt counter
        self._net_retry_label_id = canvas.create_text(
            cx, 158, text=f"Attempt: {retry_count} / 10",
            font=("SF Pro Text", 12, "bold"),
            fill=c["accent"], anchor="center")

        # Countdown
        self._net_countdown_label_id = canvas.create_text(
            cx, 182, text="Next retry in: 30s",
            font=("SF Pro Text", 10),
            fill=c["muted"], anchor="center")

        # Buttons
        bw, bh = 95, 32
        by = 222

        if on_pause_callback:
            self._make_dialog_button(d, "Pause", c["warning"], "white",
                                     lambda: self._on_net_pause(on_pause_callback),
                                     cx - bw - 6, by, bw, bh)
            self._make_dialog_button(d, "Close", c["btn_secondary_bg"], c["text"],
                                     self._close_network_dialog,
                                     cx + 6, by, bw, bh)
        else:
            self._make_dialog_button(d, "Close", c["btn_secondary_bg"], c["text"],
                                     self._close_network_dialog,
                                     cx - bw // 2, by, bw, bh)

    def _update_network_dialog(self, retry_count):
        if hasattr(self, "_net_canvas") and self._net_canvas.winfo_exists():
            self._net_canvas.itemconfig(self._net_retry_label_id,
                                        text=f"Attempt: {retry_count} / 10")
            self._net_countdown_value = 30
            self._net_canvas.itemconfig(self._net_countdown_label_id,
                                        text="Next retry in: 30s")

    def _update_dialog_countdown(self, seconds):
        if hasattr(self, "_net_canvas") and self._net_canvas.winfo_exists():
            self._net_canvas.itemconfig(self._net_countdown_label_id,
                                        text=f"Next retry in: {seconds}s")

    def _auto_close_network_dialog(self):
        self._net_dialog_open = False
        if hasattr(self, "_net_dialog") and self._net_dialog and self._net_dialog.winfo_exists():
            try:
                self._net_dialog.destroy()
            except:
                pass
        self._net_dialog = None
        self._net_canvas = None
        self.show_toast("\u2705 Internet restored. Resuming download...", "success", 3000)

    def _close_network_dialog(self):
        self._net_dialog_open = False
        if hasattr(self, "_net_dialog") and self._net_dialog and self._net_dialog.winfo_exists():
            try:
                self._net_dialog.destroy()
            except:
                pass
        self._net_dialog = None
        self._net_canvas = None

    def _on_net_pause(self, callback):
        self._close_network_dialog()
        if callback:
            callback()

    # -----------------------------------------------------------------
    # CANCEL CONFIRMATION DIALOG
    # -----------------------------------------------------------------
    def _show_cancel_confirmation(self, on_yes_callback):
        if getattr(self, "_cancel_dialog_open", False):
            return
        self._cancel_dialog_open = True

        c = self.colors
        W, H = 280, 195

        def cleanup():
            self._cancel_dialog_open = False
            if hasattr(self, "_cancel_dialog") and self._cancel_dialog:
                try:
                    self._cancel_dialog.destroy()
                except:
                    pass
                self._cancel_dialog = None

        d, canvas = self._make_modal_dialog(W, H, close_cb=cleanup)
        self._cancel_dialog = d
        cx = W // 2

        # Warning triangle icon
        icon_cx, icon_cy = cx, 36
        tri = canvas.create_polygon(
            icon_cx, icon_cy - 14,
            icon_cx - 14, icon_cy + 8,
            icon_cx + 14, icon_cy + 8,
            fill=c["warning"], outline="", tags="icon")
        # Exclamation bar
        canvas.create_rectangle(icon_cx - 2.5, icon_cy - 7,
                                icon_cx + 2.5, icon_cy + 2,
                                fill="white", outline="", tags="icon")
        # Exclamation dot
        canvas.create_rectangle(icon_cx - 2.5, icon_cy + 4.5,
                                icon_cx + 2.5, icon_cy + 6.5,
                                fill="white", outline="", tags="icon")

        # Text
        canvas.create_text(cx, 82,
                           text="Are you sure you want\nto cancel the download?",
                           font=("SF Pro Text", 12, "bold"),
                           fill=c["text"], anchor="center", justify="center")

        canvas.create_text(cx, 120,
                           text="All downloaded data will be deleted.",
                           font=("SF Pro Text", 10),
                           fill=c["muted"], anchor="center")

        # Buttons
        bw, bh = 100, 32
        by = 148

        def on_yes():
            cleanup()
            on_yes_callback()

        self._make_dialog_button(d, "Yes", c["error"], "white",
                                 on_yes,
                                 cx - bw - 8, by, bw, bh)
        self._make_dialog_button(d, "No", c["btn_secondary_bg"], c["text"],
                                 cleanup,
                                 cx + 8, by, bw, bh)

    # -----------------------------------------------------------------
    # AWS-01: Inactive License Dialog
    # -----------------------------------------------------------------
    def _show_inactive_license_dialog(self):
        if getattr(self, "_inactive_license_dialog_open", False):
            return
        self._inactive_license_dialog_open = True

        c = self.colors
        W, H = 380, 320

        def cleanup():
            self._inactive_license_dialog_open = False
            if hasattr(self, "_inactive_license_dialog") and self._inactive_license_dialog:
                try:
                    self._inactive_license_dialog.destroy()
                except Exception:
                    pass
                self._inactive_license_dialog = None

        d, canvas = self._make_modal_dialog(W, H, close_cb=cleanup)
        self._inactive_license_dialog = d
        cx = W // 2

        canvas.create_oval(cx - 18, 24, cx + 18, 60,
                           fill=c["error"], outline="")
        canvas.create_text(cx, 42, text="!",
                           font=("SF Pro Display", 22, "bold"),
                           fill="white", anchor="center")

        canvas.create_text(cx, 88, text="License Inactive",
                           font=("SF Pro Display", 16, "bold"),
                           fill=c["text"], anchor="center")
        canvas.create_text(cx, 110, text="Device Not Registered",
                           font=("SF Pro Text", 11),
                           fill=c["text_secondary"], anchor="center")

        canvas.create_text(cx, 148, text="License inactive or device not registered.",
                           font=("SF Pro Text", 10),
                           fill=c["text"], anchor="center")

        canvas.create_text(cx, 178, text="Please contact administrator:",
                           font=("SF Pro Text", 10),
                           fill=c["muted"], anchor="center")
        canvas.create_text(cx, 196, text="support@websmithdigital.com",
                           font=("SF Pro Text", 10, "bold"),
                           fill=c["accent"], anchor="center")

        canvas.create_line(50, 214, W - 50, 214, fill=c["border"], width=1)

        canvas.create_text(cx, 232, text="OR",
                           font=("SF Pro Text", 10, "bold"),
                           fill=c["muted"], anchor="center")

        canvas.create_text(cx, 252, text="Activate using another registered license.",
                           font=("SF Pro Text", 10),
                           fill=c["text"], anchor="center")

        bw, bh = 140, 34
        by = 276

        self._make_dialog_button(d, "Contact Support", c["accent"], "white",
                                  lambda: self._on_contact_support(),
                                  cx - bw - 6, by, bw, bh)
        self._make_dialog_button(d, "Activate License", c["success"], "white",
                                  lambda: self._on_activate_from_inactive(),
                                  cx + 6, by, bw, bh)

    def _on_contact_support(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("support@websmithdigital.com")
        self.show_toast("Support email copied to clipboard", "info", 2000)

    def _on_activate_from_inactive(self):
        if hasattr(self, "_inactive_license_dialog") and self._inactive_license_dialog:
            try:
                self._inactive_license_dialog.destroy()
            except Exception:
                pass
            self._inactive_license_dialog = None
            self._inactive_license_dialog_open = False
        self._on_activate_license()

    # ---- Dashboard ----

    def show_dashboard(self):
        self.current_view = "dashboard"
        self._update_nav("dashboard")
        self.clear_content()

        colors = self.colors

        header = tk.Frame(self.content_area, bg=colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=24)

        left_h = tk.Frame(header, bg=colors["header_bg"])
        left_h.pack(side=tk.LEFT, anchor=tk.W)
        tk.Label(left_h, text="Dashboard", font=("SF Pro Display", 26, "bold"),
                 fg=colors["text"], bg=colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(left_h, text="Overview of your macOS downloads and activities",
                 font=("SF Pro Text", 11), fg=colors["muted"],
                 bg=colors["header_bg"]).pack(anchor=tk.W, pady=2)

        right_h = tk.Frame(header, bg=colors["header_bg"])
        right_h.pack(side=tk.RIGHT, anchor=tk.N, pady=6, padx=4)
        self._theme_toggle = ThemeToggle(
            right_h,
            command=self._on_theme_toggle,
            colors=colors,
        )
        self._theme_toggle.pack(side=tk.RIGHT, padx=4)
        self._license_badge = tk.Label(
            right_h, text="", font=("SF Pro Text", 9, "bold"),
            fg=colors.get("muted", "#86868b"), bg=colors["header_bg"]
        )
        self._license_badge.pack(side=tk.RIGHT, padx=8)

        body_frame = tk.Frame(self.content_area, bg=colors["content_bg"])
        body_frame.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        stats_row = tk.Frame(body_frame, bg=colors["content_bg"])
        stats_row.pack(fill=tk.X, pady=12)

        stats_keys = ["versions", "downloads", "active", "storage"]
        stats_labels = ["Available Versions", "Downloads", "Active Downloads", "Storage Used"]
        stats_defaults = {"versions": "30+", "downloads": "0", "active": "0", "storage": "0 GB"}
        stats_colors_list = [colors["accent"], colors["success"], colors["warning"], colors["muted"]]
        self._stats_labels = {}
        for i, key in enumerate(stats_keys):
            card = tk.Frame(stats_row, bg=colors["card_bg"],
                            highlightbackground=colors["border"],
                            highlightthickness=1, height=100)
            card._role = "card"
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            stats_row.grid_columnconfigure(i, weight=1)
            card.pack_propagate(False)
            val_label = tk.Label(card, text=stats_defaults.get(key, "0"),
                                 font=("SF Pro Display", 28, "bold"),
                                 fg=stats_colors_list[i], bg=colors["card_bg"])
            val_label.pack(pady=16)
            self._stats_labels[key] = val_label
            tk.Label(card, text=stats_labels[i], font=("SF Pro Text", 10),
                     fg=colors["muted"], bg=colors["card_bg"]).pack()

        self._build_dashboard_license_card(body_frame)

        actions_card = ModernCard(body_frame, colors, title="Quick Actions", padding=18)
        actions_card.pack(fill=tk.X, pady=12)
        act_frame = tk.Frame(actions_card.get_body(), bg=colors["card_bg"])
        act_frame.pack(fill=tk.X)
        for text, cmd, clr in [
            ("Open Library", self.show_library, colors["accent"]),
            ("Clean Temp Files", self._on_clean_temp, colors["warning"]),
            ("Clean Old Logs", self._on_clean_logs, colors["error"]),
        ]:
            btn = tk.Button(act_frame, text=text, command=cmd,
                      font=("SF Pro Text", 11, "bold"),
                      fg="white", bg=clr, activebackground="#5a5a5e",
                      bd=0, padx=20, pady=8, cursor="hand2",
                      width=18)
            btn.pack(side=tk.LEFT, padx=5)
            btn.bind('<Return>', lambda e, c=cmd: c())
            btn.bind('<KP_Enter>', lambda e, c=cmd: c())

        history_card = ModernCard(body_frame, colors, title="Recent Activity", subtitle="Your latest download actions", padding=18)
        history_card.pack(fill=tk.X, pady=12)
        tk.Label(history_card.get_body(), text="No recent activity yet. Start downloading macOS versions to see activity here.",
                 font=("SF Pro Text", 10), fg=colors["muted"], bg=colors["card_bg"]).pack(anchor=tk.W, pady=6)

        info_card = ModernCard(body_frame, colors, title="Getting Started", padding=18)
        info_card.pack(fill=tk.X)
        body = info_card.get_body()
        steps = [
            ("1", "Click 'Library' in the sidebar"),
            ("2", "Click 'FETCH CATALOGUE' to see available macOS versions"),
            ("3", "Enter the index number and click 'DOWNLOAD SELECTED'"),
        ]
        for num, desc in steps:
            row = tk.Frame(body, bg=colors["card_bg"])
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=num, font=("SF Pro Text", 12, "bold"),
                     fg=colors["accent"], bg=colors["card_bg"], width=3).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=("SF Pro Text", 11),
                     fg=colors["text"], bg=colors["card_bg"]).pack(side=tk.LEFT, padx=6)

        self._build_live_log_viewer(body_frame)

    # ---- License ----

    def _build_dashboard_license_card(self, parent):
        colors = self.colors
        card = ModernCard(parent, colors, title="License Overview",
                          subtitle="ZEM MAC OS license status", padding=18)
        card.pack(fill=tk.X, pady=12)
        body = card.get_body()
        rows = [
            ("status", "Status", "--"),
            ("plan", "Plan", "--"),
            ("license_key", "License Number", "--"),
            ("validity", "Validity", "--"),
            ("expiry", "Valid until", "--"),
        ]
        self._dashboard_license_widgets = {}
        for key, label, _ in rows:
            row = tk.Frame(body, bg=colors["card_bg"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label+":", font=("SF Pro Text", 10, "bold"),
                     fg=colors["text_secondary"], bg=colors["card_bg"],
                     width=16, anchor=tk.W).pack(side=tk.LEFT)
            val = tk.Label(row, text="--", font=("SF Pro Text", 10),
                           fg=colors["text"], bg=colors["card_bg"], anchor=tk.W)
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._dashboard_license_widgets[key] = val

        action_row = tk.Frame(body, bg=colors["card_bg"])
        action_row.pack(fill=tk.X, pady=(12, 0))
        self._btn_activate = tk.Button(action_row, text="Activate License",
                  command=self._on_activate_license,
                  font=("SF Pro Text", 10, "bold"),
                  fg="white", bg=colors["accent"],
                  bd=0, padx=14, pady=6, cursor="hand2"
                  )
        self._btn_activate.pack(side=tk.LEFT, padx=2)
        self._btn_activate.bind('<Return>', lambda e: self._on_activate_license())
        self._btn_activate.bind('<KP_Enter>', lambda e: self._on_activate_license())
        self._btn_refresh = tk.Button(action_row, text="Refresh",
                  command=self._on_refresh_license,
                  font=("SF Pro Text", 10, "bold"),
                  fg=colors["text"], bg=colors["btn_secondary_bg"],
                  bd=0, padx=14, pady=6, cursor="hand2"
                  )
        self._btn_refresh.pack(side=tk.LEFT, padx=2)
        self._btn_refresh.bind('<Return>', lambda e: self._on_refresh_license())
        self._btn_refresh.bind('<KP_Enter>', lambda e: self._on_refresh_license())
        self._btn_renew = tk.Button(action_row, text="Renew License",
                  command=self._on_renew_license,
                  font=("SF Pro Text", 10, "bold"),
                  fg="white", bg=colors["success"],
                  bd=0, padx=14, pady=6, cursor="hand2"
                  )
        self._btn_renew.bind('<Return>', lambda e: self._on_renew_license())
        self._btn_renew.bind('<KP_Enter>', lambda e: self._on_renew_license())
        self._btn_renew.pack(side=tk.LEFT, padx=2)

    def _update_dashboard_license(self):
        if not hasattr(self, '_dashboard_license_widgets'):
            return
        w = self._dashboard_license_widgets
        try:
            key = next(iter(w))
            if not w[key] or not w[key].winfo_exists():
                return
        except (tk.TclError, StopIteration, KeyError):
            return
        colors = self.colors
        status_obj = getattr(self, 'license_status', None) if hasattr(self, 'license_status') else None
        engine = getattr(self, 'license_engine', None) if hasattr(self, 'license_engine') else None

        try:
            if status_obj and status_obj.valid:
                is_trial = getattr(status_obj, 'trial_active', False)
                status_text = status_obj.status.upper()
                fg = colors["warning"] if is_trial else colors["success"]
                plan_text = status_obj.plan or ('Trial' if is_trial else 'Active')
                lic_key = getattr(status_obj, 'license_key', '') or ''
                if lic_key and len(lic_key) > 12:
                    formatted = ''
                    for i, ch in enumerate(lic_key):
                        if i > 0 and i % 4 == 0:
                            formatted += '-'
                        formatted += ch
                    lic_key = formatted
                if w.get("status") and w["status"].winfo_exists():
                    w["status"].config(text=status_text, fg=fg)
                if w.get("plan") and w["plan"].winfo_exists():
                    w["plan"].config(text=plan_text)
                if w.get("license_key") and w["license_key"].winfo_exists():
                    w["license_key"].config(text=lic_key or '--')
                days_left = getattr(status_obj, 'days_left', 0) or 0
                if w.get("validity") and w["validity"].winfo_exists():
                    w["validity"].config(text=f"{days_left} days remaining")
                expiry = getattr(status_obj, 'expiry_date', None)
                if expiry and w.get("expiry") and w["expiry"].winfo_exists():
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                        w["expiry"].config(text=dt.strftime('%d %b %Y'))
                    except Exception:
                        w["expiry"].config(text=expiry.split('T')[0])
                elif w.get("expiry") and w["expiry"].winfo_exists():
                    w["expiry"].config(text='--')
            else:
                for key in ('status', 'plan', 'license_key', 'validity', 'expiry'):
                    if w.get(key) and w[key].winfo_exists():
                        txt = "UNLICENSED" if key == 'status' else '--'
                        fg = colors["error"] if key == 'status' else None
                        if fg:
                            w[key].config(text=txt, fg=fg)
                        else:
                            w[key].config(text=txt)
        except tk.TclError:
            pass

    def _update_header_license_badge(self):
        try:
            if not self._license_badge or not self._license_badge.winfo_exists():
                return
        except tk.TclError:
            return
        colors = self.colors
        status_obj = getattr(self, 'license_status', None) if hasattr(self, 'license_status') else None
        try:
            if status_obj and status_obj.valid:
                if status_obj.trial_active:
                    text = f"TRIAL  {status_obj.days_left}d"
                    fg = colors["warning"]
                else:
                    text = f"ACTIVE  {status_obj.days_left}d"
                    fg = colors["success"]
            else:
                text = "UNLICENSED"
                fg = colors["error"]
            self._license_badge.config(text=text, fg=fg)
        except tk.TclError:
            pass

    def _on_activate_license(self):
        act = getattr(self, 'open_activation', None)
        if act:
            act()

    def _on_refresh_license(self):
        ref = getattr(self, 'refresh_license', None)
        if ref:
            ref()

    def _on_renew_license(self):
        ren = getattr(self, 'open_renew_license', None)
        if ren:
            ren()

    # ---- Live Log Viewer ----

    def _build_live_log_viewer(self, parent):
        colors = self.colors
        card = ModernCard(parent, colors, title="Live Log",
                          subtitle="Real-time license integration events", padding=8)
        card.pack(fill=tk.X, pady=(0, 12))
        body = card.get_body()

        header_row = tk.Frame(body, bg=colors["card_bg"])
        header_row.pack(fill=tk.X)
        self._log_filter_var = tk.StringVar(value="ALL")
        filters = ["ALL", "STARTUP", "SDK", "WELCOME", "ACTIVATION", "RENEWAL", "DEVICE", "UI"]
        for f in filters:
            rb = tk.Radiobutton(
                header_row, text=f, variable=self._log_filter_var,
                value=f, command=self._apply_log_filter,
                font=("SF Pro Text", 8), bg=colors["card_bg"],
                fg=colors["text"], selectcolor=colors["card_bg"],
                activebackground=colors["card_bg"],
                indicatoron=False, padx=6, pady=1,
            )
            rb.pack(side=tk.LEFT, padx=1)

        log_frame = tk.Frame(body, bg=colors["card_bg"])
        log_frame.pack(fill=tk.X, pady=(4, 0))
        self._log_text = tk.Text(
            log_frame,
            font=("SF Mono", 8),
            bg=colors.get("input_bg", "#ffffff"),
            fg=colors.get("text", "#1d1d1f"),
            bd=1, relief=tk.FLAT, height=10,
            wrap=tk.WORD, state=tk.DISABLED,
        )
        sb = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        for cat, clr in [
            ("STARTUP", "#5ac8fa"), ("SDK", "#af52de"), ("WELCOME", "#ff9f0a"),
            ("ACTIVATION", "#0071e3"), ("RENEWAL", "#34c759"), ("DEVICE", "#ff6482"),
            ("UI", "#86868b"),
        ]:
            self._log_text.tag_config(f"cat_{cat}", foreground=clr, font=("SF Mono", 8, "bold"))
        for lvl, clr in [
            ("DEBUG", "#888888"), ("INFO", "#51cf66"), ("SUCCESS", "#00ff88"),
            ("WARNING", "#ffd43b"), ("ERROR", "#ff6b6b"),
        ]:
            self._log_text.tag_config(f"lvl_{lvl}", foreground=clr)
        self._log_text.tag_config("ts", foreground="#666666")
        self._log_text.tag_config("detail", foreground="#555555")

        self._log_entries = []
        self._live_log_cb = None

        self.root.after(500, self._connect_live_log)

    def _connect_live_log(self):
        try:
            from live_log import get_live_log
            ll = get_live_log()
            for entry in ll.get_recent(100):
                self._log_entries.append(entry)
            self._apply_log_filter()
            ll.register(self._on_live_log_entry)
            self._live_log_cb = self._on_live_log_entry
        except Exception:
            pass

    def _on_live_log_entry(self, category, level, message, detail):
        self._log_entries.append((category, level, message, detail))
        if len(self._log_entries) > 2000:
            self._log_entries = self._log_entries[-1000:]
        self._apply_log_filter()

    def _apply_log_filter(self):
        try:
            filt = self._log_filter_var.get()
            self._log_text.configure(state=tk.NORMAL)
            self._log_text.delete(1.0, tk.END)
            count = 0
            for cat, lvl, msg, det in reversed(self._log_entries):
                if filt != "ALL" and cat != filt:
                    continue
                from datetime import datetime
                ts = datetime.now().strftime("%H:%M:%S")
                self._log_text.insert(tk.END, f"[{ts}] ", "ts")
                self._log_text.insert(tk.END, f"[{cat:<9}] ", f"cat_{cat}")
                self._log_text.insert(tk.END, f"[{lvl:<7}] ", f"lvl_{lvl}")
                self._log_text.insert(tk.END, f"{msg}\n")
                if det:
                    self._log_text.insert(tk.END, f"  {det}\n", "detail")
                count += 1
                if count >= 100:
                    break
            self._log_text.see(tk.END)
            self._log_text.configure(state=tk.DISABLED)
        except Exception:
            pass

    # ---- Library ----

    def show_library(self):
        self.current_view = "library"
        self._update_nav("library")
        self.clear_content()

        colors = self.colors

        header = tk.Frame(self.content_area, bg=colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=24)

        left_h = tk.Frame(header, bg=colors["header_bg"])
        left_h.pack(side=tk.LEFT, anchor=tk.W)
        tk.Label(left_h, text="Download Library", font=("SF Pro Display", 26, "bold"),
                 fg=colors["text"], bg=colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(left_h, text="Browse and download macOS installer versions",
                 font=("SF Pro Text", 11), fg=colors["muted"],
                 bg=colors["header_bg"]).pack(anchor=tk.W, pady=2)

        right_h = tk.Frame(header, bg=colors["header_bg"])
        right_h.pack(side=tk.RIGHT, anchor=tk.N, pady=6, padx=4)
        self._license_badge = tk.Label(
            right_h, text="", font=("SF Pro Text", 9, "bold"),
            fg=colors.get("muted", "#86868b"), bg=colors["header_bg"]
        )
        self._license_badge.pack(side=tk.RIGHT, padx=8)

        body = tk.Frame(self.content_area, bg=colors["content_bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=10)

        left_panel = tk.Frame(body, bg=colors["content_bg"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        list_card = ModernCard(left_panel, colors, title="Available macOS Versions", padding=14)
        list_card.pack(fill=tk.BOTH, expand=True, pady=10)

        list_body = list_card.get_body()
        list_top = tk.Frame(list_body, bg=colors["card_bg"])
        list_top.pack(fill=tk.X, pady=10)
        self.fetch_btn = tk.Button(list_top, text="\u21bb FETCH CATALOGUE", command=self._on_fetch_clicked,
                                   font=("SF Pro Text", 10, "bold"),
                                   fg="white", bg=colors["accent"],
                                   activebackground="#0056b3",
                                   bd=0, padx=16, pady=7, cursor="hand2")
        self.fetch_btn.pack(side=tk.RIGHT)
        self.fetch_btn.bind('<Return>', lambda e: self._on_fetch_clicked())
        self.fetch_btn.bind('<KP_Enter>', lambda e: self._on_fetch_clicked())

        list_frame = tk.Frame(list_body, bg=colors["card_bg"])
        list_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(list_frame, bg=colors["card_bg"])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.version_listbox = tk.Listbox(
            list_frame,
            font=("SF Mono", 10),
            bg=colors["input_bg"], fg=colors["input_fg"],
            selectbackground=colors["accent"],
            selectforeground="#ffffff",
            yscrollcommand=scrollbar.set,
            bd=0, relief=tk.FLAT, height=7,
        )
        self.version_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.version_listbox.yview)
        self.version_listbox.insert(tk.END, "Click 'FETCH CATALOGUE' to load macOS versions")
        self.version_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        # -- Right panel: Download Engine --
        right_panel = tk.Frame(body, bg=colors["content_bg"], width=420)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_panel.pack_propagate(False)

        # Start Download Card - Unified toolbar: Index input + Download button
        index_card = ModernCard(right_panel, colors, title="Start Download", padding=16)
        index_card.pack(fill=tk.X, pady=10)
        index_body = index_card.get_body()

        toolbar = tk.Frame(index_body, bg=colors["card_bg"],
                           highlightbackground=colors["accent"],
                           highlightthickness=1)
        toolbar.pack(fill=tk.X)

        inner = tk.Frame(toolbar, bg=colors["card_bg"])
        inner.pack(fill=tk.X, expand=True)

        tk.Label(inner, text="Index:", font=("SF Pro Text", 10, "bold"),
                 fg=colors["muted"], bg=colors["card_bg"],
                 padx=10, pady=8).pack(side=tk.LEFT)

        self.index_entry = tk.Entry(
            inner,
            font=("SF Pro Text", 14),
            bg=colors["input_bg"], fg=colors["input_fg"],
            insertbackground=colors["accent"],
            bd=0, relief=tk.FLAT, width=5, justify="center",
        )
        self.index_entry.pack(side=tk.LEFT, ipady=6, fill=tk.Y, expand=True)
        self.index_entry.bind("<Return>", lambda e: self._on_download_clicked())
        self.index_entry.bind("<KeyRelease>", self._on_index_entry_keyrelease)
        self.root.after_idle(lambda: self.index_entry.focus_set())

        sep_v = tk.Frame(inner, bg=colors["accent"], width=1)
        sep_v.pack(side=tk.LEFT, fill=tk.Y, pady=4)

        self.download_btn = tk.Button(
            inner, text="\u2b07 DOWNLOAD",
            command=self._on_download_clicked,
            font=("SF Pro Text", 11, "bold"),
            fg="white", bg=colors["accent"],
            activebackground=colors["accent_hover"],
            bd=0, padx=20, cursor="hand2",
        )
        self.download_btn.pack(side=tk.RIGHT, ipady=9)
        self.download_btn.bind('<Return>', lambda e: self._on_download_clicked())
        self.download_btn.bind('<KP_Enter>', lambda e: self._on_download_clicked())

        self.index_error_label = tk.Label(index_body, text="", font=("SF Pro Text", 9),
                                          fg=colors["error"], bg=colors["card_bg"])
        self.index_error_label.pack(anchor=tk.W, pady=4)

        # MacLab Engine Card (with controls)
        engine_card = ModernCard(right_panel, colors, title="MacLab Download Engine", padding=16)
        engine_card.pack(fill=tk.X, pady=10)
        eng_body = engine_card.get_body()

        top_row = tk.Frame(eng_body, bg=colors["card_bg"])
        top_row.pack(fill=tk.X)
        self.dl_status = StatusBadge(top_row, colors, text="Ready", status="idle")
        self.dl_status.pack(side=tk.RIGHT)
        self.dl_filename = tk.Label(top_row, text="No active download", font=("SF Pro Text", 10, "bold"),
                                    fg=colors["text"], bg=colors["card_bg"], anchor="w")
        self.dl_filename.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.dl_progress = ModernProgressBar(eng_body, colors, height=10)
        self.dl_progress.pack(fill=tk.X, pady=10)

        pct_row = tk.Frame(eng_body, bg=colors["card_bg"])
        pct_row.pack(fill=tk.X)
        self.dl_percentage = tk.Label(pct_row, text="0%", font=("SF Pro Display", 20, "bold"),
                                      fg=colors["accent"], bg=colors["card_bg"])
        self.dl_percentage.pack(side=tk.LEFT, padx=14)

        self.dl_size = tk.Label(pct_row, text="Size: --", font=("SF Pro Text", 10),
                                fg=colors["text_secondary"], bg=colors["card_bg"])
        self.dl_size.pack(side=tk.LEFT, padx=8)
        self.dl_remaining = tk.Label(pct_row, text="Remaining: --", font=("SF Pro Text", 10),
                                     fg=colors["text_secondary"], bg=colors["card_bg"])
        self.dl_remaining.pack(side=tk.LEFT, padx=8)

        stats_row = tk.Frame(eng_body, bg=colors["card_bg"])
        stats_row.pack(fill=tk.X, pady=4)
        self.dl_speed = tk.Label(stats_row, text="Download: --", font=("SF Pro Text", 10),
                                 fg=colors["text"], bg=colors["card_bg"])
        self.dl_speed.pack(side=tk.LEFT, padx=8)
        self.dl_eta = tk.Label(stats_row, text="ETA: --", font=("SF Pro Text", 10),
                               fg=colors["text"], bg=colors["card_bg"])
        self.dl_eta.pack(side=tk.LEFT, padx=8)

        sep2 = tk.Frame(eng_body, bg=colors["border"], height=1)
        sep2.pack(fill=tk.X, pady=8)

        btn_row = tk.Frame(eng_body, bg=colors["card_bg"])
        btn_row.pack(fill=tk.X)
        for btn_data in [
            ("Pause", self._on_pause_download, colors["warning"], "dl_pause_btn"),
            ("Resume", self._on_resume_download, colors["accent"], "dl_resume_btn"),
            ("Cancel", self._on_cancel_download, colors["error"], "dl_cancel_btn"),
        ]:
            btn = tk.Button(btn_row, text=btn_data[0], command=btn_data[1],
                            font=("SF Pro Text", 10), fg="white", bg=btn_data[2],
                            activebackground=self.colors.get("btn_secondary_hover", "#d1d1d6"),
                            bd=0, padx=16, pady=6, cursor="hand2", state=tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
            btn.bind('<Return>', lambda e, c=btn_data[1]: c())
            btn.bind('<KP_Enter>', lambda e, c=btn_data[1]: c())
            setattr(self, btn_data[3], btn)

        # Debug Console Card
        debug_card = ModernCard(right_panel, colors, title="Developer Console", padding=8)
        debug_card.pack(fill=tk.BOTH, expand=True, pady=10)
        self._debug_console = DebugConsole(debug_card.get_body(), colors, height=120)
        self._debug_console.pack(fill=tk.BOTH, expand=True)
        self._debug_console.log("APP", "INFO", "Debug console ready")
        self._debug_console.log("APP", "SYSTEM", "Monitoring download activity...")

        # Console Card
        console_card = ModernCard(left_panel, colors, title="Console Output", padding=14)
        console_card.pack(fill=tk.X, pady=10)

        console_body = console_card.get_body()
        console_top = tk.Frame(console_body, bg=colors["card_bg"])
        console_top.pack(fill=tk.X, pady=6)
        tk.Button(console_top, text="Copy", command=self._on_copy_console,
                  font=("SF Pro Text", 10), fg=colors["text"], bg=colors["btn_secondary_bg"],
                  bd=1, relief=tk.FLAT, padx=12, pady=3, cursor="hand2").pack(side=tk.RIGHT, padx=3)
        tk.Button(console_top, text="Clear", command=self._on_clear_console,
                  font=("SF Pro Text", 10), fg=colors["text"], bg=colors["btn_secondary_bg"],
                  bd=1, relief=tk.FLAT, padx=12, pady=3, cursor="hand2").pack(side=tk.RIGHT, padx=3)

        console_frame = tk.Frame(console_body, bg=colors["console_bg"])
        console_frame._role = "console"
        console_frame.pack(fill=tk.BOTH, expand=True)
        self._console_raw = scrolledtext.ScrolledText(
            console_frame, wrap=tk.WORD,
            font=("SF Mono", 10),
            bg=colors["console_bg"], fg=colors["console_fg"],
            insertbackground="white", height=6,
            bd=0, relief=tk.FLAT,
        )
        self._console_raw.pack(fill=tk.BOTH, expand=True)
        self.console = SafeConsole(self._console_raw)
        tag_colors = [("info", "#51cf66"), ("error", "#ff6b6b"), ("warning", "#ffd43b"),
                      ("output", "#d4d4d4"), ("timestamp", "#888888"), ("success", "#00ff88"),
                      ("progress", "#0071e3")]
        for tag, clr in tag_colors:
            self._console_raw.tag_config(tag, foreground=clr)
        self.console.append("Console Ready", "info")
        self.console.append("Click FETCH CATALOGUE to load macOS versions", "output")

    # ---- Settings ----

    def show_settings(self):
        self.current_view = "settings"
        self._update_nav("settings")
        self.clear_content()

        from settings_ui import SettingsUI
        self.settings_ui = SettingsUI(self, self)
        self.settings_ui.create_settings_view(self.content_area)

        self.settings_download_dir = getattr(self.settings_ui, 'settings_download_dir', None)
        self.settings_catalog_var = getattr(self.settings_ui, 'settings_catalog_var', None)
        self.threads_var = getattr(self.settings_ui, 'threads_var', None)
        self.root.after(100, self._update_header_license_badge)

    # ---- Callbacks ----

    def set_callbacks(self, fetch_cb=None, download_cb=None, clear_cb=None, settings_cb=None,
                      pause_cb=None, resume_cb=None, cancel_cb=None, copy_cb=None,
                      clean_cb=None, clean_logs_cb=None, theme_toggle_cb=None, check_updates_cb=None):
        self._fetch_callback = fetch_cb
        self._download_callback = download_cb
        self._clear_callback = clear_cb
        self._settings_callback = settings_cb
        self._pause_callback = pause_cb
        self._resume_callback = resume_cb
        self._cancel_callback = cancel_cb
        self._copy_callback = copy_cb
        self._clean_callback = clean_cb
        self._clean_logs_callback = clean_logs_cb
        self._theme_toggle_callback = theme_toggle_cb
        self._check_updates_callback = check_updates_cb

    def _check_for_updates(self):
        if self._check_updates_callback:
            self._check_updates_callback()

    def _on_theme_toggle(self):
        if self._theme_toggle_callback:
            self._theme_toggle_callback()
        if hasattr(self, "_theme_toggle") and self._theme_toggle.winfo_exists():
            self._theme_toggle.set_theme(self.theme_mode == "dark")

    def set_fetch_state(self, loading):
        if hasattr(self, "fetch_btn") and self.fetch_btn.winfo_exists():
            if loading:
                self.fetch_btn.config(text="\u21bb FETCHING...", state=tk.DISABLED,
                                      bg=self.colors.get("muted", "#86868b"))
            else:
                self.fetch_btn.config(text="\u21bb FETCH CATALOGUE", state=tk.NORMAL,
                                      bg=self.colors.get("accent", "#0071e3"))

    def _on_listbox_select(self, event):
        selection = self.version_listbox.curselection()
        if selection:
            idx = selection[0] + 1
            self.index_entry.delete(0, tk.END)
            self.index_entry.insert(0, str(idx))

    def _on_index_entry_keyrelease(self, event):
        if not hasattr(self, 'version_listbox'):
            return
        text = self.index_entry.get().strip()
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < self.version_listbox.size():
                self.version_listbox.selection_clear(0, tk.END)
                self.version_listbox.selection_set(idx)
                self.version_listbox.activate(idx)
                self.version_listbox.see(idx)

    def _on_fetch_clicked(self):
        self.index_error_label.config(text="")
        self.set_fetch_state(True)
        if self._fetch_callback:
            self._fetch_callback()
    def _on_download_clicked(self):
        idx = self.index_entry.get().strip() if hasattr(self, "index_entry") else ""
        if not idx:
            self.index_error_label.config(text="Enter an index number")
            return
        if not idx.isdigit():
            self.index_error_label.config(text="Invalid number")
            return
        self.index_error_label.config(text="")
        if self._download_callback:
            self._download_callback()
    def _on_clear_console(self):
        if hasattr(self, "console"):
            self.console.clear()
        if self._clear_callback:
            self._clear_callback()
    def _on_copy_console(self):
        if hasattr(self, "_console_raw"):
            self.root.clipboard_clear()
            self.root.clipboard_append(self._console_raw.get(1.0, tk.END))
            if hasattr(self, "console"):
                self.console.append("Console content copied to clipboard", "info")
        if self._copy_callback:
            self._copy_callback()
    def _on_pause_download(self):
        if self._pause_callback:
            self._pause_callback()
    def _on_resume_download(self):
        if self._resume_callback:
            self._resume_callback()
    def _on_cancel_download(self):
        if self._cancel_callback:
            self._show_cancel_confirmation(self._cancel_callback)
    def _on_clean_temp(self):
        if self._clean_callback:
            self._clean_callback()
    def _on_clean_logs(self):
        if self._clean_logs_callback:
            self._clean_logs_callback()

    # ---- Debug Logging ----

    def debug_log(self, category, level, message, detail=None):
        if hasattr(self, "_debug_console") and self._debug_console and self._debug_console.winfo_exists():
            self._debug_console.log(category, level, message, detail)

    # ---- Download Progress ----

    def update_download_progress(self, percentage, downloaded, total, speed, eta, filename, status):
        def update():
            self.dl_progress.set_value(percentage)
            self.dl_percentage.config(text=f"{percentage:.1f}%")
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            self.dl_filename.config(text=display_name)

            if speed > 0:
                spd = speed
                for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
                    if spd < 1024:
                        self.dl_speed.config(text=f"Download: {spd:.1f} {unit}")
                        break
                    spd /= 1024
            else:
                self.dl_speed.config(text="Download: --")
            if eta > 0 and status != "completed":
                if eta >= 3600:
                    self.dl_eta.config(text=f"ETA: {eta/3600:.1f} hr")
                elif eta >= 60:
                    self.dl_eta.config(text=f"ETA: {eta/60:.1f} min")
                else:
                    self.dl_eta.config(text=f"ETA: {eta:.0f} sec")
            else:
                self.dl_eta.config(text="ETA: --")

            def fmt(b):
                if b <= 0:
                    return "0 B"
                for u in ["B", "KB", "MB", "GB", "TB"]:
                    if b < 1024.0:
                        return f"{b:.1f} {u}"
                    b /= 1024.0
                return f"{b:.1f} PB"
            self.dl_size.config(text=f"{fmt(downloaded)} / {fmt(total)}")
            remaining = max(0, total - downloaded)
            self.dl_remaining.config(text=f"Remaining: {fmt(remaining)}")

            if status == "downloading":
                self.dl_status.set_status("downloading", "Downloading")
                self.dl_pause_btn.config(state=tk.NORMAL)
                self.dl_resume_btn.config(state=tk.DISABLED)
                self.dl_cancel_btn.config(state=tk.NORMAL)
            elif status == "paused":
                self.dl_status.set_status("paused", "Paused")
                self.dl_pause_btn.config(state=tk.DISABLED)
                self.dl_resume_btn.config(state=tk.NORMAL)
                self.dl_cancel_btn.config(state=tk.NORMAL)
            elif status == "completed":
                self.dl_status.set_status("completed", "Completed")
                self.dl_pause_btn.config(state=tk.DISABLED)
                self.dl_resume_btn.config(state=tk.DISABLED)
                self.dl_cancel_btn.config(state=tk.DISABLED)
            elif status in ("network_error", "retrying"):
                self.dl_status.set_status("failed", status.replace("_", " ").title())
                self.dl_pause_btn.config(state=tk.DISABLED)
                self.dl_resume_btn.config(state=tk.DISABLED)
                self.dl_cancel_btn.config(state=tk.NORMAL)
            else:
                self.dl_status.set_status("idle", status.capitalize())
                self.dl_pause_btn.config(state=tk.DISABLED)
                self.dl_resume_btn.config(state=tk.DISABLED)
                self.dl_cancel_btn.config(state=tk.DISABLED)
        self.root.after(0, update)

    def update_stats(self, versions=None, downloads=None, active=None, storage=None):
        def upd():
            if hasattr(self, "_stats_labels"):
                if versions is not None and "versions" in self._stats_labels:
                    self._stats_labels["versions"].config(text=str(versions))
                if downloads is not None and "downloads" in self._stats_labels:
                    self._stats_labels["downloads"].config(text=str(downloads))
                if active is not None and "active" in self._stats_labels:
                    self._stats_labels["active"].config(text=str(active))
                if storage is not None and "storage" in self._stats_labels:
                    self._stats_labels["storage"].config(text=storage if " " in storage else f"{storage} GB")
        self.root.after(0, upd)

    def reset_download_ui(self):
        def reset():
            self.dl_progress.set_value(0, animate=False)
            self.dl_percentage.config(text="0%")
            self.dl_filename.config(text="No active download")
            self.dl_speed.config(text="Download: --")
            self.dl_eta.config(text="ETA: --")
            self.dl_size.config(text="Size: --")
            self.dl_remaining.config(text="Remaining: --")
            self.dl_status.set_status("idle", "Ready")
            self.dl_pause_btn.config(state=tk.DISABLED)
            self.dl_resume_btn.config(state=tk.DISABLED)
            self.dl_cancel_btn.config(state=tk.DISABLED)
        self.root.after(0, reset)
