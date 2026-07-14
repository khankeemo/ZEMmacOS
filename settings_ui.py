import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import platform

from SDK_ZEM_MAC_OS_prod_zemmacos import LicenseEngine


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

    def _build_license(self):
        c = self.colors
        engine = getattr(self.app, 'license_engine', None)
        status = engine.get_status() if engine else None

        inner = self._card(self._content_frame, "License Status")
        if status:
            rows = [
                ("Status", status.status.upper()),
                ("Plan", status.plan or 'N/A'),
                ("Expires", status.expires_at or 'N/A'),
                ("Days Remaining", str(status.days_remaining)),
                ("Hardware ID", (status.hardware_id or 'N/A')[:40] + '...' if status.hardware_id and len(status.hardware_id) > 40 else (status.hardware_id or 'N/A')),
                ("Valid", "\u2705 Yes" if status.valid else "\u274c No"),
                ("Message", status.message or ''),
            ]
            for label, val in rows:
                row = self._row(inner, label)
                tk.Label(row, text=val, font=("SF Pro Text", 11),
                         fg=c["text"], bg=c["card_bg"]).pack(side=tk.LEFT)
        else:
            tk.Label(inner, text="License engine not initialized.",
                     font=("SF Pro Text", 11), fg=c["muted"],
                     bg=c["card_bg"]).pack(anchor=tk.W, pady=10)

        inner2 = self._card(self._content_frame, "Actions")
        if engine and status:
            if status.valid:
                def do_deactivate():
                    key = engine.get_license_key()
                    if not key:
                        messagebox.showerror("Error", "No license key available")
                        return
                    if messagebox.askyesno("Deactivate", "Deactivate license on this device?"):
                        try:
                            result = engine.deactivate(key)
                            if result.get('success'):
                                messagebox.showinfo("Success", "License deactivated")
                                self._switch_section("license")
                            else:
                                messagebox.showerror("Error", result.get('message', 'Deactivation failed'))
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                tk.Button(inner2, text="Deactivate License",
                          font=("SF Pro Text", 11, "bold"),
                          fg="white", bg=c["error"],
                          bd=0, padx=20, pady=8, cursor="hand2",
                          command=do_deactivate).pack(side=tk.LEFT, padx=5)
            else:
                def open_activate():
                    d = tk.Toplevel(self.parent)
                    d.title("Activate License")
                    d.geometry("400x200")
                    d.resizable(False, False)
                    d.transient(self.parent)
                    d.grab_set()
                    tk.Label(d, text="Enter License Key", font=("SF Pro Text", 12, "bold"),
                             fg=c["text"], bg=c["card_bg"]).pack(pady=15)
                    key_var = tk.StringVar()
                    entry = tk.Entry(d, textvariable=key_var, font=("SF Pro Text", 12),
                                     bg=c["input_bg"], fg=c["input_fg"],
                                     bd=1, relief=tk.FLAT, width=30)
                    entry.pack(pady=10)
                    def do_activate():
                        key = key_var.get().strip()
                        if not key:
                            messagebox.showerror("Error", "Enter a license key")
                            return
                        try:
                            result = engine.activate(key)
                            if result.get('success'):
                                messagebox.showinfo("Success", "License activated!")
                                d.destroy()
                                self._switch_section("license")
                            else:
                                messagebox.showerror("Error", result.get('message', 'Activation failed'))
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                    tk.Button(d, text="Activate", font=("SF Pro Text", 11, "bold"),
                              fg="white", bg=c["success"], bd=0, padx=20, pady=8,
                              cursor="hand2", command=do_activate).pack(pady=10)
                tk.Button(inner2, text="Activate License",
                          font=("SF Pro Text", 11, "bold"),
                          fg="white", bg=c["success"],
                          bd=0, padx=20, pady=8, cursor="hand2",
                          command=open_activate).pack(side=tk.LEFT, padx=5)

        inner3 = self._card(self._content_frame, "Support")
        support_email = "support@websmithdigital.com"
        try:
            if engine and engine.config:
                support_email = engine.config.get("branding", {}).get("support_email", support_email)
        except Exception:
            pass
        tk.Label(inner3, text=f"For license issues contact: {support_email}",
                 font=("SF Pro Text", 10), fg=c["text_secondary"],
                 bg=c["card_bg"]).pack(anchor=tk.W, pady=6)
        tk.Label(inner3, text="https://websmith-z.vercel.app",
                 font=("SF Pro Text", 10), fg=c["accent"],
                 bg=c["card_bg"]).pack(anchor=tk.W)

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
