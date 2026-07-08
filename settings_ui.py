# settings_ui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import urllib.error
import urllib.request

# Get base directory for dynamic imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SettingsUI:
    """Settings UI component embedded in main content area"""

    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.colors = app_instance.colors
        self._current_modal = None

    def create_settings_view(self, container):
        """Create the complete settings view"""
        self.container = container

        header = tk.Frame(container, bg=self.colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=(20, 10))
        tk.Label(
            header,
            text="Settings",
            font=("SF Pro Display", 24, "bold"),
            fg=self.colors["text"],
            bg=self.colors["header_bg"],
        ).pack(anchor=tk.W)

        settings_card = self._create_card(container, "Application Settings")
        settings_card.pack(fill=tk.X, padx=30, pady=20)
        content_frame = tk.Frame(settings_card, bg=self.colors["card_bg"])
        content_frame.pack(fill=tk.X, padx=25, pady=25)

        # Download Directory
        tk.Label(
            content_frame,
            text="Download Directory:",
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card_bg"],
        ).pack(anchor=tk.W)

        dir_frame = tk.Frame(content_frame, bg=self.colors["card_bg"])
        dir_frame.pack(fill=tk.X, pady=5)
        self.settings_download_dir = tk.Entry(
            dir_frame,
            font=("SF Pro Text", 11),
            bg=self.colors["input_bg"],
            fg=self.colors["input_fg"],
            insertbackground=self.colors["accent"],
            bd=1,
            relief=tk.FLAT,
        )
        self.settings_download_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Button(
            dir_frame,
            text="Browse",
            command=self._browse_download_dir,
            font=("SF Pro Text", 10),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        # Catalog Selection
        tk.Label(
            content_frame,
            text="Apple Catalog:",
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card_bg"],
        ).pack(anchor=tk.W, pady=(15, 5))
        self.settings_catalog_var = tk.StringVar(value="publicrelease")
        ttk.Combobox(
            content_frame,
            textvariable=self.settings_catalog_var,
            values=["publicrelease", "public", "customer", "developer"],
            state="readonly",
            font=("SF Pro Text", 11),
        ).pack(fill=tk.X)

        # Download Threads
        tk.Label(
            content_frame,
            text="MacLab Download Settings:",
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card_bg"],
        ).pack(anchor=tk.W, pady=(15, 5))
        threads_frame = tk.Frame(content_frame, bg=self.colors["card_bg"])
        threads_frame.pack(fill=tk.X)
        tk.Label(
            threads_frame,
            text="Download Threads:",
            font=("SF Pro Text", 10),
            fg=self.colors["text"],
            bg=self.colors["card_bg"],
        ).pack(side=tk.LEFT, padx=(0, 10))
        self.threads_var = tk.StringVar(value="8")
        ttk.Combobox(
            threads_frame,
            textvariable=self.threads_var,
            values=["4", "8", "16", "32"],
            state="readonly",
            font=("SF Pro Text", 10),
            width=5,
        ).pack(side=tk.LEFT)
        tk.Label(
            content_frame,
            text="More threads = faster downloads, but more server load",
            font=("SF Pro Text", 8),
            fg=self.colors["muted"],
            bg=self.colors["card_bg"],
        ).pack(anchor=tk.W, pady=(5, 0))

        # Premium Features
        premium_frame = tk.LabelFrame(
            content_frame,
            text="Premium Features",
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card_bg"],
            bd=1,
            relief=tk.RIDGE,
        )
        premium_frame.pack(fill=tk.X, pady=(20, 0))

        premium_inner = tk.Frame(premium_frame, bg=self.colors["card_bg"])
        premium_inner.pack(fill=tk.X, padx=15, pady=15)

        # Three buttons row - same size and style
        buttons_row = tk.Frame(premium_inner, bg=self.colors["card_bg"])
        buttons_row.pack(fill=tk.X, pady=5)

        # Theme Button
        theme_text = (
            "🌙 Switch to Dark"
            if getattr(self.app, "theme_mode", "light") == "light"
            else "☀️ Switch to Light"
        )
        self.theme_btn = tk.Button(
            buttons_row,
            text=theme_text,
            command=self._on_theme_toggle,
            font=("SF Pro Text", 10, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
            width=18,
            height=1,
        )
        self.theme_btn.pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)

        # License Button
        self.license_btn = tk.Button(
            buttons_row,
            text="Manage License",
            command=self._open_license_modal,
            font=("SF Pro Text", 10, "bold"),
            fg="white",
            bg=self.colors["accent"],
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            width=18,
            height=1,
        )
        self.license_btn.pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)

        # Update Button
        self.update_btn = tk.Button(
            buttons_row,
            text="Check Updates",
            command=self._check_for_updates,
            font=("SF Pro Text", 10, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
            width=18,
            height=1,
        )
        self.update_btn.pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)

        # Save Button
        tk.Button(
            content_frame,
            text="💾 Save Settings",
            command=self._save_settings,
            font=("SF Pro Text", 12, "bold"),
            fg="white",
            bg=self.colors["success"],
            activebackground="#2e8b57",
            bd=0,
            padx=20,
            pady=12,
            cursor="hand2",
        ).pack(pady=(20, 0))

    def _create_card(self, parent, title=None):
        card = tk.Frame(
            parent,
            bg=self.colors["card_bg"],
            relief=tk.RIDGE,
            bd=0,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        card._role = "card"
        if title:
            title_bar = tk.Frame(card, bg=self.colors["card_bg"], height=45)
            title_bar.pack(fill=tk.X, padx=20, pady=(12, 0))
            title_bar.pack_propagate(False)
            tk.Label(
                title_bar,
                text=title,
                font=("SF Pro Text", 13, "bold"),
                fg=self.colors["text"],
                bg=self.colors["card_bg"],
            ).pack(side=tk.LEFT)
        return card

    def _browse_download_dir(self):
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.settings_download_dir.delete(0, tk.END)
            self.settings_download_dir.insert(0, directory)

    def _on_theme_toggle(self):
        if self.app._theme_toggle_callback:
            self.app._theme_toggle_callback()

        new_text = (
            "🌙 Switch to Dark"
            if getattr(self.app, "theme_mode", "light") == "light"
            else "☀️ Switch to Light"
        )
        self.theme_btn.config(text=new_text)

    def _check_for_updates(self):
        def has_internet():
            try:
                urllib.request.urlopen("https://8.8.8.8", timeout=3)
                return True
            except (urllib.error.URLError, ValueError):
                return False

        if not has_internet():
            messagebox.showwarning(
                "No Internet",
                "No internet connection detected.\n\nPlease check your connection and try again.",
            )
            return

        if self.app._check_updates_callback:
            self.app._check_updates_callback()
        else:
            try:
                from update import AppUpdater

                updater = AppUpdater()
                result = updater.check_for_updates()

                if result.get("update_available"):
                    msg = f"Update Available!\n\nVersion {result.get('latest_version')} is available.\n\nCurrent version: {updater.get_current_version()}\n\nWould you like to visit the website to download?"
                    if messagebox.askyesno("Update Available", msg):
                        import webbrowser

                        webbrowser.open("https://www.websmithdigital.com")
                elif result.get("error"):
                    msg = f"{result.get('error')}\n\nWould you like to visit the website?"
                    if messagebox.askyesno("Update Check", msg):
                        import webbrowser

                        webbrowser.open("https://www.websmithdigital.com")
                else:
                    messagebox.showinfo(
                        "Up to Date",
                        f"Software is up to date.\n\nCurrent version: {updater.get_current_version()}",
                    )
            except Exception as e:
                messagebox.showerror("Update Error", f"Failed to check for updates.\n\nError: {str(e)}")

    def _open_license_modal(self):
        """Open license manager modal with ZEM License API activation"""
        from integration.wsd_license import get_license_service

        # Destroy existing modal if any
        if self._current_modal is not None:
            try:
                self._current_modal.destroy()
            except tk.TclError:
                pass
            self._current_modal = None

        modal = tk.Toplevel(self.app.root)
        modal.title("ZEMmacOS - License Manager")
        modal.geometry("750x650")
        modal.transient(self.app.root)
        modal.grab_set()

        def on_modal_close():
            self._current_modal = None
            modal.destroy()

        modal.protocol("WM_DELETE_WINDOW", on_modal_close)
        self._current_modal = modal

        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 375
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 325
        modal.geometry(f"750x650+{x}+{y}")

        # Use clam theme for consistent styling across OS
        style = ttk.Style()
        style.theme_use("clam")

        # Configure custom notebook style
        style.configure(
            "ZEM.TNotebook",
            background=self.colors["content_bg"],
            borderwidth=0,
        )
        style.configure(
            "ZEM.TNotebook.Tab",
            padding=[15, 10],
            font=("SF Pro Text", 11),
            background=self.colors["card_bg"],
            foreground=self.colors["text"],
        )
        style.map(
            "ZEM.TNotebook.Tab",
            background=[
                ("selected", self.colors["accent"]),
                ("active", self.colors["accent_hover"]),
            ],
            foreground=[
                ("selected", "#ffffff"),
                ("active", self.colors["text"]),
            ],
        )

        main_frame = tk.Frame(modal, bg=self.colors["content_bg"], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main_frame,
            text="License Manager",
            font=("SF Pro Display", 18, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
        ).pack(pady=(0, 20))

        notebook = ttk.Notebook(main_frame, style="ZEM.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Get current license info from service
        license_service = get_license_service()
        current_status = license_service.check_license()

        # ========== TAB 1: LICENSE STATUS ==========
        status_frame = tk.Frame(notebook, bg=self.colors["content_bg"])
        notebook.add(status_frame, text="📄 License Status")

        text_frame = tk.Frame(status_frame, bg=self.colors["border"], bd=1, relief=tk.FLAT)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        status_text = tk.Text(
            text_frame,
            font=("SF Mono", 10),
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10,
        )
        status_text.pack(fill=tk.BOTH, expand=True)

        def refresh_status_display():
            """Refresh the status display with current license info"""
            updated_status = license_service.check_license()
            status_text.config(state=tk.NORMAL)
            status_text.delete(1.0, tk.END)

            if updated_status.get("is_valid"):
                if updated_status.get("is_trial"):
                    content = f"""
╔══════════════════════════════════════════════════════════════╗
║                      TRIAL MODE ACTIVE                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Status:            Trial Mode                               ║
║  Days Remaining:    {updated_status.get('days_left', 0)} days
║  Expiry Date:       {updated_status.get('expiry_date', 'N/A')}
║                                                              ║
║  ⚠️ This is a 7-day trial. After expiration, a valid        ║
║     license is required to continue using ZEMmacOS.         ║
║                                                              ║
║  To purchase a license, visit:                              ║
║  https://www.websmithdigital.com                            ║
║  Support: support@websmithdigital.com                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
                else:
                    content = f"""
╔══════════════════════════════════════════════════════════════╗
║                    LICENSE ACTIVE                             ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Status:            Active                                   ║
║  Source:            {updated_status.get('source', 'unknown').upper()}
║  Days Remaining:    {updated_status.get('days_left', 0)} days
║                                                              ║
║  Customer Name:     {updated_status.get('customer_name', 'N/A')}
║  Customer Email:    {updated_status.get('customer_email', 'N/A')}
║                                                              ║
║  Hardware ID:       {license_service.get_hardware_id()[:50]}...
║                                                              ║
║  Support: support@websmithdigital.com                       ║
╚══════════════════════════════════════════════════════════════╝
"""
            else:
                error = updated_status.get('error', 'No license found')
                error_type = updated_status.get('error_type', 'missing')
                
                if error_type == "trial_expired":
                    content = f"""
╔══════════════════════════════════════════════════════════════╗
║                    TRIAL EXPIRED                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  {error}
║                                                              ║
║  Please purchase a license to continue using ZEMmacOS.      ║
║                                                              ║
║  Visit: https://www.websmithdigital.com                     ║
║  Support: support@websmithdigital.com                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
                else:
                    content = f"""
╔══════════════════════════════════════════════════════════════╗
║                    NO LICENSE FOUND                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  {error}
║                                                              ║
║  Use the "Activate License" tab to activate your license.   ║
║                                                              ║
║  If you don't have a license, you can start a 7-day trial   ║
║  or purchase at:                                            ║
║  https://www.websmithdigital.com                            ║
║  Support: support@websmithdigital.com                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
            # Update badge in main window
            if hasattr(self.app, "update_license_badge"):
                self.app.update_license_badge()

        refresh_status_display()

        # ========== TAB 2: ACTIVATE LICENSE (ZEM API) ==========
        activate_frame = tk.Frame(notebook, bg=self.colors["content_bg"])
        notebook.add(activate_frame, text="🔑 Activate License")

        activate_container = tk.Frame(activate_frame, bg=self.colors["content_bg"])
        activate_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        # Instructions
        tk.Label(
            activate_container,
            text="Activate Your License",
            font=("SF Pro Display", 16, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
        ).pack(pady=(0, 5))

        tk.Label(
            activate_container,
            text="Enter the information exactly as provided when you purchased your license.",
            font=("SF Pro Text", 10),
            fg=self.colors["muted"],
            bg=self.colors["content_bg"],
        ).pack(pady=(0, 20))

        # Name field
        tk.Label(
            activate_container,
            text="Full Name *",
            font=("SF Pro Text", 11, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))
        name_var = tk.StringVar()
        name_entry = tk.Entry(
            activate_container,
            textvariable=name_var,
            font=("SF Pro Text", 11),
            bg=self.colors["input_bg"],
            fg=self.colors["input_fg"],
            insertbackground=self.colors["accent"],
            bd=1,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=self.colors["accent"],
            highlightbackground=self.colors["border"],
        )
        name_entry.pack(fill=tk.X, pady=(0, 5))
        name_status = tk.Label(
            activate_container,
            text="",
            font=("SF Pro Text", 9),
            bg=self.colors["content_bg"],
            fg=self.colors["error"],
        )
        name_status.pack(fill=tk.X, pady=(0, 15))

        # Email field
        tk.Label(
            activate_container,
            text="Email Address *",
            font=("SF Pro Text", 11, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))
        email_var = tk.StringVar()
        email_entry = tk.Entry(
            activate_container,
            textvariable=email_var,
            font=("SF Pro Text", 11),
            bg=self.colors["input_bg"],
            fg=self.colors["input_fg"],
            insertbackground=self.colors["accent"],
            bd=1,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=self.colors["accent"],
            highlightbackground=self.colors["border"],
        )
        email_entry.pack(fill=tk.X, pady=(0, 5))
        email_status = tk.Label(
            activate_container,
            text="",
            font=("SF Pro Text", 9),
            bg=self.colors["content_bg"],
            fg=self.colors["error"],
        )
        email_status.pack(fill=tk.X, pady=(0, 15))

        # License Key field
        tk.Label(
            activate_container,
            text="License Key *",
            font=("SF Pro Text", 11, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))
        key_var = tk.StringVar()
        key_entry = tk.Entry(
            activate_container,
            textvariable=key_var,
            font=("SF Mono", 11),
            bg=self.colors["input_bg"],
            fg=self.colors["input_fg"],
            insertbackground=self.colors["accent"],
            bd=1,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=self.colors["accent"],
            highlightbackground=self.colors["border"],
        )
        key_entry.pack(fill=tk.X, pady=(0, 5))
        key_status = tk.Label(
            activate_container,
            text="",
            font=("SF Pro Text", 9),
            bg=self.colors["content_bg"],
            fg=self.colors["error"],
        )
        key_status.pack(fill=tk.X, pady=(0, 15))

        # Status label for activation result
        activation_status = tk.Label(
            activate_container,
            text="",
            font=("SF Pro Text", 10),
            bg=self.colors["content_bg"],
            fg=self.colors["success"],
        )
        activation_status.pack(fill=tk.X, pady=(0, 10))

        # Validation functions
        def validate_name():
            name = name_var.get().strip()
            if len(name) >= 2:
                name_status.config(text="✓ Valid name", fg=self.colors["success"])
                return True
            elif name:
                name_status.config(text="✗ Name must be at least 2 characters", fg=self.colors["error"])
                return False
            else:
                name_status.config(text="", fg=self.colors["error"])
                return False

        def validate_email():
            email = email_var.get().strip()
            if not email:
                email_status.config(text="", fg=self.colors["error"])
                return False
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(email_pattern, email):
                email_status.config(text="✓ Valid email", fg=self.colors["success"])
                return True
            else:
                email_status.config(text="✗ Invalid email format", fg=self.colors["error"])
                return False

        def validate_key():
            key = key_var.get().strip()
            if len(key) >= 10:
                key_status.config(text="✓ License key provided", fg=self.colors["success"])
                return True
            elif key:
                key_status.config(text="✗ License key is too short", fg=self.colors["error"])
                return False
            else:
                key_status.config(text="", fg=self.colors["error"])
                return False

        def update_activate_button(*args):
            """Update activate button state based on form validity"""
            name_valid = validate_name()
            email_valid = validate_email()
            key_valid = validate_key()
            
            if name_valid and email_valid and key_valid:
                act_btn.config(state=tk.NORMAL, cursor="hand2")
            else:
                act_btn.config(state=tk.DISABLED, cursor="arrow")

        def do_activate():
            """Activate license using ZEM License API"""
            name = name_var.get().strip()
            email = email_var.get().strip()
            key = key_var.get().strip()

            # Show loading
            act_btn.config(state=tk.DISABLED, text="Activating...")
            activation_status.config(text="Contacting license server...", fg=self.colors["accent"])
            modal.update()

            # Use LicenseService for activation - FIXED: use activate_license not activate_license_with_google
            result = license_service.activate_license(name, email, key)

            if result.get("success"):
                activation_status.config(text="✓ " + result.get("message", "License activated successfully!"), fg=self.colors["success"])
                
                # Show success message
                days = result.get("days_left", 0)
                messagebox.showinfo(
                    "Activation Successful",
                    f"License activated successfully!\n\nDays remaining: {days}\n\nThe application will now use your licensed status."
                )
                
                # Refresh displays
                refresh_status_display()
                
                # Refresh main window badge and callback
                if hasattr(self.app, "update_license_badge"):
                    self.app.update_license_badge()
                if hasattr(self.app, "on_license_activated"):
                    self.app.on_license_activated()
                
                # Close modal after success
                modal.after(1500, on_modal_close)
            else:
                error = result.get("error", "Activation failed")
                activation_status.config(text="✗ " + error, fg=self.colors["error"])
                act_btn.config(state=tk.NORMAL, text="Activate License")

        # Button frame
        btn_frame = tk.Frame(activate_container, bg=self.colors["content_bg"])
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        act_btn = tk.Button(
            btn_frame,
            text="Activate License",
            command=do_activate,
            font=("SF Pro Text", 12, "bold"),
            fg="white",
            bg=self.colors["success"],
            bd=0,
            padx=20,
            pady=10,
            cursor="arrow",
            state=tk.DISABLED,
        )
        act_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=on_modal_close,
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
        )
        cancel_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Start trial button (only if no paid license)
        if not current_status.get("is_valid") or current_status.get("is_trial"):
            start_trial_btn = tk.Button(
                btn_frame,
                text="Start 7-Day Trial",
                command=lambda: self._start_trial_and_close(modal, refresh_status_display),
                font=("SF Pro Text", 12, "bold"),
                fg="white",
                bg=self.colors["warning"],
                bd=0,
                padx=20,
                pady=10,
                cursor="hand2",
            )
            start_trial_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Set up validation tracing
        name_var.trace_add("write", update_activate_button)
        email_var.trace_add("write", update_activate_button)
        key_var.trace_add("write", update_activate_button)

        # ========== TAB 3: LICENSE ACTIONS ==========
        actions_frame = tk.Frame(notebook, bg=self.colors["content_bg"])
        notebook.add(actions_frame, text="⚙️ License Actions")

        actions_container = tk.Frame(actions_frame, bg=self.colors["content_bg"])
        actions_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        action_buttons = [
            ("🔄 Refresh License Status", self._refresh_license_status_modal, self.colors["accent"]),
            ("🗑️ Clear Local Cache", self._clear_license_cache, self.colors["error"]),
            ("💾 View Hardware ID", self._show_hardware_id, self.colors["accent"]),
            ("📋 Copy Hardware ID", self._copy_hardware_id_modal, self.colors["success"]),
        ]

        for text, cmd, color in action_buttons:
            btn = tk.Button(
                actions_container,
                text=text,
                command=lambda c=cmd: c(modal, refresh_status_display),
                font=("SF Pro Text", 11, "bold"),
                fg="white",
                bg=color,
                bd=0,
                padx=15,
                pady=8,
                cursor="hand2",
                width=30,
            )
            btn.pack(pady=6)

        # Close button
        close_frame = tk.Frame(main_frame, bg=self.colors["content_bg"])
        close_frame.pack(fill=tk.X, pady=(10, 0))

        close_btn = tk.Button(
            close_frame,
            text="Close",
            command=on_modal_close,
            font=("SF Pro Text", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["btn_secondary_bg"],
            bd=1,
            relief=tk.FLAT,
            padx=30,
            pady=10,
            cursor="hand2",
            width=20,
        )
        close_btn.pack()

    def _start_trial_and_close(self, modal, refresh_callback):
        """Start trial mode and refresh UI"""
        from integration.wsd_license import get_license_service
        
        license_service = get_license_service()
        result = license_service.start_trial()
        
        if result.get("success"):
            messagebox.showinfo("Trial Started", "7-day trial has been activated!\n\nYou can now use ZEMmacOS.")
            refresh_callback()
            if hasattr(self.app, "update_license_badge"):
                self.app.update_license_badge()
            if hasattr(self.app, "on_license_activated"):
                self.app.on_license_activated()
            modal.destroy()
        else:
            messagebox.showerror("Error", result.get("error", "Failed to start trial"))

    def _refresh_license_status_modal(self, modal, refresh_callback):
        """Force refresh license status from API"""
        from integration.wsd_license import get_license_service
        
        license_service = get_license_service()
        # FIXED: removed force_google parameter
        result = license_service.check_license()
        
        if result.get("is_valid"):
            messagebox.showinfo("License Status", "License status refreshed successfully.")
        else:
            messagebox.showinfo("License Status", f"No valid license found.\n\n{result.get('message', '')}")
        
        refresh_callback()
        if hasattr(self.app, "update_license_badge"):
            self.app.update_license_badge()

    def _clear_license_cache(self, modal, refresh_callback):
        """Clear local license cache"""
        from integration.wsd_license import get_license_service
        
        if messagebox.askyesno("Confirm", "Clear local license cache?\n\nThis will not affect your license on the server, but may require re-activation if offline."):
            license_service = get_license_service()
            # FIXED: use clear_cache not clear_local_cache
            result = license_service.clear_cache()
            
            if result.get("success"):
                messagebox.showinfo("Success", "Local license cache cleared.")
            else:
                messagebox.showerror("Error", result.get("error", "Failed to clear cache"))
            
            refresh_callback()
            if hasattr(self.app, "update_license_badge"):
                self.app.update_license_badge()

    def _show_hardware_id(self, modal, refresh_callback):
        """Show current hardware ID"""
        from integration.wsd_license import get_license_service
        
        license_service = get_license_service()
        hwid = license_service.get_hardware_id()
        
        # Create popup to show HWID
        popup = tk.Toplevel(modal)
        popup.title("Hardware ID")
        popup.geometry("500x250")
        popup.transient(modal)
        popup.grab_set()
        
        x = modal.winfo_x() + (modal.winfo_width() // 2) - 250
        y = modal.winfo_y() + (modal.winfo_height() // 2) - 125
        popup.geometry(f"500x250+{x}+{y}")
        
        frame = tk.Frame(popup, bg=self.colors["content_bg"], padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            frame,
            text="System Hardware ID",
            font=("SF Pro Display", 14, "bold"),
            fg=self.colors["text"],
            bg=self.colors["content_bg"],
        ).pack(pady=(0, 15))
        
        hwid_text = tk.Text(
            frame,
            font=("SF Mono", 10),
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            height=3,
            wrap=tk.WORD,
        )
        hwid_text.pack(fill=tk.BOTH, expand=True)
        hwid_text.insert(tk.END, hwid)
        hwid_text.config(state=tk.DISABLED)
        
        def copy_and_close():
            popup.clipboard_clear()
            popup.clipboard_append(hwid)
            messagebox.showinfo("Copied", "Hardware ID copied to clipboard")
            popup.destroy()
        
        tk.Button(
            frame,
            text="Copy to Clipboard",
            command=copy_and_close,
            font=("SF Pro Text", 10),
            fg="white",
            bg=self.colors["accent"],
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
        ).pack(pady=(15, 0))

    def _copy_hardware_id_modal(self, modal, refresh_callback):
        """Copy hardware ID to clipboard directly"""
        from integration.wsd_license import get_license_service
        
        license_service = get_license_service()
        hwid = license_service.get_hardware_id()
        
        modal.clipboard_clear()
        modal.clipboard_append(hwid)
        messagebox.showinfo("Copied", "Hardware ID copied to clipboard")

    def _save_settings(self):
        if self.app._settings_callback:
            self.app._settings_callback()

    def get_values(self):
        """Return current settings values"""
        return {
            "download_dir": self.settings_download_dir.get().strip(),
            "catalog": self.settings_catalog_var.get(),
            "threads": int(self.threads_var.get()),
        }

    def set_values(self, download_dir, catalog, threads):
        """Set settings values"""
        self.settings_download_dir.delete(0, tk.END)
        self.settings_download_dir.insert(0, download_dir)
        self.settings_catalog_var.set(catalog)
        self.threads_var.set(str(threads))