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
        tk.Button(inner2, text="Save Settings", command=self._save_settings,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["success"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(inner2, text="Activate License", command=self._activate_license,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["accent"],
                  bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(inner2, text="Check for Updates", command=self._check_for_updates,
                  font=("SF Pro Text", 11, "bold"),
                  fg="white", bg=self.colors["warning"],
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

        inner4 = self._card(self._content_frame, "Legal")
        tk.Label(inner4, text="ZEMmacOS is a tool for downloading macOS installer packages from Apple's servers.",
                 font=("SF Pro Text", 10), fg=self.colors["text_secondary"],
                 bg=self.colors["card_bg"], wraplength=500, justify=tk.LEFT).pack(anchor=tk.W)

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
        buttons = [
            ("Activate License", self._activate_license, self.colors["accent"]),
            ("Renew License", self._renew_license, self.colors["success"]),
            ("Refresh Status", self._refresh_license_status, self.colors["muted"]),
        ]
        for text, cmd, clr in buttons:
            tk.Button(btn_frame, text=text, command=cmd,
                      font=("SF Pro Text", 11, "bold"),
                      fg="white", bg=clr,
                      bd=0, padx=20, pady=8, cursor="hand2",
                      width=24).pack(side=tk.LEFT, padx=5)

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

    def _activate_license(self):
        act = getattr(self.app, 'open_activation', None)
        if act:
            act()

    def _renew_license(self):
        branding = getattr(self.app, 'license_engine', None)
        branding = branding.config.get('branding', {}) if branding and branding.config else {}
        support_email = branding.get('support_email', 'support@websmithdigital.com')
        status_obj = getattr(self.app, 'license_status', None)
        license_key = (status_obj.license_key or '') if status_obj else ''
        customer_name = (status_obj.customer_name or '') if status_obj else ''
        customer_email = (status_obj.customer_email or '') if status_obj else ''
        colors = self.colors
        d = tk.Toplevel(self.parent)
        d.transient(self.parent)
        d.grab_set()
        d.title("Renew License")
        d.geometry("440x340")
        d.resizable(False, False)
        d.configure(bg=colors.get("card_bg", "#ffffff"))
        d.update_idletasks()
        sw = d.winfo_screenwidth(); sh = d.winfo_screenheight()
        w = d.winfo_width(); h = d.winfo_height()
        d.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        header = tk.Frame(d, bg=colors.get("accent", "#6366f1"), height=50)
        header.pack(fill=tk.X); header.pack_propagate(False)
        tk.Label(header, text="Renew License", fg="white",
                 bg=colors.get("accent", "#6366f1"),
                 font=("SF Pro Text", 14, "bold")).pack(expand=True)
        body = tk.Frame(d, bg=colors.get("card_bg", "#ffffff"), padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(body, text="Renewal requests are handled by the administrator.",
                 font=("SF Pro Text", 11),
                 fg=colors.get("text", "#333"),
                 bg=colors.get("card_bg", "#ffffff"),
                 wraplength=400, justify="left").pack(anchor=tk.W, pady=(8, 4))
        tk.Label(body, text="Please contact:",
                 font=("SF Pro Text", 10),
                 fg=colors.get("muted", "#888"),
                 bg=colors.get("card_bg", "#ffffff"),
                 wraplength=400, justify="left").pack(anchor=tk.W, pady=(0, 6))
        email_frame = tk.Frame(body, bg=colors.get("input_bg", "#f5f5f7"),
                               highlightbackground=colors.get("border", "#d1d5db"),
                               highlightthickness=1)
        email_frame.pack(fill=tk.X, pady=(0, 14))
        tk.Label(email_frame, text=support_email,
                 font=("Courier", 11, "bold"),
                 bg=colors.get("input_bg", "#f5f5f7"),
                 fg=colors.get("accent", "#6366f1")).pack(padx=12, pady=8)
        btn_frame = tk.Frame(body, bg=colors.get("card_bg", "#ffffff"))
        btn_frame.pack(fill=tk.X)
        close_btn = tk.Button(btn_frame, text="Close", command=d.destroy,
                               font=("SF Pro Text", 11),
                               bg=colors.get("btn_secondary_bg", "#e5e7eb"),
                               fg=colors.get("text", "#333"),
                               bd=0, padx=16, pady=6, cursor="hand2")
        close_btn.pack(side=tk.LEFT, padx=(0, 8))
        def copy_email():
            d.clipboard_clear(); d.clipboard_append(support_email)
            close_btn.config(text="Copied!", fg=colors.get("success", "#16a34a"))
            d.after(1500, lambda: close_btn.config(text="Close", fg=colors.get("text", "#333")))
        copy_btn = tk.Button(btn_frame, text="Copy Email", command=copy_email,
                              font=("SF Pro Text", 11, "bold"),
                              bg=colors.get("accent", "#6366f1"), fg="white",
                              bd=0, padx=16, pady=6, cursor="hand2")
        copy_btn.pack(side=tk.LEFT)
        def open_email():
            import webbrowser
            subject = "License Renewal Request"
            body_lines = [
                "Hello,",
                "",
                "I would like to renew my license.",
                "",
                f"License Key: {license_key}",
                f"Customer: {customer_name}",
                f"Email: {customer_email}",
                "",
                "Thank you.",
            ]
            body_text = "\n".join(body_lines)
            from urllib.parse import quote
            mailto_url = f"mailto:{support_email}?subject={quote(subject)}&body={quote(body_text)}"
            webbrowser.open(mailto_url)
        open_btn = tk.Button(btn_frame, text="Open Email", command=open_email,
                              font=("SF Pro Text", 11, "bold"),
                              bg=colors.get("accent", "#6366f1"), fg="white",
                              bd=0, padx=16, pady=6, cursor="hand2")
        open_btn.pack(side=tk.LEFT, padx=(5, 0))
        d.bind('<Escape>', lambda e: d.destroy())

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
