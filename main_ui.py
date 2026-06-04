# main_ui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
from PIL import Image, ImageTk, ImageDraw
from safe_console import SafeConsole

# Get base directory for dynamic imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "zem_license"))


class ZEMmacOSUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZEMmacOS")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Track current view
        self.current_view = "dashboard"
        
        # License service instance (will be set by main.py after init)
        self.license_service = None
        
        # Last known license badge state (cache for display only)
        self._cached_badge_text = "Checking..."
        self._cached_badge_color = "#86868b"
        
        # Default Colors (Overwritten by themes.py on startup)
        self.colors = {
            "root_bg":      "#f5f5f7", "sidebar_bg":   "#ffffff", "content_bg":   "#f5f5f7",
            "card_bg":      "#ffffff", "header_bg":    "#f5f5f7", "text":         "#1d1d1f",
            "muted":        "#86868b", "border":       "#e0e0e0", "input_bg":     "#ffffff",
            "input_fg":     "#1d1d1f", "console_bg":   "#1e1e1e", "console_fg":   "#d4d4d4",
            "accent":       "#0071e3", "accent_hover": "#005bbf", "success":      "#34c759",
            "warning":      "#ff9f0a", "error":        "#ff3b30", "btn_primary_fg":   "#ffffff",
            "btn_secondary_fg": "#1d1d1f", "btn_secondary_bg": "#e5e5ea"
        }
        
        # Callbacks
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
        self._license_upgrade_callback = None
        self._theme_toggle_callback = None
        self._check_updates_callback = None
        
        self.setup_styles()
        self.create_ui()
        self.load_logo()

    def set_license_service(self, service):
        """Set license service instance (called by main.py after init)"""
        self.license_service = service
        if hasattr(self, "console") and self.console and hasattr(service, "attach_console"):
            service.attach_console(self.console)
        self.update_license_badge()

    def setup_styles(self):
        style = ttk.Style()
        style.configure("Toggle.TButton", font=("SF Pro Text", 11))
        style.configure("Accent.TButton", font=("SF Pro Text", 11, "bold"))
        
        # Configure notebook tabs for better visibility
        style.configure("TNotebook", background=self.colors["content_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", 
                       padding=[12, 8],
                       font=("SF Pro Text", 11),
                       background=self.colors["card_bg"],
                       foreground=self.colors["text"])
        style.map("TNotebook.Tab",
                 background=[("selected", self.colors["accent"])],
                 foreground=[("selected", "#ffffff")],
                 expand=[("selected", [1, 1, 1, 0])])

    def load_logo(self):
        self.logo_image = None
        logo_path = os.path.join(BASE_DIR, "public", "images", "logo.png")
        try:
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((80, 80), Image.Resampling.LANCZOS)
                mask = Image.new('L', (80, 80), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 80, 80), fill=255)
                img.putalpha(mask)
                self.logo_image = ImageTk.PhotoImage(img)
                if hasattr(self, 'logo_label'):
                    self.logo_label.config(image=self.logo_image)
            elif hasattr(self, 'logo_label'):
                self.logo_label.config(text="Z", font=("SF Pro Display", 32, "bold"), fg=self.colors["accent"], bg=self.colors["sidebar_bg"])
        except Exception as e:
            print(f"Logo load error: {e}")

    def create_ui(self):
        main_container = tk.Frame(self.root, bg=self.colors["root_bg"])
        main_container.pack(fill=tk.BOTH, expand=True)
        self.create_sidebar(main_container)
        self.create_content_area(main_container)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.colors["sidebar_bg"], width=260)
        sidebar._role = 'sidebar'
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self.sidebar_frame = sidebar
        
        logo_frame = tk.Frame(sidebar, bg=self.colors["sidebar_bg"])
        logo_frame.pack(fill=tk.X, pady=(30, 10))
        self.logo_label = tk.Label(logo_frame, text="  ", bg=self.colors["sidebar_bg"])
        self.logo_label.pack()
        
        tk.Label(logo_frame, text="ZEMmacOS", font=("SF Pro Display", 22, "bold"), fg=self.colors["text"], bg=self.colors["sidebar_bg"]).pack(pady=(10, 0))
        tk.Label(logo_frame, text="macOS Download Manager", font=("SF Pro Text", 10), fg=self.colors["muted"], bg=self.colors["sidebar_bg"]).pack()
        
        nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("📚 Library", self.show_library),
            ("💽 Prepare macOS Installer", self.open_installer_tools),
            ("⚙️ Settings", self.show_settings)
        ]
        for text, command in nav_buttons:
            btn = tk.Button(sidebar, text=text, command=command, font=("SF Pro Text", 12), fg=self.colors["text"], bg=self.colors["sidebar_bg"], activebackground="#f0f0f0", bd=0, anchor="w", padx=20, pady=12, cursor="hand2")
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#f0f0f0"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors["sidebar_bg"]))
        
        footer = tk.Frame(sidebar, bg=self.colors["sidebar_bg"])
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        tk.Label(footer, text="Version 3.0", font=("SF Pro Text", 9), fg=self.colors["muted"], bg=self.colors["sidebar_bg"]).pack()

    def create_content_area(self, parent):
        self.content_area = tk.Frame(parent, bg=self.colors["content_bg"])
        self.content_area._role = 'content'
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.show_dashboard()

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def create_card(self, parent, title=None, height=None):
        card = tk.Frame(parent, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1)
        card._role = 'card'
        if title:
            title_bar = tk.Frame(card, bg=self.colors["card_bg"], height=45)
            title_bar.pack(fill=tk.X, padx=20, pady=(12, 0))
            title_bar.pack_propagate(False)
            tk.Label(title_bar, text=title, font=("SF Pro Text", 13, "bold"), fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)
        if height:
            card.pack_propagate(False)
            card.config(height=height)
        return card

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.clear_content()
        
        header = tk.Frame(self.content_area, bg=self.colors["header_bg"])
        header._role = 'header'
        header.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        left_frame = tk.Frame(header, bg=self.colors["header_bg"])
        left_frame.pack(side=tk.LEFT, anchor=tk.W)
        
        tk.Label(left_frame, text="Welcome to ZEMmacOS", font=("SF Pro Display", 24, "bold"), fg=self.colors["text"], bg=self.colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(left_frame, text="Download macOS installers directly from Apple", font=("SF Pro Text", 12), fg=self.colors["muted"], bg=self.colors["header_bg"]).pack(anchor=tk.W, pady=(5, 0))
        
        right_frame = tk.Frame(header, bg=self.colors["header_bg"])
        right_frame.pack(side=tk.RIGHT, anchor=tk.N)
        
        # Refresh button for manual badge update
        self.refresh_badge_btn = tk.Button(
            right_frame,
            text="⟳",
            command=self.force_refresh_license_badge,
            font=("SF Pro Text", 10, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=8,
            pady=6,
            cursor="hand2"
        )
        self.refresh_badge_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        self.license_badge_label = tk.Label(
            right_frame,
            text=self._cached_badge_text,
            font=("SF Pro Text", 10, "bold"),
            fg=self._cached_badge_color,
            bg=self.colors["card_bg"],
            padx=12,
            pady=6,
            relief=tk.FLAT,
            bd=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        self.license_badge_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Set theme toggle button text based on current theme
        theme_text = "🌙 Switch to Dark" if getattr(self, 'theme_mode', 'light') == "light" else "☀️ Switch to Light"
        self.theme_toggle_btn = tk.Button(
            right_frame,
            text=theme_text,
            command=self._on_theme_toggle,
            font=("SF Pro Text", 10, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            activebackground=self.colors["border"],
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )
        self.theme_toggle_btn.pack(side=tk.RIGHT)
        
        stats_frame = tk.Frame(self.content_area, bg=self.colors["content_bg"])
        stats_frame.pack(fill=tk.X, padx=30, pady=20)
        stats = [("🍎 macOS Versions", "30+", self.colors["accent"]), ("⬇️ Downloads", "0", self.colors["warning"])]
        for i, (title_text, value, color) in enumerate(stats):
            card = tk.Frame(stats_frame, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1, height=100)
            card._role = 'card'
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            card.pack_propagate(False)
            tk.Label(card, text=title_text, font=("SF Pro Text", 11), fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(pady=(15, 5))
            tk.Label(card, text=value, font=("SF Pro Display", 28, "bold"), fg=color, bg=self.colors["card_bg"]).pack(pady=(0, 15))
        
        actions_card = self.create_card(self.content_area, "Quick Actions")
        actions_card.pack(fill=tk.X, padx=30, pady=(0, 20))
        actions_frame = tk.Frame(actions_card, bg=self.colors["card_bg"])
        actions_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(actions_frame, text="📚 Open Library", command=self.show_library, font=("SF Pro Text", 12, "bold"), fg="white", bg=self.colors["accent"], activebackground=self.colors["accent_hover"], bd=0, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="💽 Prepare macOS Installer", command=self.open_installer_tools, font=("SF Pro Text", 12, "bold"), fg="white", bg=self.colors["success"], activebackground="#2e8b57", bd=0, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="🧹 Clean Temp Files", command=self._on_clean_temp, font=("SF Pro Text", 12, "bold"), fg="white", bg=self.colors["warning"], activebackground="#e08e00", bd=0, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="🗑️ Clean Old Logs", command=self._on_clean_logs, font=("SF Pro Text", 12, "bold"), fg="white", bg=self.colors["error"], activebackground="#cc2a1f", bd=0, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        info_card = self.create_card(self.content_area)
        info_card.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))
        info_frame = tk.Frame(info_card, bg=self.colors["card_bg"])
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        info_text = tk.Text(info_frame, font=("SF Pro Text", 11), bg=self.colors["card_bg"], fg=self.colors["text"], wrap=tk.WORD, bd=0, height=8)
        info_text.pack(fill=tk.BOTH, expand=True)
        info_text.insert(tk.END, "Getting Started:\n\n", "bold")
        info_text.insert(tk.END, "1. Click 'Library' in the sidebar\n")
        info_text.insert(tk.END, "2. Click 'FETCH CATALOGUE' to see available macOS versions\n")
        info_text.insert(tk.END, "3. Enter the number and click 'DOWNLOAD SELECTED'\n")
        info_text.insert(tk.END, "4. After download, click 'Prepare macOS Installer' to validate files.\n\n")
        info_text.insert(tk.END, "Downloads use the MacLab download engine with pause/resume support.")
        info_text.tag_config("bold", font=("SF Pro Text", 11, "bold"))
        info_text.config(state=tk.DISABLED)
        
        # Update badge after dashboard is created
        self.update_license_badge()

    def update_license_badge(self):
        """
        Public method to update badge using LicenseService.
        Called after startup and after any license changes.
        """
        # Ensure we have fresh service instance
        from zem_license.license_service import get_license_service, reload_license_service
        
        if self.license_service is None:
            # License service not set yet - try to get fresh instance
            try:
                self.license_service = get_license_service()
            except:
                if hasattr(self, 'license_badge_label') and self.license_badge_label.winfo_exists():
                    self.license_badge_label.config(text="Checking...", fg=self.colors["muted"])
                return
        
        try:
            # Reload to ensure fresh state
            reload_license_service()
            self.license_service = get_license_service()
            
            # Use dedicated badge info method from license service
            badge_info = self.license_service.get_badge_info()
            badge_text = badge_info.get("text", "✗ License Required")
            color_key = badge_info.get("color_key", "error")
            
            color_map = {
                "success": self.colors["success"],
                "warning": self.colors["warning"],
                "error": self.colors["error"]
            }
            badge_color = color_map.get(color_key, self.colors["error"])
            
            self._cached_badge_text = badge_text
            self._cached_badge_color = badge_color
            
            if hasattr(self, 'license_badge_label') and self.license_badge_label.winfo_exists():
                self.license_badge_label.config(text=badge_text, fg=badge_color)
                
        except Exception as e:
            print(f"Badge update error: {e}")
            if hasattr(self, 'license_badge_label') and self.license_badge_label.winfo_exists():
                self.license_badge_label.config(text="⚠️ License Error", fg=self.colors["error"])

    def force_refresh_license_badge(self):
        """
        Force refresh badge from the source.
        Called by manual refresh button.
        """
        from zem_license.license_service import get_license_service, reload_license_service
        
        # Update badge with "Refreshing..." state
        if hasattr(self, 'license_badge_label') and self.license_badge_label.winfo_exists():
            self.license_badge_label.config(text="⟳ Refreshing...", fg=self.colors["accent"])
            self.root.update_idletasks()
        
        # Reload license service to clear cache
        reload_license_service()
        
        # Get fresh service instance
        self.license_service = get_license_service()
        
        # Update badge with fresh result
        self.update_license_badge()
        
        # Show result message
        status = self.license_service.check_license()
        if status.get("is_valid"):
            if status.get("license_type") == "paid":
                days = status.get("days_left", 0)
                messagebox.showinfo("License Status", f"License valid.\n\n{days} days remaining.")
            else:
                days = status.get("days_left", 0)
                messagebox.showinfo("License Status", f"Trial mode active.\n\n{days} days remaining.")
        else:
            error = status.get("message", "No valid license found")
            messagebox.showinfo("License Status", f"No valid license found.\n\n{error}")

    def show_library(self):
        self.current_view = "library"
        self.clear_content()
        
        header = tk.Frame(self.content_area, bg=self.colors["header_bg"])
        header._role = 'header'
        header.pack(fill=tk.X, padx=30, pady=(20, 10))
        tk.Label(header, text="Download Library", font=("SF Pro Display", 24, "bold"), fg=self.colors["text"], bg=self.colors["header_bg"]).pack(anchor=tk.W)
        
        main_frame = tk.Frame(self.content_area, bg=self.colors["content_bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        list_card = tk.Frame(main_frame, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1)
        list_card._role = 'card'
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        list_header = tk.Frame(list_card, bg=self.colors["card_bg"], height=50)
        list_header.pack(fill=tk.X, padx=20, pady=(12, 0))
        list_header.pack_propagate(False)
        tk.Label(list_header, text="Available macOS Versions", font=("SF Pro Text", 14, "bold"), fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)
        self.fetch_btn = tk.Button(list_header, text="📋 FETCH CATALOGUE", command=self._on_fetch_clicked, font=("SF Pro Text", 11, "bold"), fg="white", bg=self.colors["accent"], activebackground=self.colors["accent_hover"], bd=0, padx=20, pady=8, cursor="hand2")
        self.fetch_btn.pack(side=tk.RIGHT)
        
        list_frame = tk.Frame(list_card, bg=self.colors["card_bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        scrollbar = tk.Scrollbar(list_frame, bg=self.colors["card_bg"])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.version_listbox = tk.Listbox(list_frame, font=("SF Mono", 10), bg=self.colors["console_bg"], fg=self.colors["console_fg"], selectbackground=self.colors["accent"], yscrollcommand=scrollbar.set, bd=0, relief=tk.FLAT, height=10)
        self.version_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.version_listbox.yview)
        self.version_listbox.insert(tk.END, "Click 'FETCH CATALOGUE' to load macOS versions")
        
        download_control_card = tk.Frame(main_frame, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1)
        download_control_card._role = 'card'
        download_control_card.pack(fill=tk.X, pady=(0, 15))
        download_control_frame = tk.Frame(download_control_card, bg=self.colors["card_bg"])
        download_control_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(download_control_frame, text="Enter Index Number:", font=("SF Pro Text", 12), fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT, padx=(0, 10))
        self.index_entry = tk.Entry(download_control_frame, font=("SF Pro Text", 12), bg=self.colors["input_bg"], fg=self.colors["input_fg"], insertbackground=self.colors["accent"], bd=1, relief=tk.FLAT, highlightthickness=1, highlightcolor=self.colors["accent"], highlightbackground=self.colors["border"], width=10)
        self.index_entry.pack(side=tk.LEFT, padx=(0, 20))
        self.index_entry.bind('<Return>', lambda event: self._on_download_clicked())
        
        self.download_btn = tk.Button(download_control_frame, text="⬇️ DOWNLOAD SELECTED", command=self._on_download_clicked, font=("SF Pro Text", 12, "bold"), fg="white", bg=self.colors["success"], activebackground="#2e8b57", bd=0, padx=30, pady=10, cursor="hand2")
        self.download_btn.pack(side=tk.RIGHT)
        
        maclab_card = tk.Frame(main_frame, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1)
        maclab_card._role = 'card'
        maclab_card.pack(fill=tk.X, pady=(0, 15))
        maclab_header = tk.Frame(maclab_card, bg=self.colors["card_bg"], height=40)
        maclab_header.pack(fill=tk.X, padx=20, pady=(10, 0))
        maclab_header.pack_propagate(False)
        tk.Label(maclab_header, text="🧪 MacLab Download Engine", font=("SF Pro Text", 13, "bold"), fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)
        self.dl_status = tk.Label(maclab_header, text="Ready", font=("SF Pro Text", 10), fg=self.colors["muted"], bg=self.colors["card_bg"])
        self.dl_status.pack(side=tk.RIGHT)
        
        maclab_frame = tk.Frame(maclab_card, bg=self.colors["card_bg"])
        maclab_frame.pack(fill=tk.X, padx=20, pady=15)
        self.dl_progress = ttk.Progressbar(maclab_frame, mode='determinate', length=400)
        self.dl_progress.pack(fill=tk.X, pady=5)
        
        info_row = tk.Frame(maclab_frame, bg=self.colors["card_bg"])
        info_row.pack(fill=tk.X, pady=5)
        self.dl_percentage = tk.Label(info_row, text="0%", font=("SF Pro Display", 18, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"])
        self.dl_percentage.pack(side=tk.LEFT, padx=(0, 20))
        self.dl_filename = tk.Label(info_row, text="No active download", font=("SF Pro Text", 10), fg=self.colors["muted"], bg=self.colors["card_bg"], anchor="w")
        self.dl_filename.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        stats_row = tk.Frame(maclab_frame, bg=self.colors["card_bg"])
        stats_row.pack(fill=tk.X, pady=5)
        self.dl_speed = tk.Label(stats_row, text="Speed: --", font=("SF Pro Text", 10), fg=self.colors["text"], bg=self.colors["card_bg"])
        self.dl_speed.pack(side=tk.LEFT, padx=10)
        self.dl_eta = tk.Label(stats_row, text="ETA: --", font=("SF Pro Text", 10), fg=self.colors["text"], bg=self.colors["card_bg"])
        self.dl_eta.pack(side=tk.LEFT, padx=10)
        self.dl_size = tk.Label(stats_row, text="Size: --", font=("SF Pro Text", 10), fg=self.colors["text"], bg=self.colors["card_bg"])
        self.dl_size.pack(side=tk.LEFT, padx=10)
        
        btn_row = tk.Frame(maclab_frame, bg=self.colors["card_bg"])
        btn_row.pack(fill=tk.X, pady=10)
        self.dl_pause_btn = tk.Button(btn_row, text="⏸️ Pause", command=self._on_pause_download, font=("SF Pro Text", 10), fg="white", bg=self.colors["warning"], bd=0, padx=15, pady=6, cursor="hand2", state=tk.DISABLED)
        self.dl_pause_btn.pack(side=tk.LEFT, padx=5)
        self.dl_resume_btn = tk.Button(btn_row, text="▶️ Resume", command=self._on_resume_download, font=("SF Pro Text", 10), fg="white", bg=self.colors["accent"], bd=0, padx=15, pady=6, cursor="hand2", state=tk.DISABLED)
        self.dl_resume_btn.pack(side=tk.LEFT, padx=5)
        self.dl_cancel_btn = tk.Button(btn_row, text="❌ Cancel", command=self._on_cancel_download, font=("SF Pro Text", 10), fg="white", bg=self.colors["error"], bd=0, padx=15, pady=6, cursor="hand2", state=tk.DISABLED)
        self.dl_cancel_btn.pack(side=tk.LEFT, padx=5)
        
        console_card = tk.Frame(main_frame, bg=self.colors["card_bg"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["border"], highlightthickness=1)
        console_card._role = 'card'
        console_card.pack(fill=tk.BOTH, expand=True)
        console_header = tk.Frame(console_card, bg=self.colors["card_bg"], height=40)
        console_header.pack(fill=tk.X, padx=20, pady=(10, 0))
        console_header.pack_propagate(False)
        tk.Label(console_header, text="Console Output", font=("SF Pro Text", 13, "bold"), fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)
        tk.Button(console_header, text="📋 Copy Console", command=self._on_copy_console, font=("SF Pro Text", 10), fg=self.colors["text"], bg=self.colors["btn_secondary_bg"], bd=1, relief=tk.FLAT, padx=15, pady=5, cursor="hand2").pack(side=tk.RIGHT, padx=5)
        tk.Button(console_header, text="🗑️ Clear Console", command=self._on_clear_console, font=("SF Pro Text", 10), fg=self.colors["text"], bg=self.colors["btn_secondary_bg"], bd=1, relief=tk.FLAT, padx=15, pady=5, cursor="hand2").pack(side=tk.RIGHT, padx=5)
        
        console_frame = tk.Frame(console_card, bg=self.colors["console_bg"])
        console_frame._role = 'console'
        console_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        self._console_raw = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, font=("SF Mono", 10), bg=self.colors["console_bg"], fg=self.colors["console_fg"], insertbackground="white", height=10, bd=0, relief=tk.FLAT)
        self._console_raw.pack(fill=tk.BOTH, expand=True)
        self.console = SafeConsole(self._console_raw)
        self._console_raw.tag_config("info", foreground="#51cf66")
        self._console_raw.tag_config("error", foreground="#ff6b6b")
        self._console_raw.tag_config("warning", foreground="#ffd43b")
        self._console_raw.tag_config("output", foreground="#d4d4d4")
        self._console_raw.tag_config("timestamp", foreground="#888888")
        self._console_raw.tag_config("success", foreground="#00ff88")
        self._console_raw.tag_config("progress", foreground="#0071e3")
        self.console.append("Console Ready", "info")
        self.console.append("Click FETCH CATALOGUE to load macOS versions", "output")

    def show_settings(self):
        self.current_view = "settings"
        self.clear_content()
        
        from settings_ui import SettingsUI
        self.settings_ui = SettingsUI(self, self)
        self.settings_ui.create_settings_view(self.content_area)
        
        # Bind references for main.py compatibility
        self.settings_download_dir = self.settings_ui.settings_download_dir
        self.settings_catalog_var = self.settings_ui.settings_catalog_var
        self.threads_var = self.settings_ui.threads_var

    def _check_for_updates(self):
        if self._check_updates_callback:
            self._check_updates_callback()

    def _save_settings(self):
        if self._settings_callback:
            self._settings_callback()

    def _on_theme_toggle(self):
        if self._theme_toggle_callback:
            self._theme_toggle_callback()
        # Update theme button text in dashboard (if visible)
        if hasattr(self, 'theme_toggle_btn') and self.theme_toggle_btn.winfo_exists():
            new_text = "🌙 Switch to Dark" if getattr(self, 'theme_mode', 'light') == "light" else "☀️ Switch to Light"
            self.theme_toggle_btn.config(text=new_text)

    def _on_fetch_clicked(self):
        if self._fetch_callback: self._fetch_callback()
    def _on_download_clicked(self):
        if self._download_callback: self._download_callback()
    def _on_clear_console(self):
        if hasattr(self, 'console'): self.console.clear()
        if self._clear_callback: self._clear_callback()
    def _on_copy_console(self):
        if hasattr(self, '_console_raw'):
            self.root.clipboard_clear()
            self.root.clipboard_append(self._console_raw.get(1.0, tk.END))
            if hasattr(self, 'console'): self.console.append("Console content copied to clipboard", "info")
        if self._copy_callback: self._copy_callback()
    def _on_pause_download(self):
        if self._pause_callback: self._pause_callback()
    def _on_resume_download(self):
        if self._resume_callback: self._resume_callback()
    def _on_cancel_download(self):
        if self._cancel_callback: self._cancel_callback()
    def _on_clean_temp(self):
        if self._clean_callback: self._clean_callback()
    def _on_clean_logs(self):
        if self._clean_logs_callback: self._clean_logs_callback()

    def open_installer_tools(self):
        try:
            import usb_creator_ui
            if hasattr(usb_creator_ui, 'run_as_modal'):
                usb_creator_ui.run_as_modal(self.root)
            else:
                app = usb_creator_ui.USBCreatorUI()
                app.run()
        except ImportError as e:
            messagebox.showerror("Module Not Found", f"Installer Tools module is missing.\n\nError: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Installer Tools:\n{str(e)}")

    def set_callbacks(self, fetch_cb, download_cb, clear_cb, settings_cb=None, pause_cb=None, resume_cb=None, cancel_cb=None, copy_cb=None, clean_cb=None, clean_logs_cb=None, license_upgrade_cb=None, theme_toggle_cb=None, check_updates_cb=None):
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
        self._license_upgrade_callback = license_upgrade_cb
        self._theme_toggle_callback = theme_toggle_cb
        self._check_updates_callback = check_updates_cb

    def update_download_progress(self, percentage, downloaded, total, speed, eta, filename, status):
        def update():
            self.dl_progress['value'] = percentage
            self.dl_percentage.config(text=f"{percentage:.1f}%")
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            self.dl_filename.config(text=display_name)
            if speed > 0:
                spd = speed
                for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
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
            def format_size(b):
                if b <= 0: return "0 B"
                for u in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if b < 1024.0: return f"{b:.1f} {u}"
                    b /= 1024.0
                return f"{b:.1f} PB"
            self.dl_size.config(text=f"{format_size(downloaded)} / {format_size(total)}")
            if status == "downloading":
                self.dl_status.config(text="Downloading...", fg=self.colors["accent"])
                self.dl_pause_btn.config(state=tk.NORMAL); self.dl_resume_btn.config(state=tk.DISABLED); self.dl_cancel_btn.config(state=tk.NORMAL)
            elif status == "paused":
                self.dl_status.config(text="Paused", fg=self.colors["warning"])
                self.dl_pause_btn.config(state=tk.DISABLED); self.dl_resume_btn.config(state=tk.NORMAL); self.dl_cancel_btn.config(state=tk.NORMAL)
            elif status == "completed":
                self.dl_status.config(text="Completed", fg=self.colors["success"])
                self.dl_pause_btn.config(state=tk.DISABLED); self.dl_resume_btn.config(state=tk.DISABLED); self.dl_cancel_btn.config(state=tk.DISABLED)
            else:
                self.dl_status.config(text=status.capitalize(), fg=self.colors["muted"])
        self.root.after(0, update)

    def reset_download_ui(self):
        """Reset download UI elements to initial state"""
        def reset():
            self.dl_progress['value'] = 0
            self.dl_percentage.config(text="0%")
            self.dl_filename.config(text="No active download")
            self.dl_speed.config(text="Speed: --")
            self.dl_eta.config(text="ETA: --")
            self.dl_size.config(text="Size: --")
            self.dl_status.config(text="Ready", fg=self.colors["muted"])
            self.dl_pause_btn.config(state=tk.DISABLED)
            self.dl_resume_btn.config(state=tk.DISABLED)
            self.dl_cancel_btn.config(state=tk.DISABLED)
        self.root.after(0, reset)