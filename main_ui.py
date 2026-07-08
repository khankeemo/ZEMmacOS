import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import sys
import time
from PIL import Image, ImageTk, ImageDraw
from safe_console import SafeConsole
from modern_widgets import ModernCard, ModernButton, ModernProgressBar, AnimatedCounter, StatusBadge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class ZEMmacOSUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZEMmacOS")
        self.root.geometry("1260+820")
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

        self._init_light_colors()
        self.setup_styles()
        self.create_ui()
        self.load_logo()

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
        self.logo_image = None
        logo_path = os.path.join(BASE_DIR, "public", "images", "logo.png")
        try:
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((56, 56), Image.Resampling.LANCZOS)
                mask = Image.new("L", (56, 56), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 56, 56), fill=255)
                img.putalpha(mask)
                self.logo_image = ImageTk.PhotoImage(img)
                if hasattr(self, "logo_label"):
                    self.logo_label.config(image=self.logo_image)
            elif hasattr(self, "logo_label"):
                self.logo_label.config(text="Z", font=("SF Pro Display", 24, "bold"),
                                       fg=self.colors["accent"], bg=self.colors["sidebar_bg"])
        except Exception:
            pass

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
        logo_frame.pack(fill=tk.X, pady=(28, 6))
        self.logo_label = tk.Label(logo_frame, text="", bg=self.colors["sidebar_bg"])
        self.logo_label.pack()
        tk.Label(logo_frame, text="ZEMmacOS", font=("SF Pro Display", 18, "bold"),
                 fg=self.colors["text"], bg=self.colors["sidebar_bg"]).pack(pady=(4, 0))
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
            self._nav_buttons[key] = btn

        self._update_nav("dashboard")

        footer = tk.Frame(sidebar, bg=self.colors["sidebar_bg"])
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=16)
        tk.Label(footer, text="Version 3.0", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["sidebar_bg"]).pack()

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
        self.show_dashboard()

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

    # ---- Dashboard ----

    def show_dashboard(self):
        self.current_view = "dashboard"
        self._update_nav("dashboard")
        self.clear_content()

        colors = self.colors

        header = tk.Frame(self.content_area, bg=colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=(24, 4))
        tk.Label(header, text="Dashboard", font=("SF Pro Display", 26, "bold"),
                 fg=colors["text"], bg=colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(header, text="Overview of your macOS downloads and activities",
                 font=("SF Pro Text", 11), fg=colors["muted"],
                 bg=colors["header_bg"]).pack(anchor=tk.W, pady=(2, 0))

        scroll_canvas = tk.Canvas(self.content_area, bg=colors["content_bg"],
                                  highlightthickness=0, bd=0)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.content_area, orient="vertical", command=scroll_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_frame = tk.Frame(scroll_canvas, bg=colors["content_bg"])
        scroll_frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(e):
            scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        scroll_frame._cleanup_bind = lambda: scroll_canvas.unbind_all("<MouseWheel>")

        self._dashboard_scroll = scroll_canvas

        stats_row = tk.Frame(scroll_frame, bg=colors["content_bg"])
        stats_row.pack(fill=tk.X, padx=28, pady=(6, 0))

        stats_data = [
            ("30+", "Available Versions", colors["accent"]),
            ("0", "Downloads", colors["success"]),
            ("0", "Active Downloads", colors["warning"]),
            ("0 GB", "Storage Used", colors["muted"]),
        ]
        for i, (val, label, clr) in enumerate(stats_data):
            card = ModernCard(stats_row, colors, width=1, height=110, hover_raise=True, padding=0)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            stats_row.grid_columnconfigure(i, weight=1)
            body = card.get_body()
            AnimatedCounter(body, colors, font=("SF Pro Display", 28, "bold"),
                           fg=clr).pack(pady=(14, 0))
            tk.Label(body, text=label, font=("SF Pro Text", 10),
                     fg=colors["muted"], bg=colors["card_bg"]).pack()

        actions_card = ModernCard(scroll_frame, colors, title="Quick Actions", padding=18)
        actions_card.pack(fill=tk.X, padx=28, pady=(12, 0))

        act_frame = tk.Frame(actions_card.get_body(), bg=colors["card_bg"])
        act_frame.pack(fill=tk.X)
        modern_widgets_list = [
            ("Open Library", self.show_library, colors["accent"]),
            ("Clean Temp Files", self._on_clean_temp, colors["warning"]),
            ("Clean Old Logs", self._on_clean_logs, colors["error"]),
        ]
        for text, cmd, clr in modern_widgets_list:
            ModernButton(act_frame, text=text, command=cmd, colors=colors,
                        bg_color=clr, width=180, height=38, font_size=11, bold=True).pack(side=tk.LEFT, padx=5)

        history_card = ModernCard(scroll_frame, colors, title="Recent Activity", subtitle="Your latest download actions", padding=18)
        history_card.pack(fill=tk.X, padx=28, pady=(12, 0))
        tk.Label(history_card.get_body(), text="No recent activity yet. Start downloading macOS versions to see activity here.",
                 font=("SF Pro Text", 10), fg=colors["muted"], bg=colors["card_bg"]).pack(anchor=tk.W, pady=6)

        info_card = ModernCard(scroll_frame, colors, title="Getting Started", padding=18)
        info_card.pack(fill=tk.X, padx=28, pady=(12, 24))
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
                     fg=colors["text"], bg=colors["card_bg"]).pack(side=tk.LEFT, padx=(6, 0))

    # ---- Library ----

    def show_library(self):
        self.current_view = "library"
        self._update_nav("library")
        self.clear_content()

        colors = self.colors

        header = tk.Frame(self.content_area, bg=colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=(24, 4))
        tk.Label(header, text="Download Library", font=("SF Pro Display", 26, "bold"),
                 fg=colors["text"], bg=colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(header, text="Browse and download macOS installer versions",
                 font=("SF Pro Text", 11), fg=colors["muted"],
                 bg=colors["header_bg"]).pack(anchor=tk.W, pady=(2, 0))

        body = tk.Frame(self.content_area, bg=colors["content_bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=10)

        left_panel = tk.Frame(body, bg=colors["content_bg"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        list_card = ModernCard(left_panel, colors, title="Available macOS Versions", padding=14)
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        list_body = list_card.get_body()
        list_top = tk.Frame(list_body, bg=colors["card_bg"])
        list_top.pack(fill=tk.X, pady=(0, 10))
        self.fetch_btn = ModernButton(list_top, text="FETCH CATALOGUE", command=self._on_fetch_clicked,
                                     colors=colors, bg_color=colors["accent"], width=160, height=34,
                                     font_size=10, bold=True)
        self.fetch_btn.pack(side=tk.RIGHT)

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

        # -- Right panel: Download Engine --
        right_panel = tk.Frame(body, bg=colors["content_bg"], width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_panel.pack_propagate(False)

        # OS Index Input Card
        index_card = ModernCard(right_panel, colors, title="Start Download", padding=14)
        index_card.pack(fill=tk.X, pady=(0, 10))

        index_body = index_card.get_body()
        tk.Label(index_body, text="Enter macOS Index Number:",
                 font=("SF Pro Text", 11), fg=colors["text"],
                 bg=colors["card_bg"]).pack(anchor=tk.W)

        input_row = tk.Frame(index_body, bg=colors["card_bg"])
        input_row.pack(fill=tk.X, pady=(6, 0))
        self.index_entry = tk.Entry(
            input_row,
            font=("SF Pro Text", 14),
            bg=colors["input_bg"], fg=colors["input_fg"],
            insertbackground=colors["accent"],
            bd=1, relief=tk.FLAT, width=6, justify="center",
        )
        self.index_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.index_entry.bind("<Return>", lambda e: self._on_download_clicked())

        self.index_error_label = tk.Label(input_row, text="", font=("SF Pro Text", 9),
                                          fg=colors["error"], bg=colors["card_bg"])
        self.index_error_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.download_btn = ModernButton(index_body, text="DOWNLOAD SELECTED",
                                         command=self._on_download_clicked,
                                         colors=colors, bg_color=colors["success"],
                                         font_size=11, bold=True)
        self.download_btn.pack(fill=tk.X, pady=(10, 0))

        # MacLab Engine Card
        engine_card = ModernCard(right_panel, colors, title="MacLab Download Engine", padding=14)
        engine_card.pack(fill=tk.X, pady=(0, 10))

        eng_body = engine_card.get_body()
        eng_top = tk.Frame(eng_body, bg=colors["card_bg"])
        eng_top.pack(fill=tk.X, pady=(0, 4))
        self.dl_status = StatusBadge(eng_top, colors, text="Ready", status="idle")
        self.dl_status.pack(side=tk.RIGHT)

        self.dl_progress = ModernProgressBar(eng_body, colors, height=8, radius=4)
        self.dl_progress.pack(fill=tk.X, pady=6)

        info_row = tk.Frame(eng_body, bg=colors["card_bg"])
        info_row.pack(fill=tk.X, pady=4)
        self.dl_percentage = tk.Label(info_row, text="0%", font=("SF Pro Display", 16, "bold"),
                                      fg=colors["accent"], bg=colors["card_bg"])
        self.dl_percentage.pack(side=tk.LEFT, padx=(0, 10))
        self.dl_filename = tk.Label(info_row, text="No active download", font=("SF Pro Text", 10),
                                    fg=colors["muted"], bg=colors["card_bg"], anchor="w")
        self.dl_filename.pack(side=tk.LEFT, fill=tk.X, expand=True)

        stats_row = tk.Frame(eng_body, bg=colors["card_bg"])
        stats_row.pack(fill=tk.X, pady=2)
        self.dl_speed = tk.Label(stats_row, text="Speed: --", font=("SF Pro Text", 10),
                                 fg=colors["text"], bg=colors["card_bg"])
        self.dl_speed.pack(side=tk.LEFT, padx=6)
        self.dl_eta = tk.Label(stats_row, text="ETA: --", font=("SF Pro Text", 10),
                               fg=colors["text"], bg=colors["card_bg"])
        self.dl_eta.pack(side=tk.LEFT, padx=6)
        self.dl_size = tk.Label(stats_row, text="Size: --", font=("SF Pro Text", 10),
                                fg=colors["text"], bg=colors["card_bg"])
        self.dl_size.pack(side=tk.LEFT, padx=6)

        # Download Queue Card
        queue_card = ModernCard(right_panel, colors, title="Download Queue", padding=14)
        queue_card.pack(fill=tk.X, pady=(0, 10))

        queue_body = queue_card.get_body()
        btn_row = tk.Frame(queue_body, bg=colors["card_bg"])
        btn_row.pack(fill=tk.X, pady=4)
        self.dl_pause_btn = tk.Button(btn_row, text="Pause", command=self._on_pause_download,
                                      font=("SF Pro Text", 10), fg="white", bg=colors["warning"],
                                      bd=0, padx=14, pady=5, cursor="hand2", state=tk.DISABLED)
        self.dl_pause_btn.pack(side=tk.LEFT, padx=3)
        self.dl_resume_btn = tk.Button(btn_row, text="Resume", command=self._on_resume_download,
                                       font=("SF Pro Text", 10), fg="white", bg=colors["accent"],
                                       bd=0, padx=14, pady=5, cursor="hand2", state=tk.DISABLED)
        self.dl_resume_btn.pack(side=tk.LEFT, padx=3)
        self.dl_cancel_btn = tk.Button(btn_row, text="Cancel", command=self._on_cancel_download,
                                       font=("SF Pro Text", 10), fg="white", bg=colors["error"],
                                       bd=0, padx=14, pady=5, cursor="hand2", state=tk.DISABLED)
        self.dl_cancel_btn.pack(side=tk.LEFT, padx=3)

        # Console Card
        console_card = ModernCard(left_panel, colors, title="Console Output", padding=14)
        console_card.pack(fill=tk.X, pady=(0, 10))

        console_body = console_card.get_body()
        console_top = tk.Frame(console_body, bg=colors["card_bg"])
        console_top.pack(fill=tk.X, pady=(0, 6))
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

        self.settings_download_dir = self.settings_ui.settings_download_dir
        self.settings_catalog_var = self.settings_ui.settings_catalog_var
        self.threads_var = self.settings_ui.threads_var

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

    def _on_fetch_clicked(self):
        self.index_error_label.config(text="")
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
            self._cancel_callback()
    def _on_clean_temp(self):
        if self._clean_callback:
            self._clean_callback()
    def _on_clean_logs(self):
        if self._clean_logs_callback:
            self._clean_logs_callback()

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
                        self.dl_speed.config(text=f"{spd:.1f} {unit}")
                        break
                    spd /= 1024
            else:
                self.dl_speed.config(text="--")
            if eta > 0 and status != "completed":
                hours, minutes, secs = int(eta // 3600), int((eta % 3600) // 60), int(eta % 60)
                self.dl_eta.config(text=f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}")
            else:
                self.dl_eta.config(text="--")

            def fmt(b):
                if b <= 0:
                    return "0 B"
                for u in ["B", "KB", "MB", "GB", "TB"]:
                    if b < 1024.0:
                        return f"{b:.1f} {u}"
                    b /= 1024.0
                return f"{b:.1f} PB"
            self.dl_size.config(text=f"{fmt(downloaded)} / {fmt(total)}")

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
            else:
                self.dl_status.set_status("idle", status.capitalize())
                self.dl_pause_btn.config(state=tk.DISABLED)
                self.dl_resume_btn.config(state=tk.DISABLED)
                self.dl_cancel_btn.config(state=tk.DISABLED)
        self.root.after(0, update)

    def reset_download_ui(self):
        def reset():
            self.dl_progress.set_value(0, animate=False)
            self.dl_percentage.config(text="0%")
            self.dl_filename.config(text="No active download")
            self.dl_speed.config(text="Speed: --")
            self.dl_eta.config(text="ETA: --")
            self.dl_size.config(text="Size: --")
            self.dl_status.set_status("idle", "Ready")
            self.dl_pause_btn.config(state=tk.DISABLED)
            self.dl_resume_btn.config(state=tk.DISABLED)
            self.dl_cancel_btn.config(state=tk.DISABLED)
        self.root.after(0, reset)
