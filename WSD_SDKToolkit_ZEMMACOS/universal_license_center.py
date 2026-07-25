"""Universal License Center - single customer experience for all license operations"""
import json
import os
import time
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


class LiveLog:
    _entries: list = []

    @classmethod
    def log(cls, event: str, detail: str = "") -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] {event}"
        if detail:
            entry += f" — {detail}"
        cls._entries.append(entry)
        print(entry)

    @classmethod
    def get_log(cls) -> list:
        return list(cls._entries)

    @classmethod
    def clear(cls) -> None:
        cls._entries = []


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
        self._trial_consumed = False

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
        LiveLog.log("License Center started", "Application lock engaged")
        self._lock_application()
        LiveLog.log("Engine initializing", "Starting decision engine")
        self._status = self.engine.initialize()
        status = self._status.status if self._status else 'unlicensed'
        LiveLog.log("Decision engine result", f"Status: {status}")

        if status == 'unlicensed' or (not self._status):
            if not self.cache.is_onboarding_complete():
                LiveLog.log("Opening Welcome", "Onboarding required")
                result = self._show_welcome()
                if result.get('trial_started'):
                    LiveLog.log("Trial started via Welcome")
                    self._status = self.engine.initialize()
                    return {'action': 'trial_started', 'status': self._status.to_dict() if self._status else None}
                if result.get('trial_consumed'):
                    LiveLog.log("Existing customer detected", "Trial already consumed — showing license center")
                    self._status = self.engine.initialize()
                    return self._show_license_center(trial_consumed=True)
                if result.get('onboarding_complete'):
                    LiveLog.log("Onboarding complete", "Re-initializing engine")
                    self._status = self.engine.initialize()
                    return {'action': 'trial_started', 'status': self._status.to_dict() if self._status else None}
                if result.get('skipped') and not result.get('closed'):
                    return {'action': 'skipped', 'locked': True}
                return {'action': 'closed', 'locked': True}

        return self._show_license_center()

    def _show_welcome(self) -> Dict[str, Any]:
        LiveLog.log("Opening Welcome Dialog")
        welcome = WelcomeDialog(
            client=self.client,
            hardware=self.hardware,
            cache=self.cache,
            product_name=self._product_name
        )
        return welcome.show()

    def _show_license_center(self, trial_consumed: bool = False) -> Dict[str, Any]:
        LiveLog.log("Opening Universal License Center",
                     f"Status: {self._status.status if self._status else 'unlicensed'}, "
                     f"trial_consumed={trial_consumed}")
        self._trial_consumed = trial_consumed
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
                "unlocked": self._app_unlocked,
                "trial_consumed": trial_consumed}

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
                ("View Hardware Status", self._view_hardware_status, self._text_secondary),
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
            if self._trial_consumed:
                buttons = [
                    ("Activate License", self._activate_license, self._primary),
                    ("Contact Support", self._contact_support, self._text_secondary),
                    ("Sales Enquiry", self._contact_sales, self._text_secondary),
                    ("Exit", self._on_close, "#e5e7eb"),
                ]
                self._status_detail.config(
                    text="This email has already used its free trial. Please Activate a License or Contact Sales.",
                    fg=self._warning
                )
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
        LiveLog.log("Opening Welcome (from Start Free Trial button)")
        self._on_close()
        result = self._show_welcome()
        if result.get('trial_started'):
            self._status = self.engine.initialize()
            if self._status and self._status.valid:
                self._unlock_application()
                messagebox.showinfo("Trial Started",
                                    "Your free trial has been activated!",
                                    parent=self._root)
        elif result.get('trial_consumed'):
            LiveLog.log("Existing customer detected", "Trial already consumed — showing license center")
            self._status = self.engine.initialize()
            self._trial_consumed = True
            self._show_license_center(trial_consumed=True)
        elif result.get('closed'):
            self._show_license_center()

    def _show_restart_prompt(self, parent):
        restart_win = tk.Toplevel(parent)
        restart_win.title("Restart Required")
        restart_win.geometry("420x200")
        restart_win.configure(bg=self._bg)
        restart_win.transient(parent)
        restart_win.grab_set()

        frame = tk.Frame(restart_win, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activation completed successfully.",
                 font=("Segoe UI", 12, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        tk.Label(frame, text="The application must now restart to apply your license.",
                 font=("Segoe UI", 10),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=360).pack(anchor="w", padx=16, pady=(0, 16))

        btn_frame = tk.Frame(frame, bg=self._card_bg)
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        def restart_now():
            restart_win.destroy()
            parent.destroy()
            import sys
            sys.exit(0)

        tk.Button(btn_frame, text="Restart Now", command=restart_now,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="Restart Later", command=restart_win.destroy,
                  font=("Segoe UI", 11),
                  bg=self._text_secondary, fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2").pack(side="left")

        restart_win.wait_window()

    def _show_activation_confirmation(self, parent, data, license_key):
        confirm = tk.Toplevel(parent)
        confirm.title("Activation Successful")
        confirm.geometry("500x480")
        confirm.configure(bg=self._bg)
        confirm.transient(parent)
        confirm.grab_set()

        frame = tk.Frame(confirm, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activation Successful", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._success).pack(anchor="w", padx=16, pady=(12, 8))

        info_items = [
            ("Customer", data.get('customer_name', 'N/A')),
            ("Email", data.get('customer_email', 'N/A')),
            ("License Key", (license_key[:4] + "-****-" + license_key[-4:]) if len(license_key) > 8 else "****"),
            ("Plan", data.get('plan', 'N/A')),
            ("Status", data.get('status', 'active')),
            ("Activation Date", data.get('activation_date', 'N/A')),
            ("Expiry Date", data.get('expiry_date', 'N/A')),
            ("Remaining Validity", f"{data.get('days_left', 0)} days"),
            ("Device", data.get('hardware_id', self.hardware.get_fingerprint())[:32]),
        ]

        for label, value in info_items:
            row = tk.Frame(frame, bg=self._card_bg)
            row.pack(fill="x", padx=16, pady=(2, 2))
            tk.Label(row, text=label + ":", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary, width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10),
                     bg=self._card_bg, fg=self._text_secondary, anchor="w").pack(side="left", fill="x")

        tk.Button(frame, text="Continue", command=lambda: [confirm.destroy(), self._show_restart_prompt(parent)],
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2").pack(padx=16, pady=(16, 12))

        confirm.wait_window()

    def _activate_license(self):
        LiveLog.log("Opening Activation", "Dialog displayed")
        dialog = tk.Toplevel(self._root)
        dialog.title("Activate License")
        dialog.geometry("560x620")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activate License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        # === PHASE 1: Hardware + License Key + Validate ===
        phase1 = tk.Frame(frame, bg=self._card_bg)
        phase1.pack(fill="x", padx=0, pady=0)

        tk.Label(phase1, text="Hardware ID", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        hw_id = self.hardware.get_fingerprint()
        tk.Label(phase1, text=hw_id[:48], font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=480).pack(anchor="w", padx=16, pady=(0, 8))

        tk.Label(phase1, text="License Key *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        key_var = tk.StringVar()
        key_entry = tk.Entry(phase1, textvariable=key_var, font=("Courier", 11),
                             relief="solid", bd=1)
        key_entry.pack(fill="x", padx=16, pady=(0, 8))

        # === PHASE 2: Customer Info (hidden until validated) ===
        phase2 = tk.Frame(frame, bg=self._card_bg)
        cust_name_lbl = tk.Label(phase2, text="", font=("Segoe UI", 10, "bold"),
                                 bg=self._card_bg, fg=self._text_primary)
        cust_email_lbl = tk.Label(phase2, text="", font=("Segoe UI", 10),
                                  bg=self._card_bg, fg=self._text_secondary)
        cust_plan_lbl = tk.Label(phase2, text="", font=("Segoe UI", 10),
                                 bg=self._card_bg, fg=self._text_secondary)

        # === OTP Section (hidden until validated) ===
        otp_frame = tk.Frame(frame, bg=self._card_bg)
        otp_var = tk.StringVar()

        # === PHASE 3: Activate button ===
        activate_frame = tk.Frame(frame, bg=self._card_bg)

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg)
        status_lbl.pack(padx=16)

        validated = {"key": "", "data": {}, "done": False}
        otp_verified = {"done": False}

        def do_validate():
            if validated["done"]:
                return
            key = key_var.get().strip()
            if not key:
                status_lbl.config(text="License key is required.", fg=self._error)
                return
            status_lbl.config(text="Validating license...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.validate(key)
                err_data = result.get('error', {})
                err_code = ''
                if isinstance(err_data, dict):
                    err_code = err_data.get('code', '')
                if result.get("success"):
                    data = result.get("data", result)
                    validated["key"] = key
                    validated["data"] = data
                    validated["done"] = True

                    # Check if already activated on this device
                    if data.get('this_device_activated'):
                        status_lbl.config(
                            text="License already activated on this device. You can continue using the application.",
                            fg=self._success)
                        dialog.after(3000, dialog.destroy)
                        return

                    # Check device limit
                    active_devices = data.get('active_devices', 0)
                    max_devices = data.get('max_devices', 999)
                    if active_devices >= max_devices:
                        status_lbl.config(
                            text=f"Device limit reached ({active_devices}/{max_devices}). Please deactivate another device or contact support.",
                            fg=self._error)
                        return

                    # Lock key entry
                    key_entry.config(state="disabled")

                    # Show customer info
                    tk.Label(phase2, text="Customer", font=("Segoe UI", 10, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
                    cust_name_lbl.config(text=data.get('customer_name', 'N/A'))
                    cust_name_lbl.pack(anchor="w", padx=16, pady=(0, 2))
                    cust_email_lbl.config(text=data.get('customer_email', 'N/A'))
                    cust_email_lbl.pack(anchor="w", padx=16, pady=(0, 2))
                    plan_info = f"Product: {data.get('product_name', 'N/A')} | Plan: {data.get('plan', 'N/A')} | Status: {data.get('status', 'N/A')} | Expires: {data.get('expiry_date', 'N/A')} | Days Left: {data.get('days_left', 0)}"
                    cust_plan_lbl.config(text=plan_info)
                    cust_plan_lbl.pack(anchor="w", padx=16, pady=(0, 8))

                    sep_valid = tk.Frame(phase2, bg=self._border, height=1)
                    sep_valid.pack(fill="x", padx=16, pady=(4, 8))

                    phase2.pack(fill="x", padx=0, pady=0)
                    validate_btn.pack_forget()
                    dialog.geometry("560x620")

                    # Show OTP section
                    tk.Label(otp_frame, text="OTP Verification", font=("Segoe UI", 11, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(8, 4))
                    email = data.get('customer_email', '')
                    tk.Label(otp_frame, text=f"OTP sent to: {email}",
                             font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
                        anchor="w", padx=16, pady=(0, 8))
                    tk.Label(otp_frame, text="OTP Code", font=("Segoe UI", 10, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
                    tk.Entry(otp_frame, textvariable=otp_var, font=("Courier", 11),
                             relief="solid", bd=1, width=16).pack(anchor="w", padx=16, pady=(0, 8))

                    sep_otp = tk.Frame(otp_frame, bg=self._border, height=1)
                    sep_otp.pack(fill="x", padx=16, pady=(4, 8))

                    otp_frame.pack(fill="x", padx=0, pady=0)
                    otp_btn_frame.pack(fill="x", padx=16, pady=(4, 8))

                    self._on_send_otp_inline(email, status_lbl)
                else:
                    err_msg = "Validation failed"
                    err_data = result.get('error', result)
                    if isinstance(err_data, dict):
                        err_msg = err_data.get('message', err_msg)
                    if err_code == 'LICENSE_EXPIRED':
                        status_lbl.config(text="License has expired. Please renew your license.", fg=self._error)
                    elif err_code == 'LICENSE_REVOKED':
                        status_lbl.config(text="License has been revoked. Please contact support.", fg=self._error)
                    elif err_code == 'LICENSE_INACTIVE':
                        status_lbl.config(text="License is inactive. Please contact support.", fg=self._error)
                    elif err_code == 'LICENSE_DELETED':
                        status_lbl.config(text="License has been deleted. Please contact support.", fg=self._error)
                    else:
                        status_lbl.config(text=f"Validation failed: {err_msg}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        validate_btn = tk.Button(phase1, text="Validate License", command=do_validate,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=12, pady=6, cursor="hand2")
        validate_btn.pack(fill="x", padx=16, pady=(8, 12))

        def do_send_otp():
            email = validated["data"].get('customer_email', '')
            self._on_send_otp_inline(email, status_lbl)

        def do_verify_otp():
            if otp_verified["done"]:
                return
            otp = otp_var.get().strip()
            if not otp:
                status_lbl.config(text="OTP code is required.", fg=self._error)
                return
            email = validated["data"].get('customer_email', '')
            if not email:
                status_lbl.config(text="No customer email available.", fg=self._error)
                return
            status_lbl.config(text="Verifying OTP...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.client.verify_otp(email, otp)
                if result.get("success"):
                    otp_verified["done"] = True
                    status_lbl.config(text="OTP verified. You may now activate.", fg=self._success)
                    send_otp_btn.config(state="disabled")
                    verify_otp_btn.config(state="disabled")

                    # Show activate button
                    activate_frame.pack(fill="x", padx=0, pady=0)
                    activate_btn.pack(fill="x", padx=16, pady=(8, 12))
                else:
                    err = result.get('error', result.get('message', 'Verification failed'))
                    if isinstance(err, dict):
                        err = err.get('message', str(err))
                    status_lbl.config(text=f"OTP verification failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"OTP error: {str(e)}", fg=self._error)

        otp_btn_frame = tk.Frame(otp_frame, bg=self._card_bg)
        send_otp_btn = tk.Button(otp_btn_frame, text="Send OTP", command=do_send_otp,
                                 font=("Segoe UI", 10, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=10, pady=4, cursor="hand2")
        send_otp_btn.pack(side="left", padx=(0, 8))
        verify_otp_btn = tk.Button(otp_btn_frame, text="Verify OTP", command=do_verify_otp,
                                   font=("Segoe UI", 10, "bold"),
                                   bg=self._primary, fg="white", relief="flat",
                                   padx=10, pady=4, cursor="hand2")
        verify_otp_btn.pack(side="left")

        def do_activate():
            if not otp_verified["done"]:
                status_lbl.config(text="Please verify OTP before activating.", fg=self._error)
                return
            key = validated["key"]
            status_lbl.config(text="Activating license...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.activate(key)
                if result.get("success"):
                    if result.get('already_activated'):
                        status_lbl.config(
                            text="License already activated on this device. You can continue using the application.",
                            fg=self._success)
                        dialog.after(2000, dialog.destroy)
                        return
                    data = result.get("data", result)
                    data["customer_name"] = validated["data"].get("customer_name", "")
                    data["customer_email"] = validated["data"].get("customer_email", "")
                    self._status = self.engine.get_status()
                    self._refresh_display()
                    self._unlock_application()
                    dialog.withdraw()
                    self._show_activation_confirmation(dialog, data, key)
                    dialog.destroy()
                else:
                    err_data = result.get('error', {})
                    err_code = ''
                    if isinstance(err_data, dict):
                        err_code = err_data.get('code', '')
                    err = result.get("message", result.get("error", "Unknown error"))
                    if err_code == 'MAX_DEVICES_EXCEEDED':
                        status_lbl.config(text="Device limit reached. Please deactivate another device or contact support.", fg=self._error)
                    elif err_code == 'LICENSE_EXPIRED':
                        status_lbl.config(text="License has expired. Please renew your license.", fg=self._error)
                    elif err_code == 'LICENSE_REVOKED':
                        status_lbl.config(text="License has been revoked. Please contact support.", fg=self._error)
                    elif err_code == 'LICENSE_INACTIVE':
                        status_lbl.config(text="License is inactive. Please contact support.", fg=self._error)
                    elif result.get('already_activated'):
                        status_lbl.config(text="License already activated on this device.", fg=self._success)
                    else:
                        status_lbl.config(text=f"Activation failed: {err}", fg=self._error)
            except Exception as e:
                status_lbl.config(text=f"Activation error: {str(e)}", fg=self._error)

        activate_btn = tk.Button(activate_frame, text="Activate License", command=do_activate,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._success, fg="white", relief="flat",
                                 padx=12, pady=6, cursor="hand2")

        dialog.wait_window()

    def _on_send_otp_inline(self, email, status_lbl):
        if not email:
            status_lbl.config(text="No customer email available for OTP.", fg=self._error)
            return
        status_lbl.config(text="Sending OTP...", fg=self._text_secondary)
        status_lbl.update()
        try:
            result = self.client.send_otp(email)
            if result.get("success"):
                status_lbl.config(text=f"OTP sent to {email}. Enter code below.", fg=self._success)
            else:
                err = result.get('error', result.get('message', 'Failed to send OTP'))
                if isinstance(err, dict):
                    err = err.get('message', str(err))
                status_lbl.config(text=f"OTP send failed: {err}", fg=self._error)
        except Exception as e:
            status_lbl.config(text=f"OTP error: {str(e)}", fg=self._error)

    def _renew_license(self):
        LiveLog.log("Opening Renewal", "Dialog displayed")
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
        LiveLog.log("Opening Reactivation", "Dialog displayed")
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

    def _view_hardware_status(self):
        if not self._status:
            messagebox.showwarning("No Status", "No license status available.", parent=self._root)
            return
        hw_id = self.hardware.get_fingerprint()
        dialog = tk.Toplevel(self._root)
        dialog.title("Hardware Status")
        dialog.geometry("500x350")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(frame, text="Hardware Status", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))
        tk.Label(frame, text=f"Current Hardware ID:", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        tk.Label(frame, text=hw_id, font=("Courier", 9),
                 bg=self._card_bg, fg=self._text_secondary,
                 wraplength=420).pack(anchor="w", padx=16, pady=(0, 4))
        cached_hw = None
        if self._status and self._status.hardware_id:
            cached_hw = self._status.hardware_id
        if cached_hw:
            match = hw_id == cached_hw
            tk.Label(frame, text=f"Registered Hardware ID:", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
            tk.Label(frame, text=cached_hw, font=("Courier", 9),
                     bg=self._card_bg, fg=self._text_secondary,
                     wraplength=420).pack(anchor="w", padx=16, pady=(0, 4))
            status_color = self._success if match else self._warning
            status_text = "Matched" if match else "Mismatched"
            tk.Label(frame, text=f"Status: {status_text}", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=status_color).pack(anchor="w", padx=16, pady=(4, 8))
        tk.Label(frame, text="Hardware replacement requires administrator approval.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary,
                 wraplength=420).pack(anchor="w", padx=16, pady=(8, 4))
        tk.Label(frame, text="Please use Contact Support to request a hardware change.",
                 font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary,
                 wraplength=420).pack(anchor="w", padx=16, pady=(0, 12))
        tk.Button(frame, text="Close", command=dialog.destroy,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._text_secondary, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(padx=16, pady=(8, 12))
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
