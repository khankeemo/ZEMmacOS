import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import platform


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

        left_h = tk.Frame(header, bg=self.colors["header_bg"])
        left_h.pack(side=tk.LEFT, anchor=tk.W)
        tk.Label(left_h, text="Settings", font=("SF Pro Display", 26, "bold"),
                 fg=self.colors["text"], bg=self.colors["header_bg"]).pack(anchor=tk.W)
        tk.Label(left_h, text="Configure your application preferences",
                 font=("SF Pro Text", 11), fg=self.colors["muted"],
                 bg=self.colors["header_bg"]).pack(anchor=tk.W, pady=2)

        right_h = tk.Frame(header, bg=self.colors["header_bg"])
        right_h.pack(side=tk.RIGHT, anchor=tk.N, pady=6, padx=4)
        self._license_badge = tk.Label(
            right_h, text="", font=("SF Pro Text", 9, "bold"),
            fg=self.colors.get("muted", "#86868b"), bg=self.colors["header_bg"]
        )
        self._license_badge.pack(side=tk.RIGHT, padx=8)

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
            ("license", "License"),
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
            btn.bind('<Return>', lambda e, k=key: self._switch_section(k))
            btn.bind('<KP_Enter>', lambda e, k=key: self._switch_section(k))
            self._nav_buttons[key] = btn

        self._content_frame = tk.Frame(body, bg=self.colors["content_bg"])
        self._content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._switch_section("general")

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

        inner2 = self._card(self._content_frame, "Actions")
        btn_save = tk.Button(inner2, text="Save Settings", command=self._save_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_save.pack(side=tk.LEFT, padx=5)
        btn_save.bind('<Return>', lambda e: self._save_settings())
        btn_save.bind('<KP_Enter>', lambda e: self._save_settings())
        btn_act = tk.Button(inner2, text="Activate License", command=self._activate_license,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["accent"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_act.pack(side=tk.LEFT, padx=5)
        btn_act.bind('<Return>', lambda e: self._activate_license())
        btn_act.bind('<KP_Enter>', lambda e: self._activate_license())
        btn_upd = tk.Button(inner2, text="Check for Updates", command=self._check_for_updates,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["warning"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_upd.pack(side=tk.LEFT, padx=5)
        btn_upd.bind('<Return>', lambda e: self._check_for_updates())
        btn_upd.bind('<KP_Enter>', lambda e: self._check_for_updates())

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
        btn_dl = tk.Button(inner2, text="Save Download Settings", command=self._save_download_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_dl.pack(side=tk.LEFT, padx=5)
        btn_dl.bind('<Return>', lambda e: self._save_download_settings())
        btn_dl.bind('<KP_Enter>', lambda e: self._save_download_settings())

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
        btn_perf = tk.Button(inner2, text="Save Performance Settings", command=self._save_performance_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_perf.pack(side=tk.LEFT, padx=5)
        btn_perf.bind('<Return>', lambda e: self._save_performance_settings())
        btn_perf.bind('<KP_Enter>', lambda e: self._save_performance_settings())

    def _build_updates(self):
        inner = self._card(self._content_frame, "Update Settings")
        row = self._row(inner, "Notifications:")
        self.notif_var = tk.BooleanVar(value=self.app.settings.get("notifications_enabled", True))
        ttk.Checkbutton(row, variable=self.notif_var, text=" Enable update notifications",
                        style="TCheckbutton").pack(side=tk.LEFT)

        inner2 = self._card(self._content_frame, "Actions")
        btn_upd = tk.Button(inner2, text="Check for Updates Now", command=self._check_for_updates,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["accent"],
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_upd.pack(side=tk.LEFT, padx=5)
        btn_upd.bind('<Return>', lambda e: self._check_for_updates())
        btn_upd.bind('<KP_Enter>', lambda e: self._check_for_updates())

    def _build_about(self):
        inner = self._card(self._content_frame, "About ZEMmacOS")
        tk.Label(inner,
                 text="View detailed product and license information using the SDK About dialog.",
                 font=("SF Pro Text", 10), fg=self.colors.get("text_secondary", "#555"),
                 bg=self.colors["card_bg"], wraplength=500, justify=tk.LEFT).pack(anchor=tk.W, pady=10)
        btn_about = tk.Button(inner, text="Open About Dialog",
                  command=self._show_about_dialog,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors.get("accent", "#0071e3"),
                  bd=0, padx=20, pady=8, cursor="hand2")
        btn_about.pack(anchor=tk.W)
        btn_about.bind('<Return>', lambda e: self._show_about_dialog())
        btn_about.bind('<KP_Enter>', lambda e: self._show_about_dialog())

        inner2 = self._card(self._content_frame, "Legal")
        tk.Label(inner2,
                 text="ZEMmacOS is a tool for downloading macOS installer packages from Apple's servers.",
                 font=("SF Pro Text", 10), fg=self.colors.get("text_secondary", "#555"),
                 bg=self.colors["card_bg"], wraplength=500, justify=tk.LEFT).pack(anchor=tk.W)

    def _show_about_dialog(self):
        from WSD_SDKToolkit_ZEMMACOS import UniversalLicenseCenter
        import os
        from pathlib import Path
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = Path(base) / 'WSD_SDKToolkit_ZEMMACOS' / 'config' / 'api-config.json'
        center = UniversalLicenseCenter(config_path=str(config_path))
        center.show()

    def _build_license(self):
        inner = self._card(self._content_frame, "License Information")
        engine = getattr(self.app, 'license_engine', None)
        status_obj = getattr(self.app, 'license_status', None) if hasattr(self.app, 'license_status') else None
        labels = engine.config.get('branding', {}).get('labels', {}) if engine and engine.config else {}
        prod = engine.config.get('product', {}) if engine and engine.config else {}

        # Customer info
        cust_name = getattr(self.app, '_customer_name', '') or ''
        cust_email = getattr(self.app, '_customer_email', '') or ''
        cust_mobile = getattr(self.app, '_customer_mobile', '') or ''

        info_rows = [
            ("Status", status_obj.status.upper() if status_obj else "--"),
            ("Product", prod.get('name', 'ZEM MAC OS')),
            ("Plan", (status_obj.plan or '--') if status_obj else "--"),
            ("Expiry", (status_obj.expiry_date or '--') if status_obj else "--"),
            ("Days Remaining", str(getattr(status_obj, 'days_left', 0)) if status_obj else "--"),
            ("Customer Name", cust_name or '--'),
            ("Email", cust_email or '--'),
            ("Mobile", cust_mobile or '--'),
        ]
        for label, value in info_rows:
            row = self._row(inner, label)
            tk.Label(row, text=value, font=("SF Pro Text", 11, "bold"),
                     fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        # License Key with show/hide
        key_row = self._row(inner, "License Key")
        license_key = (status_obj.license_key or '--') if status_obj else '--'
        self._license_key_hidden = True
        self._license_key_var = tk.StringVar(value='•' * len(license_key) if license_key != '--' else '--')
        self._license_key_label = tk.Label(key_row, textvariable=self._license_key_var, font=("SF Pro Text", 11, "bold"),
                     fg=self.colors["text"], bg=self.colors["card_bg"])
        self._license_key_label.pack(side=tk.LEFT)
        self._license_key_show_btn = tk.Button(key_row, text="Show", font=("SF Pro Text", 9),
            command=self._toggle_license_key_visibility, bd=0, padx=8, pady=2, cursor="hand2")
        self._license_key_show_btn.pack(side=tk.LEFT, padx=(8, 0))

        # Device info
        device_rows = [
            ("Hardware ID", (status_obj.hardware_id or '--') if status_obj else "--"),
            ("Max Devices", str(getattr(status_obj, 'max_devices', 0)) if status_obj else "--"),
            ("Active Devices", str(getattr(status_obj, 'active_devices', getattr(status_obj, 'device_count', 0))) if status_obj else "--"),
        ]
        for label, value in device_rows:
            row = self._row(inner, label)
            tk.Label(row, text=value, font=("SF Pro Text", 11, "bold"),
                     fg=self.colors["text"], bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        # Device bound status
        bound_row = self._row(inner, "Device Bound")
        bound_status = "Yes" if (status_obj and status_obj.hardware_id) else "No"
        bound_color = self.colors["success"] if bound_status == "Yes" else self.colors["error"]
        tk.Label(bound_row, text=bound_status, font=("SF Pro Text", 11, "bold"),
                 fg=bound_color, bg=self.colors["card_bg"]).pack(side=tk.LEFT)

        inner2 = self._card(self._content_frame, "Actions")
        btn_frame = tk.Frame(inner2, bg=self.colors["card_bg"])
        btn_frame.pack(fill=tk.X)
        self._btn_activate_lic = tk.Button(btn_frame, text="Activate License", command=self._activate_license,
                      font=("SF Pro Text", 11, "bold"),
                      fg="white", bg=self.colors["accent"],
                      bd=0, padx=20, pady=8, cursor="hand2",
                      width=24)
        self._btn_activate_lic.pack(side=tk.LEFT, padx=5)
        self._btn_activate_lic.bind('<Return>', lambda e: self._activate_license())
        self._btn_activate_lic.bind('<KP_Enter>', lambda e: self._activate_license())
        self._btn_renew_lic = tk.Button(btn_frame, text="Renew License", command=self._renew_license,
                      font=("SF Pro Text", 11, "bold"),
                      fg="white", bg=self.colors["success"],
                      bd=0, padx=20, pady=8, cursor="hand2",
                      width=24)
        self._btn_renew_lic.bind('<Return>', lambda e: self._renew_license())
        self._btn_renew_lic.bind('<KP_Enter>', lambda e: self._renew_license())
        self._btn_renew_lic.pack(side=tk.LEFT, padx=5)
        self._btn_refresh_lic = tk.Button(btn_frame, text="Refresh Status", command=self._refresh_license_status,
                      font=("SF Pro Text", 11, "bold"),
                      fg="white", bg=self.colors["muted"],
                      bd=0, padx=20, pady=8, cursor="hand2",
                      width=24)
        self._btn_refresh_lic.pack(side=tk.LEFT, padx=5)
        self._btn_refresh_lic.bind('<Return>', lambda e: self._refresh_license_status())
        self._btn_refresh_lic.bind('<KP_Enter>', lambda e: self._refresh_license_status())

    def _toggle_license_key_visibility(self):
        """Toggle license key visibility."""
        if not hasattr(self, '_license_key_hidden') or not hasattr(self, '_license_key_var'):
            return
        status_obj = getattr(self.app, 'license_status', None) if hasattr(self.app, 'license_status') else None
        license_key = (status_obj.license_key or '') if status_obj else ''
        if self._license_key_hidden:
            self._license_key_var.set(license_key)
            self._license_key_show_btn.config(text="Hide")
            self._license_key_hidden = False
        else:
            self._license_key_var.set('•' * len(license_key) if license_key else '--')
            self._license_key_show_btn.config(text="Show")
            self._license_key_hidden = True

    def _update_license_panel(self):
        """Refresh the license section if currently visible."""
        if self._current_section == "license":
            status_obj = getattr(self.app, 'license_status', None) if hasattr(self.app, 'license_status') else None
            if hasattr(self, '_license_badge') and self._license_badge.winfo_exists():
                if status_obj and status_obj.valid:
                    text = f'ACTIVE  {status_obj.days_left}d' if not status_obj.trial_active else f'TRIAL  {status_obj.days_left}d'
                    fg = self.colors["success"] if not status_obj.trial_active else self.colors["warning"]
                    self._license_badge.config(text=text, fg=fg)
                else:
                    self._license_badge.config(text='UNLICENSED', fg=self.colors["error"])

    def _activate_license(self):
        act = getattr(self.app, 'open_activation', None)
        if act:
            act()

    def _renew_license(self):
        engine = getattr(self.app, 'license_engine', None)
        if not engine:
            messagebox.showwarning("License Engine", "License engine not initialized.")
            return
        act = getattr(self.app, 'open_renew_license', None)
        if act:
            act()

    def _refresh_license_status(self):
        ref = getattr(self.app, 'refresh_license', None)
        if ref:
            ref()
        if hasattr(self, '_build_license'):
            self._switch_section("license")

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
