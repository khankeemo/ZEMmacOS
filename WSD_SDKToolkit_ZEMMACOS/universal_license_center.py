"""Universal License Center - single customer experience for all license operations"""
import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from .client import ApiClient
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog

SDK_VERSION = "1.0.0"
RUNTIME_TYPE = "python"


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
    return {}


class UniversalLicenseCenter:
    def __init__(self, config_path: Optional[str] = None,
                 on_license_ready: Optional[Callable[[bool], None]] = None):
        self.config = _load_api_config() if config_path is None else self._load_config(config_path)
        self.hardware = HardwareDetector()
        self.cache = CacheManager(self.config)
        self.client = ApiClient(self.config, self.hardware, self.cache)
        self.engine = LicenseEngine(config_path, on_license_ready=self._on_engine_ready)
        self.on_license_ready = on_license_ready
        self._status: Optional[LicenseStatus] = None
        self._root: Optional[tk.Toplevel] = None
        self._app_unlocked = False

        branding = self.config.get("branding", {})
        self._primary = branding.get("primary_color", "#6366f1")
        self._bg = "#f0f2f5"
        self._card_bg = "#ffffff"
        self._text_primary = "#1a1a2e"
        self._text_secondary = "#6b7280"
        self._success = "#16a34a"
        self._error = "#dc2626"
        self._warning = "#f59e0b"
        self._border = "#d1d5db"
        self._product_name = self.config.get("product", {}).get("name", "")
        self._company_name = branding.get("company_name", "Your Company")
        self._support_email = branding.get("support_email", "")
        self._sales_email = branding.get("sales_email", "")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _on_engine_ready(self, valid: bool):
        if valid:
            self._app_unlocked = True
        else:
            self._app_unlocked = False
        if self.on_license_ready:
            self.on_license_ready(valid)

    def _is_valid_for_unlock(self) -> bool:
        if not self._status:
            return False
        return self._status.status in ('active', 'trial')

    def _unlock_application(self):
        self._app_unlocked = True
        if self.on_license_ready:
            self.on_license_ready(True)

    def _lock_application(self):
        self._app_unlocked = False
        if self.on_license_ready:
            self.on_license_ready(False)

    def show(self) -> Dict[str, Any]:
        self._lock_application()
        self._status = self.engine.initialize()
        status = self._status.status if self._status else 'unlicensed'

        if self._is_valid_for_unlock():
            self._unlock_application()

        if status == 'unlicensed' or (not self._status):
            if not self.cache.is_onboarding_complete():
                result = self._show_welcome()
                if result.get('trial_started') or result.get('onboarding_complete'):
                    self._status = self.engine.initialize()
                    if self._is_valid_for_unlock():
                        self._unlock_application()
                    return {'action': 'trial_started', 'status': self._status.to_dict() if self._status else None}
                if result.get('skipped') and not result.get('closed'):
                    return {'action': 'skipped', 'locked': True}
                return {'action': 'closed', 'locked': True}

        return self._show_license_center()

    def _show_welcome(self) -> Dict[str, Any]:
        welcome = WelcomeDialog(
            client=self.client,
            hardware=self.hardware,
            cache=self.cache,
            product_name=self._product_name
        )
        return welcome.show()

    def _show_license_center(self) -> Dict[str, Any]:
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
        return {"status": self._status.to_dict() if self._status else None,
                "unlocked": self._app_unlocked}

    def _center_window(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        root = self._root

        header = tk.Frame(root, bg=self._primary, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Universal License Center",
                 font=("Segoe UI", 20, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

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

        status = self._status.status if self._status else 'unlicensed'
        is_valid = self._status.valid if self._status else False
        is_expired = status in ('expired', 'force_reactivation')
        is_trial = status == 'trial'
        is_paid = status == 'active' and is_valid

        if is_trial:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_paid:
            buttons = [
                ("Renew License", self._renew_license, self._primary),
                ("Replace Device", self._replace_device, self._warning),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("Sales Enquiry", self._contact_sales, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_expired:
            buttons = [
                ("Renew License", self._renew_license, self._primary),
                ("Reactivate License", self._reactivate_license, self._warning),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        else:
            buttons = [
                ("Start Free Trial", self._start_trial, self._success),
                ("Activate License", self._activate_license, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("Sales Enquiry", self._contact_sales, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]

        for text, cmd, color in buttons:
            if color == "#e5e7eb":
                btn = tk.Button(btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11),
                                bg=color, fg=self._text_primary,
                                relief="flat", padx=12, pady=8, cursor="hand2")
            else:
                btn = tk.Button(btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11, "bold"),
                                bg=color, fg="white", relief="flat",
                                padx=12, pady=8, cursor="hand2")
            btn.pack(fill="x", pady=(0, 6))

        self._output_label = tk.Label(main, text="", font=("Segoe UI", 9),
                                       bg=self._bg, fg=self._text_secondary,
                                       wraplength=540, justify="left")
        self._output_label.pack(fill="x", pady=(8, 0))

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
        lines.append(f"Status: {self._status.status.upper()}")
        if self._status.license_key:
            lines.append(f"License: {self._status.license_key}")
        if self._status.plan:
            lines.append(f"Plan: {self._status.plan}")
        if self._status.expiry_date:
            lines.append(f"Expires: {self._status.expiry_date}")
        if self._status.days_left > 0:
            lines.append(f"Days Remaining: {self._status.days_left}")
        if self._status.hardware_id:
            lines.append(f"Hardware: {self._status.hardware_id[:48]}...")
        if self._status.message:
            lines.append(f"Message: {self._status.message}")

        if self._status.valid:
            fg = self._success
        elif self._status.status == "trial":
            fg = self._warning
        else:
            fg = self._error

        self._status_detail.config(text="\n".join(lines), fg=fg)

    def _set_output(self, text: str, color: str = "#6b7280"):
        self._output_label.config(text=text, fg=color)

    def _start_trial(self):
        self._on_close()
        result = self._show_welcome()
        if result.get('trial_started'):
            self._status = self.engine.initialize()
            if self._status and self._status.valid:
                self._unlock_application()
                messagebox.showinfo("Trial Started",
                                    "Your free trial has been activated!",
                                    parent=self._root)
        elif result.get('closed'):
            self._show_license_center()

    def _activate_license(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Activate License")
        dialog.geometry("520x480")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activate License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="Hardware ID", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        hw_id = self.hardware.get_fingerprint()
        tk.Label(frame, text=hw_id[:48], font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=450).pack(anchor="w", padx=16, pady=(0, 8))

        tk.Label(frame, text="License Key *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        key_var = tk.StringVar()
        if self._status and self._status.license_key:
            key_var.set(self._status.license_key)
        tk.Entry(frame, textvariable=key_var, font=("Courier", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 12))

        if self._status and self._status.customer_name:
            tk.Label(frame, text="Customer", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
            cust_info = self._status.customer_name
            if self._status.customer_email:
                cust_info += f" \u2022 {self._status.customer_email}"
            tk.Label(frame, text=cust_info, font=("Segoe UI", 10),
                     bg=self._card_bg, fg=self._text_secondary).pack(anchor="w", padx=16, pady=(0, 12))

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
                    self._unlock_application()
                    messagebox.showinfo("Activated", "License activated successfully!",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Unknown error"))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Activate", command=do_activate,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _renew_license(self):
        if not self._status:
            messagebox.showwarning("Not Available", "No license information available.",
                                    parent=self._root)
            return

        dialog = tk.Toplevel(self._root)
        dialog.title("Renew License")
        dialog.geometry("560x580")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Renew License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="Current License", font=("Segoe UI", 11, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        current_info = f"Plan: {self._status.plan or 'N/A'}"
        if self._status.expiry_date:
            current_info += f" | Expires: {self._status.expiry_date}"
        if self._status.license_key:
            current_info += f"\nKey: {self._status.license_key}"
        tk.Label(frame, text=current_info, font=("Segoe UI", 10),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=480, justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=16, pady=8)

        tk.Label(frame, text="Request Renewal", font=("Segoe UI", 11, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        tk.Label(frame, text="Our team will contact you with renewal options.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
            anchor="w", padx=16, pady=(0, 8))

        tk.Label(frame, text="Your Name *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        name_var = tk.StringVar(value=self._status.customer_name or "")
        tk.Entry(frame, textvariable=name_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Your Email *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        email_var = tk.StringVar(value=self._status.customer_email or "")
        tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Your Mobile", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        mobile_var = tk.StringVar(value=self._status.customer_mobile or self._status.customer_phone or "")
        tk.Entry(frame, textvariable=mobile_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_send():
            name = name_var.get().strip()
            email = email_var.get().strip()
            if not name or not email:
                status_lbl.config(text="Name and email are required.", fg=self._error)
                return
            status_lbl.config(text="Submitting renewal request...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.send_renewal_request(
                    license_key=self._status.license_key or "",
                    customer_name=name, customer_email=email,
                    customer_mobile=mobile_var.get().strip(),
                    request_type='renew',
                    current_plan_id='', current_plan_name=self._status.plan or '',
                )
                if result.get("success"):
                    messagebox.showinfo("Request Submitted",
                                        "Your renewal request has been submitted.\n"
                                        "Our team will contact you shortly.",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Failed"))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Submit Renewal Request", command=do_send,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _reactivate_license(self):
        if not self._status:
            messagebox.showwarning("Not Available", "No license information available.",
                                    parent=self._root)
            return

        dialog = tk.Toplevel(self._root)
        dialog.title("Reactivate License")
        dialog.geometry("520x500")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Reactivate License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))
        tk.Label(frame, text="Submit a reactivation request to restore your license.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
            anchor="w", padx=16, pady=(0, 12))

        tk.Label(frame, text="License Key", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        key_var = tk.StringVar(value=self._status.license_key or "")
        tk.Entry(frame, textvariable=key_var, font=("Courier", 11),
                 relief="solid", bd=1, state="readonly").pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Customer Name *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        name_var = tk.StringVar(value=self._status.customer_name or "")
        tk.Entry(frame, textvariable=name_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Email *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        email_var = tk.StringVar(value=self._status.customer_email or "")
        tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Mobile", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        mobile_var = tk.StringVar(value=self._status.customer_mobile or self._status.customer_phone or "")
        tk.Entry(frame, textvariable=mobile_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Hardware ID", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        hw_id = self.hardware.get_fingerprint()
        tk.Label(frame, text=hw_id, font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=450).pack(anchor="w", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_send():
            name = name_var.get().strip()
            email = email_var.get().strip()
            if not name or not email:
                status_lbl.config(text="Name and email are required.", fg=self._error)
                return
            status_lbl.config(text="Submitting reactivation request...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.send_reactivation_request(
                    license_key=key_var.get().strip(),
                    customer_name=name,
                    customer_email=email,
                    message='',
                )
                if result.get("success"):
                    messagebox.showinfo("Request Submitted",
                                        "Your reactivation request has been submitted.\n"
                                        "Our team will contact you shortly.",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Failed"))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Submit Reactivation Request", command=do_send,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._warning, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _replace_device(self):
        if not self._status or not self._status.valid:
            messagebox.showwarning("Not Licensed",
                                    "No active license found.", parent=self._root)
            return
        dialog = tk.Toplevel(self._root)
        dialog.title("Replace Device")
        dialog.geometry("500x400")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Device Replacement", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))
        tk.Label(frame, text="Submit a device replacement request.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
            anchor="w", padx=16, pady=(0, 12))

        tk.Label(frame, text="License Key", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        lk_lbl = tk.Label(frame, text=self._status.license_key or "N/A",
                          font=("Courier", 10), bg=self._card_bg, fg=self._text_secondary)
        lk_lbl.pack(anchor="w", padx=16, pady=(0, 8))

        tk.Label(frame, text="Current Hardware", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        old_hw = self._status.hardware_id or "Unknown"
        tk.Label(frame, text=old_hw, font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=420).pack(anchor="w", padx=16, pady=(0, 8))

        tk.Label(frame, text="New Hardware", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        new_hw = self.hardware.get_fingerprint()
        tk.Label(frame, text=new_hw, font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_primary,
                 wraplength=420).pack(anchor="w", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_replace():
            status_lbl.config(text="Replacing device...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.replace_hardware()
                if result.get("success"):
                    self._status = self.engine.get_status()
                    self._refresh_display()
                    messagebox.showinfo("Device Replaced",
                                        "Device has been replaced successfully!",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Failed"))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Replace Device", command=do_replace,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._warning, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _contact_support(self):
        self._show_communication_dialog('support', 'Contact Support')

    def _contact_sales(self):
        self._show_communication_dialog('sales', 'Sales Enquiry')

    def _show_communication_dialog(self, category: str, title: str):
        dialog = tk.Toplevel(self._root)
        dialog.title(title)
        dialog.geometry("520x480")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text=title, font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))
        tk.Label(frame, text="We already know who you are. Just tell us what you need.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
            anchor="w", padx=16, pady=(0, 12))

        cached = self.cache.get_license_status() or {}

        tk.Label(frame, text="Your Name *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        name_var = tk.StringVar(value=self._status.customer_name if self._status else cached.get('customer_name', ''))
        tk.Entry(frame, textvariable=name_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Your Email *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        email_var = tk.StringVar(value=self._status.customer_email if self._status else cached.get('customer_email', ''))
        tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Subject", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        subject_var = tk.StringVar(value=title)
        tk.Entry(frame, textvariable=subject_var, font=("Segoe UI", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(frame, text="Message *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        msg_text = tk.Text(frame, font=("Segoe UI", 10), height=4,
                           wrap="word", relief="solid", bd=1)
        msg_text.pack(fill="x", padx=16, pady=(0, 12))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        def do_send():
            name = name_var.get().strip()
            email = email_var.get().strip()
            subject = subject_var.get().strip()
            msg = msg_text.get("1.0", "end").strip()
            if not name or not email:
                status_lbl.config(text="Name and email are required.", fg=self._error)
                return
            if not msg:
                status_lbl.config(text="Please describe your issue.", fg=self._error)
                return
            status_lbl.config(text="Sending your request...", fg=self._text_secondary)
            dialog.update()
            try:
                license_key = self._status.license_key if self._status else cached.get('license_key', '')
                result = self.engine.create_communication(
                    category=category,
                    customer_email=email,
                    customer_name=name,
                    subject=subject,
                    message=msg,
                    license_key=license_key or '',
                    hardware_id=self.hardware.get_fingerprint(),
                    sdk_version=SDK_VERSION,
                    runtime_type=RUNTIME_TYPE,
                )
                if result.get("success") or result.get("queued"):
                    messagebox.showinfo("Request Submitted",
                                        "Your request has been sent.\n"
                                        "We will contact you at " + email + ".",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get("message", result.get("error", "Failed"))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Send Request", command=do_send,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _view_conversations(self):
        if not self._status:
            return
        email = self._status.customer_email or ''
        if not email:
            cached = self.cache.get_license_status() or {}
            email = cached.get('customer_email', '')
        if not email:
            messagebox.showwarning("No Email", "No customer email found.",
                                    parent=self._root)
            return
        try:
            result = self.engine.list_conversations(email)
            if result.get("success"):
                conversations = result.get("data", {}).get("conversations", [])
                if not conversations:
                    messagebox.showinfo("Conversations",
                                        "No conversations found.",
                                        parent=self._root)
                    return
                dialog = tk.Toplevel(self._root)
                dialog.title("Your Conversations")
                dialog.geometry("600x500")
                dialog.configure(bg=self._bg)
                dialog.transient(self._root)
                dialog.grab_set()

                frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                                 highlightbackground=self._border)
                frame.pack(fill="both", expand=True, padx=16, pady=16)

                tk.Label(frame, text="Your Conversations",
                         font=("Segoe UI", 14, "bold"),
                         bg=self._card_bg, fg=self._text_primary).pack(
                    anchor="w", padx=12, pady=(8, 12))

                list_frame = tk.Frame(frame, bg=self._card_bg)
                list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

                canvas = tk.Canvas(list_frame, bg=self._card_bg,
                                   highlightthickness=0)
                scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                          command=canvas.yview)
                scrollable = tk.Frame(canvas, bg=self._card_bg)

                scrollable.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                canvas.create_window((0, 0), window=scrollable, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                for conv in conversations:
                    conv_frame = tk.Frame(scrollable, bg=self._card_bg,
                                          bd=1, relief="solid",
                                          highlightbackground=self._border)
                    conv_frame.pack(fill="x", pady=(0, 6), padx=4)

                    tk.Label(conv_frame,
                             text=f"{conv.get('category', '').upper()} - {conv.get('subject', 'No Subject')}",
                             font=("Segoe UI", 11, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(
                        anchor="w", padx=10, pady=(6, 2))
                    tk.Label(conv_frame,
                             text=f"Status: {conv.get('status', 'N/A')}  |  "
                                  f"{conv.get('created_at', '')[:10]}",
                             font=("Segoe UI", 9),
                             bg=self._card_bg, fg=self._text_secondary).pack(
                        anchor="w", padx=10, pady=(0, 6))

                tk.Button(frame, text="Close", command=dialog.destroy,
                          font=("Segoe UI", 11, "bold"),
                          bg=self._primary, fg="white", relief="flat",
                          padx=12, pady=6, cursor="hand2").pack(
                    padx=12, pady=(0, 12))
            else:
                messagebox.showerror("Error",
                                     "Failed to load conversations.",
                                     parent=self._root)
        except Exception as e:
            messagebox.showerror("Error",
                                 f"Failed to load conversations: {str(e)}",
                                 parent=self._root)

    def _view_notifications(self):
        if not self._status:
            return
        email = self._status.customer_email or ''
        if not email:
            cached = self.cache.get_license_status() or {}
            email = cached.get('customer_email', '')
        if not email:
            return
        try:
            result = self.engine.get_notifications(email)
            if result.get("success"):
                notifications = result.get("data", {}).get("notifications", [])
                if not notifications:
                    messagebox.showinfo("Notifications",
                                        "No notifications found.",
                                        parent=self._root)
                    return
                dialog = tk.Toplevel(self._root)
                dialog.title("Notifications")
                dialog.geometry("550x450")
                dialog.configure(bg=self._bg)
                dialog.transient(self._root)
                dialog.grab_set()

                frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                                 highlightbackground=self._border)
                frame.pack(fill="both", expand=True, padx=16, pady=16)

                tk.Label(frame, text="Notifications",
                         font=("Segoe UI", 14, "bold"),
                         bg=self._card_bg, fg=self._text_primary).pack(
                    anchor="w", padx=12, pady=(8, 12))

                list_frame = tk.Frame(frame, bg=self._card_bg)
                list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

                canvas = tk.Canvas(list_frame, bg=self._card_bg,
                                   highlightthickness=0)
                scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                          command=canvas.yview)
                scrollable = tk.Frame(canvas, bg=self._card_bg)

                scrollable.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                canvas.create_window((0, 0), window=scrollable, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                for notif in notifications:
                    nf = tk.Frame(scrollable, bg=self._card_bg,
                                  bd=1, relief="solid",
                                  highlightbackground=self._border)
                    nf.pack(fill="x", pady=(0, 6), padx=4)
                    read_status = "" if notif.get("is_read") else " (NEW)"
                    tk.Label(nf,
                             text=f"{notif.get('category', '').upper()}{read_status}",
                             font=("Segoe UI", 10, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(
                        anchor="w", padx=10, pady=(4, 0))
                    tk.Label(nf,
                             text=notif.get('title', ''),
                             font=("Segoe UI", 10),
                             bg=self._card_bg, fg=self._text_secondary).pack(
                        anchor="w", padx=10, pady=(0, 4))

                tk.Button(frame, text="Close", command=dialog.destroy,
                          font=("Segoe UI", 11, "bold"),
                          bg=self._primary, fg="white", relief="flat",
                          padx=12, pady=6, cursor="hand2").pack(
                    padx=12, pady=(0, 12))
        except Exception:
            pass
