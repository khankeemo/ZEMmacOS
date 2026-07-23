f'''"""Universal License Center - unified customer interface for all license operations"""
import json
import os
import platform
import socket
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, List, Optional

from .client import ApiClient
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .universal_email_dialog import UniversalEmailDialog

SDK_VERSION = "{context.kitVersion}"
RUNTIME_TYPE = "{context.runtime}"
SUPPORT_EMAIL = "support@websmithdigital.com"


def _load_api_config() -> Dict[str, Any]:
    cfg_paths = [
        os.path.join(os.path.dirname(__file__), "config", "api-config.json"),
        os.path.join(os.getcwd(), "config", "api-config.json"),
    ]
    for cfg_path in cfg_paths:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return {{}}


class UniversalLicenseCenter:
    def __init__(self, config_path: Optional[str] = None):
        self.config = _load_api_config() if config_path is None else self._load_config(config_path)
        self.engine = LicenseEngine(config_path)
        self.client = ApiClient(self.config, HardwareDetector(), CacheManager(self.config))
        self.hardware = HardwareDetector()
        self.cache = CacheManager(self.config)
        self.email_dialog = UniversalEmailDialog(self.config, self.client, self.hardware, self.cache)
        self._status: Optional[LicenseStatus] = None
        self._root: Optional[tk.Toplevel] = None

        branding = self.config.get("branding", {{}})
        self._primary = branding.get("primary_color", "#6366f1")
        self._bg = "#f0f2f5"
        self._card_bg = "#ffffff"
        self._text_primary = "#1a1a2e"
        self._text_secondary = "#6b7280"
        self._success = "#16a34a"
        self._error = "#dc2626"
        self._warning = "#f59e0b"
        self._border = "#d1d5db"

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def show(self) -> Dict[str, Any]:
        self._status = self.engine.initialize()
        self._root = tk.Toplevel()
        self._root.title("Universal License Center")
        self._root.geometry("600x700")
        self._root.minsize(520, 620)
        self._root.resizable(True, True)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._build_ui()
        self._refresh_display()
        self._center_window()
        self._root.wait_window()
        return {{"status": self._status.to_dict() if self._status else None}}

    def _center_window(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{{w}}x{{h}}+{{x}}+{{y}}")

    def _build_ui(self):
        root = self._root

        header = tk.Frame(root, bg=self._primary, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Universal License Center",
                 font=("Segoe UI", 20, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)
        tk.Label(header, text=f"SDK v{{SDK_VERSION}} | Runtime: {{RUNTIME_TYPE}}",
                 font=("Segoe UI", 8),
                 fg="#e0e7ff", bg=self._primary).pack()

        main = tk.Frame(root, bg=self._bg, padx=20, pady=16)
        main.pack(fill="both", expand=True)

        status_frame = tk.Frame(main, bg=self._card_bg, bd=1, relief="solid",
                                highlightbackground=self._border)
        status_frame.pack(fill="x", pady=(0, 16))

        self._status_header = tk.Label(status_frame, text="License Status",
                                        font=("Segoe UI", 13, "bold"),
                                        bg=self._card_bg, fg=self._text_primary)
        self._status_header.pack(anchor="w", padx=16, pady=(12, 4))

        self._status_detail = tk.Label(status_frame, text="Checking...",
                                        font=("Segoe UI", 10),
                                        bg=self._card_bg, fg=self._text_secondary,
                                        justify="left", wraplength=540)
        self._status_detail.pack(anchor="w", padx=16, pady=(0, 12))

        sep = tk.Frame(main, bg=self._border, height=1)
        sep.pack(fill="x", pady=(0, 12))

        btn_frame = tk.Frame(main, bg=self._bg)
        btn_frame.pack(fill="both", expand=True)

        buttons = [
            ("1. View License Status", self._view_status, self._primary),
            ("2. Start Free Trial", self._start_trial, self._success),
            ("3. Activate License", self._activate_license, self._primary),
            ("4. Buy License", self._buy_license, self._warning),
            ("5. Renew License", self._renew_license, self._primary),
            ("6. Replace Device", self._replace_device, self._warning),
            ("7. Hardware Issue", self._hardware_issue, self._text_secondary),
            ("8. Contact Support", self._contact_support, self._text_secondary),
            ("9. Request History", self._request_history, self._text_secondary),
        ]

        for text, cmd, color in buttons:
            btn = tk.Button(btn_frame, text=text, command=cmd,
                            font=("Segoe UI", 11, "bold"),
                            bg=color, fg="white", relief="flat",
                            padx=12, pady=8, cursor="hand2", anchor="w")
            btn.pack(fill="x", pady=(0, 6))
            btn.bind("<Enter>", lambda e, c=color: e.widget.config(bg=self._adjust_color(c, 0.85)))
            btn.bind("<Leave>", lambda e, c=color: e.widget.config(bg=c))

        tk.Button(btn_frame, text="0. Exit", command=self._on_close,
                  font=("Segoe UI", 10), bg="#e5e7eb", fg=self._text_primary,
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(fill="x", pady=(6, 0))

        self._output_label = tk.Label(main, text="", font=("Segoe UI", 9),
                                       bg=self._bg, fg=self._text_secondary,
                                       wraplength=540, justify="left")
        self._output_label.pack(fill="x", pady=(8, 0))

    @staticmethod
    def _adjust_color(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{{r:02x}}{{g:02x}}{{b:02x}}"

    def _on_close(self):
        try:
            self._root.destroy()
        except Exception:
            pass

    def _refresh_display(self):
        if not self._status:
            self._status_detail.config(text="Status: Unknown", fg=self._text_secondary)
            return
        lines = []
        lines.append(f"Status: {{self._status.status.upper()}}")
        if self._status.license_key:
            lines.append(f"License: {{self._status.license_key}}")
        if self._status.plan:
            lines.append(f"Plan: {{self._status.plan}}")
        if self._status.expiry_date:
            lines.append(f"Expires: {{self._status.expiry_date}}")
        if self._status.days_left > 0:
            lines.append(f"Days Remaining: {{self._status.days_left}}")
        if self._status.hardware_id:
            lines.append(f"Hardware: {{self._status.hardware_id[:48]}}...")
        if self._status.message:
            lines.append(f"Message: {{self._status.message}}")

        if self._status.valid:
            fg = self._success
        elif self._status.status == "trial":
            fg = self._warning
        else:
            fg = self._error

        self._status_detail.config(text="\n".join(lines), fg=fg)

    def _set_output(self, text: str, color: str = "#6b7280"):
        self._output_label.config(text=text, fg=color)

    def _view_status(self):
        self._status = self.engine.initialize()
        self._refresh_display()
        self._set_output("Status refreshed.", self._success)

    def _start_trial(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Start Free Trial")
        dialog.geometry("400x320")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Start Free Trial", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="Name *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        name_var = tk.StringVar()
        tk.Entry(frame, textvariable=name_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Email *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        email_var = tk.StringVar()
        tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_start():
            name = name_var.get().strip()
            email = email_var.get().strip()
            if not name or not email:
                status_lbl.config(text="Name and email are required.", fg=self._error)
                return
            status_lbl.config(text="Starting trial...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.start_trial(email, customer_name=name)
                if result.get("success"):
                    self._status = self.engine.get_status()
                    self._refresh_display()
                    messagebox.showinfo("Trial Started",
                                        f"Trial started successfully!\nCheck {{email}} for details.",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Unknown error"))
                    status_lbl.config(text=f"Failed: {{err}}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {{str(e)}}", fg=self._error)

        tk.Button(frame, text="Start Trial", command=do_start,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._success, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _activate_license(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Activate License")
        dialog.geometry("420x240")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activate License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="License Key *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        key_var = tk.StringVar()
        tk.Entry(frame, textvariable=key_var, font=("Courier", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_activate():
            key = key_var.get().strip()
            if not key:
                status_lbl.config(text="License key is required.", fg=self._error)
                return
            status_lbl.config(text="Activating...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.activate(key)
                if result.get("success"):
                    self._status = self.engine.get_status()
                    self._refresh_display()
                    messagebox.showinfo("Activated", "License activated successfully!",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Unknown error"))
                    status_lbl.config(text=f"Failed: {{err}}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {{str(e)}}", fg=self._error)

        tk.Button(frame, text="Activate", command=do_activate,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _buy_license(self):
        product_name = self.config.get("product", {{}}).get("name", "our product")
        result = messagebox.askyesno(
            "Buy License",
            f"Interested in buying {{product_name}}?\n\n"
            "Submit your details and our sales team will contact you.\n\n"
            "Would you like to use the email form?",
            parent=self._root,
        )
        if result:
            self.email_dialog.show(
                request_type="BUY",
                subject=f"Buy {{product_name}} License",
            )
        else:
            messagebox.showinfo(
                "Contact Sales",
                f"Please email us at {{SUPPORT_EMAIL}} to purchase a license.",
                parent=self._root,
            )

    def _renew_license(self):
        if not self._status or not self._status.valid:
            messagebox.showwarning("Not Licensed",
                                    "No active license found. Please activate first.",
                                    parent=self._root)
            return
        result = messagebox.askyesno(
            "Renew License",
            "Would you like to submit a renewal request?\n\n"
            "Our team will contact you with renewal options.",
            parent=self._root,
        )
        if result:
            self.email_dialog.show(
                request_type="RENEW",
                subject="License Renewal Request",
                license_key=self._status.license_key or "",
                plan_name=self._status.plan or "",
            )

    def _replace_device(self):
        if not self._status or not self._status.valid:
            messagebox.showwarning("Not Licensed",
                                    "No active license found.", parent=self._root)
            return
        self.email_dialog.show(
            request_type="DEVICE_REPLACEMENT",
            subject="Device Replacement Request",
            license_key=self._status.license_key or "",
            plan_name=self._status.plan or "",
        )

    def _hardware_issue(self):
        self.email_dialog.show(
            request_type="HARDWARE",
            subject="Hardware Issue Report",
        )

    def _contact_support(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Contact Support")
        dialog.geometry("400x220")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Contact Support", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="Reason:", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))

        reason_var = tk.StringVar(value="support")
        reason_combo = ttk.Combobox(frame, textvariable=reason_var,
                                     values=["support", "activation", "trial", "billing", "other"],
                                     state="readonly", font=("Segoe UI", 10))
        reason_combo.pack(fill="x", padx=16, pady=(0, 12))

        def do_contact():
            reason = reason_var.get()
            rt = "SUPPORT"
            if reason == "activation":
                rt = "ACTIVATION"
            elif reason == "trial":
                rt = "ACTIVATION"
            elif reason == "billing":
                rt = "BUY"
            self.email_dialog.show(
                request_type=rt,
                subject=f"{{reason.capitalize()}} Support Request",
            )
            dialog.destroy()

        tk.Button(frame, text="Open Email Form", command=do_contact,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _request_history(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Request History")
        dialog.geometry("500x400")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Request History", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="Enter your email to check request status:",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
            anchor="w", padx=16, pady=(0, 8))

        email_var = tk.StringVar()
        tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 12))

        result_text = tk.Text(frame, font=("Segoe UI", 9), height=10,
                               wrap="word", relief="solid", bd=1)
        result_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        def do_fetch():
            email = email_var.get().strip()
            if not email:
                messagebox.showwarning("Input Required", "Email is required.",
                                       parent=dialog)
                return
            result_text.delete("1.0", "end")
            result_text.insert("1.0", "Fetching request history...\n")
            dialog.update()
            try:
                data = self.client.get_request_history(email)
                if data.get("success") and data.get("data", {{}}).get("requests"):
                    requests = data["data"]["requests"]
                    result_text.delete("1.0", "end")
                    for req in requests:
                        rid = req.get("request_id", "")
                        rtype = req.get("request_type", "")
                        status = req.get("status", "")
                        created = req.get("created_at", "")
                        subject = req.get("subject", "")
                        result_text.insert("end",
                                           f"{{rid}} | {{rtype}} | {{status}} | {{created}}\n"
                                           f"  Subject: {{subject}}\n\n")
                else:
                    result_text.delete("1.0", "end")
                    result_text.insert("1.0", "No requests found for this email.\n")
            except Exception as e:
                result_text.delete("1.0", "end")
                result_text.insert("1.0", f"Error fetching history: {{str(e)}}\n")

        tk.Button(frame, text="Fetch History", command=do_fetch,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(0, 12))

        dialog.wait_window()
