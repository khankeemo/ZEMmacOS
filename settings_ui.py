import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SettingsUI:
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.colors = app_instance.colors
        self._sections = {}
        self._current_section = "general"

    def create_settings_view(self, container):
        self.container = container

        header = tk.Frame(container, bg=self.colors["header_bg"])
        header._role = "header"
        header.pack(fill=tk.X, padx=30, pady=24)

        right_h = tk.Frame(header, bg=self.colors["header_bg"])
        right_h.pack(side=tk.RIGHT, anchor=tk.N, pady=6)
        if hasattr(self.app, '_build_license_status_widget'):
            self.app._build_license_status_widget(right_h)

        tk.Label(header, text="Settings", font=("SF Pro Display", 26, "bold"),
                 fg=self.colors["text"], bg=self.colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(header, text="Configure your application preferences",
                 font=("SF Pro Text", 11), fg=self.colors["muted"],
                 bg=self.colors["header_bg"]).pack(anchor=tk.W, pady=2)

        body = tk.Frame(container, bg=self.colors["content_bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=30, pady=12)

        nav_frame = tk.Frame(body, bg=self.colors["card_bg"], width=200)
        nav_frame._role = "card"
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15)
        nav_frame.pack_propagate(False)

        self._nav_buttons = {}
        sections = [
            ("general", "General"),
            ("downloads", "Downloads"),
            ("appearance", "Appearance"),
            ("performance", "Performance"),
            ("updates", "Updates"),
            ("about", "About"),
        ]
        for key, label in sections:
            btn = tk.Button(
                nav_frame, text=label,
                command=lambda k=key: self._switch_section(k),
                font=("SF Pro Text", 11),
                fg=self.colors["text"],
                bg=self.colors["card_bg"],
                activebackground=self.colors["nav_hover_bg"],
                activeforeground=self.colors["accent"],
                bd=0, anchor="w", padx=16, pady=10,
                cursor="hand2",
            )
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.colors["nav_hover_bg"])
                     if b.cget("bg") != self.colors["accent"] else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors["card_bg"])
                     if b.cget("bg") != self.colors["accent"] else None)
            self._nav_buttons[key] = btn

        self._license_card_frame = tk.Frame(body, bg=self.colors["content_bg"], width=250)
        self._license_card_frame._role = "card"
        self._license_card_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15))
        self._license_card_frame.pack_propagate(False)
        self._build_license_overview()

        self._content_frame = tk.Frame(body, bg=self.colors["content_bg"])
        self._content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._switch_section("general")

    def _build_license_overview(self):
        c = self.colors
        card = tk.Frame(self._license_card_frame, bg=c["card_bg"],
                        highlightbackground=c["border"], highlightthickness=1)
        card.pack(fill=tk.X, pady=14)
        card._role = "card"

        bar = tk.Frame(card, bg=c["card_bg"])
        bar.pack(fill=tk.X, padx=18, pady=(14, 4))
        tk.Label(bar, text="License Overview", font=("SF Pro Text", 12, "bold"),
                 fg=c["text"], bg=c["card_bg"]).pack(anchor=tk.W)

        sep = tk.Frame(card, bg=c["border"], height=1)
        sep.pack(fill=tk.X, padx=18)

        self._lo_container = tk.Frame(card, bg=c["card_bg"], padx=18, pady=12)
        self._lo_container.pack(fill=tk.X)

        self._update_license_overview()

    def _update_license_overview(self):
        c = self.colors
        for w in self._lo_container.winfo_children():
            w.destroy()

        key = self.app.settings.get("license_key", "")
        license_data = self.app.settings.get("license_data", {})
        lic = license_data.get('license', {})
        active = getattr(self.app, '_license_active', False)

        if active and key:
            is_trial = lic.get('is_trial', False)
            lic_type = "Trial" if is_trial else "Licensed"
            remaining = lic.get('remaining_days', '--')
            expires_at = lic.get('expires_at', 'N/A')
            try:
                from datetime import datetime
                expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                expires_at = expiry.strftime('%d %b %Y')
            except:
                pass
            rows = [
                ("Type", lic_type),
                ("Remaining", f"{remaining} days" if remaining != '--' else '--'),
                ("Expires", str(expires_at)),
            ]
        else:
            rows = [("Type", "Not Activated")]

        for label, value in rows:
            row_f = tk.Frame(self._lo_container, bg=c["card_bg"])
            row_f.pack(fill=tk.X, pady=4)
            tk.Label(row_f, text=label, font=("SF Pro Text", 10),
                     fg=c["muted"], bg=c["card_bg"], width=10, anchor=tk.W).pack(side=tk.LEFT)
            val_color = c["success"] if value not in ("Not Activated", "--", "Trial") else c["text"]
            tk.Label(row_f, text=value, font=("SF Pro Text", 10, "bold"),
                     fg=val_color, bg=c["card_bg"]).pack(side=tk.LEFT)

        btn_frame = tk.Frame(self._lo_container, bg=c["card_bg"])
        btn_frame.pack(fill=tk.X, pady=(14, 0))
        text = "Activate License" if not active else "Manage License"
        bg_color = c["accent"] if not active else c["btn_secondary_bg"]
        fg_color = "#ffffff" if not active else c["text"]
        tk.Button(btn_frame, text=text, font=("SF Pro Text", 10, "bold"),
                  fg=fg_color, bg=bg_color, bd=0, cursor="hand2",
                  padx=16, pady=6, command=self._on_license_overview_activate).pack(fill=tk.X)

    def _on_license_overview_activate(self):
        if hasattr(self.app, 'show_settings'):
            self.app._nav_click("settings")
        self.app.root.after(100, self._focus_license_entry)

    def _focus_license_entry(self):
        if hasattr(self.app, 'settings_ui') and hasattr(self.app.settings_ui, 'license_key_entry'):
            self.app.settings_ui.license_key_entry.focus_set()

    def _switch_section(self, section):
        self._current_section = section
        for widget in self._content_frame.winfo_children():
            widget.destroy()

        for key, btn in self._nav_buttons.items():
            if key == section:
                btn.config(bg=self.colors["accent"], fg="#ffffff")
            else:
                btn.config(bg=self.colors["card_bg"], fg=self.colors["text"])

        getattr(self, f"_build_{section}", self._build_general)()
        self._update_license_overview()

    def _card(self, parent, title):
        card = tk.Frame(parent, bg=self.colors["card_bg"], relief=tk.FLAT, bd=0)
        card._role = "card"
        card.pack(fill=tk.X, pady=14)
        if title:
            bar = tk.Frame(card, bg=self.colors["card_bg"])
            bar.pack(fill=tk.X, padx=22, pady=16)
            tk.Label(bar, text=title, font=("SF Pro Text", 14, "bold"),
                     fg=self.colors["text"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
            sep = tk.Frame(card, bg=self.colors["border"], height=1)
            sep.pack(fill=tk.X, padx=22)
        inner = tk.Frame(card, bg=self.colors["card_bg"])
        inner.pack(fill=tk.X, padx=22, pady=16)
        return inner

    def _row(self, parent, label_text):
        row = tk.Frame(parent, bg=self.colors["card_bg"])
        row.pack(fill=tk.X, pady=6)
        tk.Label(row, text=label_text, font=("SF Pro Text", 11),
                 fg=self.colors["text"], bg=self.colors["card_bg"],
                 width=32, anchor="w").pack(side=tk.LEFT)
        return row

    # ---- Sections ----

    def _build_general(self):
        inner = self._card(self._content_frame, "General")
        row = self._row(inner, "Download Directory:")
        self.settings_download_dir = tk.Entry(row, font=("SF Pro Text", 11),
                                              bg=self.colors["input_bg"], fg=self.colors["input_fg"],
                                              insertbackground=self.colors["accent"],
                                              bd=1, relief=tk.FLAT)
        self.settings_download_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        tk.Button(row, text="Browse", command=self._browse_download_dir,
                  font=("SF Pro Text", 10), fg=self.colors["text"],
                  bg=self.colors["btn_secondary_bg"], bd=1, relief=tk.FLAT,
                  padx=12, pady=4, cursor="hand2").pack(side=tk.RIGHT)

        row = self._row(inner, "Apple Catalog:")
        self.settings_catalog_var = tk.StringVar(value="publicrelease")
        ttk.Combobox(row, textvariable=self.settings_catalog_var,
                     values=["publicrelease", "public", "customer", "developer"],
                     state="readonly", font=("SF Pro Text", 11)).pack(fill=tk.X)

        row = self._row(inner, "License Key:")
        saved_key = self.app.settings.get("license_key", "")
        PLACEHOLDER = "Enter your license key"
        self.license_key_var = tk.StringVar(value=saved_key if saved_key else PLACEHOLDER)
        self.license_key_entry = tk.Entry(row, textvariable=self.license_key_var,
                                          font=("SF Pro Text", 11),
                                          bg=self.colors["input_bg"],
                                          fg=self.colors["muted"] if not saved_key else self.colors["input_fg"],
                                          insertbackground=self.colors["accent"],
                                          relief=tk.SOLID, bd=1,
                                          highlightthickness=2,
                                          highlightbackground=self.colors["input_border"],
                                          highlightcolor=self.colors["accent"])
        self.license_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        def _on_lk_focus_in(event):
            if self.license_key_var.get() == PLACEHOLDER:
                self.license_key_var.set("")
                self.license_key_entry.config(fg=self.colors["input_fg"])
            self.license_key_entry.config(highlightbackground=self.colors["accent"])

        def _on_lk_focus_out(event):
            if not self.license_key_var.get().strip():
                self.license_key_var.set(PLACEHOLDER)
                self.license_key_entry.config(fg=self.colors["muted"])
            self.license_key_entry.config(highlightbackground=self.colors["input_border"])

        self.license_key_entry.bind("<FocusIn>", _on_lk_focus_in)
        self.license_key_entry.bind("<FocusOut>", _on_lk_focus_out)

        self.license_status_label = tk.Label(row, text="", font=("SF Pro Text", 9),
                                             fg=self.colors["muted"], bg=self.colors["card_bg"])
        self.license_status_label.pack(side=tk.RIGHT, padx=4)
        tk.Button(row, text="Activate", command=self._activate_license,
                  font=("SF Pro Text", 10), fg="white",
                  bg=self.colors["accent"], bd=1, relief=tk.FLAT,
                  padx=12, pady=4, cursor="hand2").pack(side=tk.RIGHT)
        self._update_license_status()

        inner2 = self._card(self._content_frame, "Actions")
        tk.Button(inner2, text="Save Settings", command=self._save_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(inner2, text="Check for Updates", command=self._check_for_updates,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["accent"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_downloads(self):
        inner = self._card(self._content_frame, "Download Settings")
        row = self._row(inner, "Download Threads:")
        self.threads_var = tk.StringVar(value=str(self.app.settings.get("download_threads", 8)))
        ttk.Combobox(row, textvariable=self.threads_var, values=["4", "8", "16", "32"],
                     state="readonly", font=("SF Pro Text", 11), width=6).pack(side=tk.LEFT)
        tk.Label(row, text="Recommended: 8", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(side=tk.LEFT, padx=10)

        row = self._row(inner, "Max Concurrent Downloads:")
        self.max_concurrent_var = tk.StringVar(value=str(self.app.settings.get("max_concurrent_downloads", 3)))
        ttk.Combobox(row, textvariable=self.max_concurrent_var, values=["1", "2", "3", "5"],
                     state="readonly", font=("SF Pro Text", 11), width=6).pack(side=tk.LEFT)

        row = self._row(inner, "Connection Timeout:")
        self.timeout_var = tk.StringVar(value=str(self.app.settings.get("timeout_seconds", 30)))
        ttk.Combobox(row, textvariable=self.timeout_var, values=["10", "20", "30", "60", "120"],
                     state="readonly", font=("SF Pro Text", 11), width=6).pack(side=tk.LEFT)
        tk.Label(row, text="seconds", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(side=tk.LEFT, padx=6)

        row = self._row(inner, "Auto-Retry on Failure:")
        self.retry_var = tk.BooleanVar(value=self.app.settings.get("retry_on_failure", True))
        ttk.Checkbutton(row, variable=self.retry_var, text=" Enabled",
                        style="TCheckbutton").pack(side=tk.LEFT)

        row = self._row(inner, "Max Retry Attempts:")
        self.max_retries_var = tk.StringVar(value=str(self.app.settings.get("max_retries", 3)))
        ttk.Combobox(row, textvariable=self.max_retries_var, values=["1", "2", "3", "5", "10"],
                     state="readonly", font=("SF Pro Text", 11), width=6).pack(side=tk.LEFT)

        inner2 = self._card(self._content_frame, "Actions")
        tk.Button(inner2, text="Save Download Settings", command=self._save_download_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_appearance(self):
        inner = self._card(self._content_frame, "Theme")
        row = self._row(inner, "Application Theme:")
        theme_frame = tk.Frame(row, bg=self.colors["card_bg"])
        theme_frame.pack(side=tk.LEFT)

        current_theme = self.app.settings.get("theme", "light")
        self._theme_var = tk.StringVar(value=current_theme)

        for mode, display in [("light", "Light"), ("dark", "Dark"), ("system", "System")]:
            rb = tk.Radiobutton(theme_frame, text=display, variable=self._theme_var,
                                value=mode, command=self._on_theme_selected,
                                font=("SF Pro Text", 11),
                                fg=self.colors["text"], bg=self.colors["card_bg"],
                                selectcolor=self.colors["card_bg"],
                                activebackground=self.colors["card_bg"],
                                activeforeground=self.colors["text"],
                                indicatoron=True)
            rb.pack(side=tk.LEFT, padx=18)

        inner2 = self._card(self._content_frame, "Preview")
        tk.Label(inner2, text="Theme changes apply immediately across the entire application.",
                 font=("SF Pro Text", 10), fg=self.colors["muted"],
                 bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(inner2, text="'System' will follow your Windows dark/light mode setting.",
                 font=("SF Pro Text", 10), fg=self.colors["muted"],
                 bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=2)

    def _build_performance(self):
        inner = self._card(self._content_frame, "Performance Settings")
        tk.Label(inner, text="Performance settings help optimize download behavior.",
                 font=("SF Pro Text", 10), fg=self.colors["muted"],
                 bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=10)

        row = self._row(inner, "Buffer Size:")
        self.buffer_var = tk.StringVar(value="8192")
        ttk.Combobox(row, textvariable=self.buffer_var, values=["4096", "8192", "16384", "32768"],
                     state="readonly", font=("SF Pro Text", 11), width=8).pack(side=tk.LEFT)
        tk.Label(row, text="bytes per chunk", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(side=tk.LEFT, padx=6)

        row = self._row(inner, "Max Simultaneous Segments:")
        self.segments_var = tk.StringVar(value="8")
        ttk.Combobox(row, textvariable=self.segments_var, values=["4", "8", "16", "32"],
                     state="readonly", font=("SF Pro Text", 11), width=6).pack(side=tk.LEFT)
        tk.Label(row, text="per download", font=("SF Pro Text", 9),
                 fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(side=tk.LEFT, padx=6)

        inner2 = self._card(self._content_frame, "Actions")
        tk.Button(inner2, text="Save Performance Settings", command=self._save_performance_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_updates(self):
        inner = self._card(self._content_frame, "Update Settings")
        row = self._row(inner, "Notifications:")
        self.notif_var = tk.BooleanVar(value=self.app.settings.get("notifications_enabled", True))
        ttk.Checkbutton(row, variable=self.notif_var, text=" Enable update notifications",
                        style="TCheckbutton").pack(side=tk.LEFT)

        inner2 = self._card(self._content_frame, "Actions")
        tk.Button(inner2, text="Check for Updates Now", command=self._check_for_updates,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["accent"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def _build_about(self):
        inner = self._card(self._content_frame, "ZEMmacOS")
        info = [
            ("Application:", "ZEMmacOS"),
            ("Version:", self.app.updater.get_current_version() if hasattr(self.app, "updater") else "3.0"),
            ("Purpose:", "macOS Download Manager"),
            ("Developer:", "Websmith Digital"),
            ("Platform:", f"{platform.system()} {platform.release()}"),
        ]
        for label, value in info:
            row = self._row(inner, label)
            tk.Label(row, text=value, font=("SF Pro Text", 11, "bold"),
                     fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        inner2 = self._card(self._content_frame, "System Information")
        sys_info = [
            ("Python Version:", platform.python_version()),
            ("Architecture:", platform.machine()),
        ]
        for label, value in sys_info:
            row = self._row(inner2, label)
            tk.Label(row, text=value, font=("SF Pro Text", 11),
                     fg=self.colors["muted"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        inner3 = self._card(self._content_frame, "License")
        license_key = self.app.settings.get("license_key", "")
        license_data = self.app.settings.get("license_data", {})
        lic = license_data.get('license', {})
        active = getattr(self.app, '_license_active', False)

        if active and license_key:
            status_text = lic.get('status', 'active').capitalize()
            lic_type = "Trial" if lic.get('is_trial', False) else "Licensed"
            remaining = lic.get('remaining_days', '--')
            expires_at = lic.get('expires_at', 'N/A')
            plan_name = lic.get('plan_name', '--')
            lic_version = lic.get('license_version', '--')
            last_val = lic.get('last_validation_at', '--')
            hardware_fp = getattr(getattr(self.app, '_license_engine', None), '_fingerprint', {})
            device_id = hardware_fp.get('fingerprint', '--')[:16] + '...' if hardware_fp.get('fingerprint') else '--'
            try:
                from datetime import datetime
                if expires_at and expires_at != 'N/A':
                    expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    expires_at = expiry.strftime('%d %b %Y')
                if last_val and last_val != '--':
                    lv = datetime.fromisoformat(last_val.replace('Z', '+00:00'))
                    last_val = lv.strftime('%d %b %Y %H:%M')
            except:
                pass
            lic_info = [
                ("License Status:", status_text),
                ("License Type:", lic_type),
                ("Days Remaining:", f"{remaining} days left" if remaining != '--' else '--'),
                ("Expiry Date:", str(expires_at)),
                ("Plan / Version:", f"{plan_name} / {lic_version}" if plan_name != '--' else '--'),
                ("Device ID:", device_id),
                ("Last Validation:", str(last_val)),
            ]
        else:
            lic_info = [
                ("License Status:", "Not Activated"),
            ]

        for label, value in lic_info:
            row = self._row(inner3, label)
            val_color = self.colors["success"] if value in ("Active", "Licensed") else self.colors["text"]
            tk.Label(row, text=value, font=("SF Pro Text", 11, "bold"),
                     fg=val_color, bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        inner4 = self._card(self._content_frame, "Legal")
        tk.Label(inner4, text="ZEMmacOS is a tool for downloading macOS installer packages from Apple's servers.",
                 font=("SF Pro Text", 10), fg=self.colors["text_secondary"],
                 bg=self.colors["card_bg"], wraplength=500, justify=tk.LEFT).pack(anchor=tk.W)

    # ---- Actions ----

    def _on_theme_selected(self):
        mode = self._theme_var.get()
        if mode != self.app.settings.get("theme", "light"):
            self.app.settings_service.set_theme(mode)

    def _browse_download_dir(self):
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.settings_download_dir.delete(0, tk.END)
            self.settings_download_dir.insert(0, directory)

    def _save_settings(self):
        if self.app._settings_callback:
            self.app._settings_callback()

    def _save_download_settings(self):
        self.app.settings.set("download_threads", int(self.threads_var.get()))
        self.app.settings.set("max_concurrent_downloads", int(self.max_concurrent_var.get()))
        self.app.settings.set("timeout_seconds", int(self.timeout_var.get()))
        self.app.settings.set("retry_on_failure", self.retry_var.get())
        self.app.settings.set("max_retries", int(self.max_retries_var.get()))
        self.app.log("Download settings saved", "info")
        messagebox.showinfo("Settings", "Download settings saved!")

    def _save_performance_settings(self):
        self.app.settings.set("buffer_size", int(self.buffer_var.get()))
        self.app.settings.set("max_segments", int(self.segments_var.get()))
        self.app.log("Performance settings saved", "info")
        messagebox.showinfo("Settings", "Performance settings saved!")

    def _get_license_key(self):
        val = self.license_key_var.get().strip()
        if val == "Enter your license key":
            return ""
        return val

    def _activate_license(self):
        key = self._get_license_key()
        if not key:
            self.license_status_label.config(text="Enter a key", fg=self.colors["error"])
            return
        if hasattr(self.app, '_activate_license_key'):
            success = self.app._activate_license_key(key)
            if success:
                self.license_status_label.config(text="Active", fg=self.colors["success"])
                self._update_license_overview()
                if self._current_section == "about":
                    self._switch_section("about")
            else:
                self.license_status_label.config(text="Failed", fg=self.colors["error"])
        else:
            self.app.settings.set("license_key", key)
            self.license_status_label.config(text="Saved", fg=self.colors["muted"])

    def _update_license_status(self):
        active = getattr(self.app, '_license_active', False)
        key = self.app.settings.get("license_key", "")
        if active and key:
            self.license_status_label.config(text="Active", fg=self.colors["success"])
        elif key:
            self.license_status_label.config(text="Inactive", fg=self.colors["error"])
        else:
            self.license_status_label.config(text="", fg=self.colors["muted"])

    def _check_for_updates(self):
        import webbrowser
        webbrowser.open("https://www.websmithdigital.com/software-store")

    def get_values(self):
        return {
            "download_dir": self.settings_download_dir.get().strip() if hasattr(self, "settings_download_dir") else "",
            "catalog": self.settings_catalog_var.get() if hasattr(self, "settings_catalog_var") else "publicrelease",
            "threads": int(self.threads_var.get()) if hasattr(self, "threads_var") else 8,
        }

    def set_values(self, download_dir, catalog, threads):
        if hasattr(self, "settings_download_dir"):
            self.settings_download_dir.delete(0, tk.END)
            self.settings_download_dir.insert(0, download_dir)
        if hasattr(self, "settings_catalog_var"):
            self.settings_catalog_var.set(catalog)
        if hasattr(self, "threads_var"):
            self.threads_var.set(str(threads))
