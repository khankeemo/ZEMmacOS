"""Universal License Center - single customer experience for all license operations"""
import json
import os
import time
import traceback
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
    _external_logger = None

    @classmethod
    def set_external_logger(cls, callback):
        cls._external_logger = callback

    @classmethod
    def log(cls, event: str, detail: str = "") -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] {event}"
        if detail:
            entry += f" — {detail}"
        cls._entries.append(entry)
        print(entry)
        if cls._external_logger:
            try:
                cls._external_logger(event, detail)
            except Exception:
                pass

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
                 on_license_ready: Optional[Callable[[bool], None]] = None,
                 log_fn: Optional[Callable[[str, str, str, Optional[str]], None]] = None):
        self.config = _load_api_config() if config_path is None else self._load_config(config_path)
        self.hardware = HardwareDetector()
        self.cache = CacheManager(self.config)
        self.client = ApiClient(self.config, self.hardware, self.cache)
        self.engine = LicenseEngine(config_path, on_license_ready=self._on_engine_ready)
        self.on_license_ready = on_license_ready
        self._log_fn = log_fn
        if log_fn:
            def _sdk_log_forwarder(event: str, detail: str = ""):
                log_fn("SDK", "INFO", event, detail)
            LiveLog.set_external_logger(_sdk_log_forwarder)
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

    def _log(self, category: str, level: str, message: str, detail: Optional[str] = None):
        LiveLog.log(f"[{category}] [{level}] {message}", detail)
        if self._log_fn:
            try:
                self._log_fn(category, level, message, detail)
            except Exception:
                pass

    def _log_error(self, category: str, exc: Exception, context: str = ""):
        tb = traceback.format_exc()
        fname = "universal_license_center.py"
        func = ""
        lineno = 0
        import sys as _sys
        try:
            frame = _sys._getframe(1)
            func = frame.f_code.co_name
            lineno = frame.f_lineno
        except Exception:
            pass
        detail = f"Module: {fname} | Function: {func} | File: {fname} | Line: {lineno} | Exception: {exc}"
        self._log(category, "ERROR", context or str(exc), detail)
        if tb and tb != "NoneType: None\n":
            for tb_line in tb.strip().split("\n"):
                self._log(category, "ERROR", f"  {tb_line}")

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
        self._log("SDK", "INFO", "License Center started", "Application lock engaged")
        LiveLog.log("License Center started", "Application lock engaged")
        self._lock_application()
        self._log("SDK", "INFO", "Engine initializing", "Starting decision engine")
        LiveLog.log("Engine initializing", "Starting decision engine")
        self._status = self.engine.initialize()
        status = self._status.status if self._status else 'no_license'
        self._log("SDK", "INFO", f"Decision engine result: {status}")
        LiveLog.log("Decision engine result", f"Status: {status}")

        if self._status and self._status.valid:
            self._unlock_application()
            self._log("SDK", "INFO", "Valid license detected — launching application directly")
            LiveLog.log("License valid", "Launching application directly")
            return {'action': 'launch', 'status': self._status.to_dict(), 'unlocked': True}

        self._trial_consumed = self.cache.is_onboarding_complete()

        self._log("SDK", "INFO", "Opening Universal License Center")
        LiveLog.log("Opening Universal License Center", f"Status: {status}")
        return self._show_license_center()

    def _show_welcome(self) -> Dict[str, Any]:
        LiveLog.log("Opening Welcome Dialog")
        self._log("WELCOME", "INFO", "Opening Welcome Dialog")
        welcome = WelcomeDialog(
            client=self.client,
            hardware=self.hardware,
            cache=self.cache,
            product_name=self._product_name,
            log_fn=self._log_fn,
        )
        return welcome.show()

    def _show_license_center(self, trial_consumed: bool = False) -> Dict[str, Any]:
        LiveLog.log("Opening Universal License Center",
                     f"Status: {self._status.status if self._status else 'no_license'}, "
                     f"trial_consumed={trial_consumed}")
        self._log("WELCOME", "INFO", "Opening Universal License Center",
                   f"Status: {self._status.status if self._status else 'no_license'}, trial_consumed={trial_consumed}")
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
        self._refresh_hardware_display()
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
        self._status_detail.pack(anchor="w", padx=16, pady=(0, 4))

        self._license_footer = tk.Label(status_frame,
                                         text="(No hardware diagnostics except Hardware ID if needed for reference)",
                                         font=("Segoe UI", 8, "italic"),
                                         bg=self._card_bg, fg="#9ca3af",
                                         justify="left", wraplength=540)
        self._license_footer.pack(anchor="w", padx=16, pady=(0, 10))

        hw_frame = tk.Frame(main, bg=self._card_bg, bd=1, relief="solid",
                             highlightbackground=self._border)
        hw_frame.pack(fill="x", pady=(0, 16))
        tk.Label(hw_frame, text="Hardware Status",
                 font=("Segoe UI", 13, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 4))
        self._hw_detail = tk.Label(hw_frame, text="Detecting...",
                                    font=("Segoe UI", 10),
                                    bg=self._card_bg, fg=self._text_secondary,
                                    justify="left", wraplength=540)
        self._hw_detail.pack(anchor="w", padx=16, pady=(0, 4))

        self._hw_footer = tk.Label(hw_frame,
                                    text="Hardware information is collected for license binding.",
                                    font=("Segoe UI", 8, "italic"),
                                    bg=self._card_bg, fg="#9ca3af",
                                    justify="left", wraplength=540)
        self._hw_footer.pack(anchor="w", padx=16, pady=(0, 10))

        sep = tk.Frame(main, bg=self._border, height=1)
        sep.pack(fill="x", pady=(0, 12))

        btn_frame = tk.Frame(main, bg=self._bg)
        btn_frame.pack(fill="both", expand=True)

        status = self._status.status if self._status else 'no_license'
        is_valid = self._status.valid if self._status else False
        is_expired = status == 'expired'
        is_trial = status == 'trial'
        is_paid = status == 'active' and is_valid
        is_deactivated = status == 'deactivated'
        is_force_reactivation = status == 'force_reactivation'
        is_inactive = status == 'inactive'
        is_trial_consumed = status == 'trial_consumed'

        if is_trial:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_paid:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("View Hardware Status", self._view_hardware_status, self._text_secondary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_expired:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_deactivated:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_force_reactivation:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_inactive:
            support_label = f"Contact Support ({self._support_email})" if self._support_email else "Contact Support"
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                (support_label, self._contact_support, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        elif is_trial_consumed:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("Close", self._on_close, "#e5e7eb"),
            ]
        else:
            if self._trial_consumed:
                buttons = [
                    ("Activate License", self._activate_license, self._primary),
                    ("Renew License", self._renew_license_flow, self._primary),
                    ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                    ("Contact Support", self._contact_support, self._text_secondary),
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
                    ("Renew License", self._renew_license_flow, self._primary),
                    ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                    ("Contact Support", self._contact_support, self._text_secondary),
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

        if self._status.status in ('no_license', 'force_activation', 'unlicensed'):
            if self._trial_consumed:
                lines.append("This email has already used its free trial.")
                lines.append("Please Activate a License or Contact Sales.")
            else:
                lines.append("Status: NO LICENSE FOUND")
                lines.append("No active license or trial was found.")
                lines.append("Start a Free Trial or activate your license.")
            fg = self._warning
        elif self._status.status == 'inactive':
            lines.append("You are an existing customer, but your license is inactive.")
            lines.append("If you have a new or reactivated license, activate it now.")
            lines.append("Otherwise, please contact support.")
            if self._support_email:
                lines.append(f"Support: {self._support_email}")
            fg = self._error
        elif self._status.status == 'trial_consumed':
            lines.append("This email has already consumed its lifetime trial.")
            lines.append("Please activate a paid license or renew your existing license.")
            fg = self._warning
        elif self._status.status == 'deactivated':
            lines.append("Your license has been deactivated.")
            lines.append("Please contact your administrator.")
            fg = self._warning
        elif self._status.status == 'force_reactivation':
            lines.append("Unable to verify your license.")
            lines.append("Please contact support.")
            fg = self._error
        else:
            if self._status.customer_name:
                lines.append(f"Customer: {self._status.customer_name}")
            if self._status.customer_email:
                lines.append(f"Email: {self._status.customer_email}")
            if self._product_name:
                lines.append(f"Product: {self._product_name}")
            if self._status.plan:
                lines.append(f"Plan: {self._status.plan}")
            if self._status.expiry_date:
                lines.append(f"Expiry: {self._status.expiry_date}")
            if self._status.days_left > 0:
                lines.append(f"Remaining Days: {self._status.days_left}")
            if self._status.max_devices:
                lines.append(f"Device Limit: {self._status.max_devices}")
                remaining_acts = max(self._status.max_devices - (self._status.device_count or 0), 0)
                lines.append(f"Remaining Activations: {remaining_acts}")
            status_display = self._status.status.upper()
            lines.append(f"License Status: {status_display}")
            if self._status.valid:
                fg = self._success
            elif self._status.status == "trial":
                fg = self._warning
            elif self._status.status == "expired":
                fg = self._error
            else:
                fg = self._error

        self._status_detail.config(text="\n".join(lines), fg=fg)

    def _set_output(self, text: str, color: str = "#6b7280"):
        self._output_label.config(text=text, fg=color)

    def _refresh_hardware_display(self):
        hw_id = self.hardware.get_fingerprint()
        try:
            import socket
            device_name = socket.gethostname()
        except Exception:
            device_name = 'N/A'
        system_name = platform.node() or 'N/A'
        os_name = f"{platform.system()} {platform.release()}"
        binding_status = "Not Bound"
        lines = []
        lines.append("Hardware Status: Ready")
        lines.append(f"Binding Status: {binding_status}")
        lines.append(f"Hardware ID: {hw_id}")
        lines.append(f"Device Name: {device_name}")
        lines.append(f"System Name: {system_name}")
        lines.append(f"Operating System: {os_name}")
        lines.append(f"Runtime: {RUNTIME_TYPE}")
        lines.append(f"SDK Version: 1.0")
        self._hw_detail.config(text="\n".join(lines))

    def _start_trial(self):
        self._log("WELCOME", "INFO", "Opening Welcome (from Start Free Trial button)")
        LiveLog.log("Opening Welcome (from Start Free Trial button)")
        self._on_close()
        result = self._show_welcome()
        if result.get('trial_started'):
            self._log("WELCOME", "SUCCESS", "Trial started")
            self._status = self.engine.initialize()
            if self._status and self._status.valid:
                self._unlock_application()
                messagebox.showinfo("Trial Started",
                                    "Your free trial has been activated!",
                                    parent=self._root)
        elif result.get('trial_consumed'):
            self._log("WELCOME", "INFO", "Existing customer detected", "Trial already consumed — showing license center")
            LiveLog.log("Existing customer detected", "Trial already consumed — showing license center")
            self._status = self.engine.initialize()
            self._trial_consumed = True
            self._show_license_center(trial_consumed=True)
        elif result.get('closed'):
            self._log("WELCOME", "INFO", "Welcome dialog closed, returning to license center")
            self._show_license_center()

    def _show_restart_prompt(self, parent):
        self._log("UI", "INFO", "Waiting for Restart confirmation")
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
            self._log("UI", "INFO", "Restart button clicked")
            self._log("APP", "INFO", "Restart requested")
            self._log("APP", "INFO", "Closing application")
            restart_win.destroy()
            parent.destroy()
            import sys
            sys.exit(0)

        tk.Button(btn_frame, text="Restart Now", command=restart_now,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=16, pady=10, cursor="hand2").pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="Restart Later", command=restart_win.destroy,
                  font=("Segoe UI", 11),
                  bg=self._text_secondary, fg="white", relief="flat",
                  padx=16, pady=10, cursor="hand2").pack(side="left")

        restart_win.wait_window()

    def _show_activation_confirmation(self, parent, data, license_key):
        self._log("UI", "INFO", "Creating Activation Success dialog")
        confirm = tk.Toplevel(parent)
        confirm.title("Activation Successful")
        confirm.geometry("500x400")
        confirm.configure(bg=self._bg)
        confirm.transient(parent)
        confirm.grab_set()

        frame = tk.Frame(confirm, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Activation Successful", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._success).pack(anchor="w", padx=16, pady=(12, 8))

        info_items = [
            ("Customer Name", data.get('customer_name', 'N/A')),
            ("Product", self._product_name or data.get('product_name', 'N/A')),
            ("Plan", data.get('plan', 'N/A')),
            ("License Status", "Active"),
            ("Activation Date", data.get('activation_date', 'N/A')),
            ("Expiry Date", data.get('expiry_date', 'N/A')),
            ("Remaining Validity", f"{data.get('days_left', 0)} days"),
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
                  padx=16, pady=10, cursor="hand2").pack(padx=16, pady=(16, 12))

        confirm.wait_window()

    def _activate_license(self):
        self._log("ACTIVATION", "INFO", "Opening Activation dialog")
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
                self._log("VALIDATION", "WARNING", "License key is required")
                status_lbl.config(text="License key is required.", fg=self._error)
                return
            self._log("VALIDATION", "INFO", "Validate button clicked")
            status_lbl.config(text="Validating license...", fg=self._text_secondary)
            dialog.update()
            try:
                self._log("VALIDATION", "INFO", "Validation request started", f"key={key[:8]}...")
                result = self.engine.validate(key)
                self._log("VALIDATION", "INFO", "Validation response received")
                err_data = result.get('error', {})
                err_code = ''
                if isinstance(err_data, dict):
                    err_code = err_data.get('code', '')
                if result.get("success"):
                    self._log("VALIDATION", "SUCCESS", "Validation successful")
                    data = result.get("data", result)
                    validated["key"] = key
                    validated["data"] = data
                    validated["done"] = True

                    # Check if already activated on this device
                    if data.get('this_device_activated'):
                        self._log("VALIDATION", "INFO", "License already activated on this device")
                        status_lbl.config(
                            text="License already activated on this device. You can continue using the application.",
                            fg=self._success)
                        self.cache.set_onboarding_complete()
                        self.cache.save_license_key(key)
                        self.engine._license_key = key
                        self.engine._status = LicenseStatus(
                            valid=True, status='active',
                            expiry_date=data.get('expiry_date'),
                            days_left=data.get('days_left', 0),
                            plan=data.get('plan'), hardware_id=self.hardware.get_fingerprint(),
                            license_key=key,
                            customer_name=data.get('customer_name'),
                            customer_email=data.get('customer_email'),
                            customer_phone=data.get('customer_phone'),
                            customer_mobile=data.get('customer_mobile'),
                            message='License active'
                        )
                        self.engine._cache.set_license_status(self.engine._status.to_dict())
                        self.engine._cache.mark_has_ever_activated_paid_license()
                        self._unlock_application()
                        self._status = self.engine.get_status()
                        self._refresh_display()
                        self._refresh_hardware_display()
                        dialog.after(2000, dialog.destroy)
                        return

                    # Check device limit
                    active_devices = data.get('device_count', data.get('active_devices', 0))
                    max_devices = data.get('max_devices', 999)
                    remaining_activations = max(max_devices - active_devices, 0)
                    if active_devices >= max_devices:
                        self._log("VALIDATION", "WARNING", f"Device limit reached ({active_devices}/{max_devices})")
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
                    plan_info = f"Product: {data.get('product_name', 'N/A')} | Plan: {data.get('plan', 'N/A')} | Status: {data.get('status', 'N/A')} | Expires: {data.get('expiry_date', 'N/A')} | Days Left: {data.get('days_left', 0)} | Remaining Activations: {remaining_activations}"
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
                    self._log("VALIDATION", "ERROR", f"Validation failed: {err_code}", err_msg)
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
                self._log_error("VALIDATION", e, "Validation exception")
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        validate_btn = tk.Button(phase1, text="Validate License", command=do_validate,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=16, pady=10, cursor="hand2")
        validate_btn.pack(fill="x", padx=16, pady=(8, 12))

        def do_send_otp():
            email = validated["data"].get('customer_email', '')
            self._log("OTP", "INFO", "Sending activation OTP (manual resend)", email)
            self._on_send_otp_inline(email, status_lbl)

        def do_verify_otp():
            if otp_verified["done"]:
                return
            otp = otp_var.get().strip()
            if not otp:
                self._log("OTP", "WARNING", "OTP code is required")
                status_lbl.config(text="OTP code is required.", fg=self._error)
                return
            email = validated["data"].get('customer_email', '')
            if not email:
                self._log("OTP", "ERROR", "No customer email available for OTP verification")
                status_lbl.config(text="No customer email available.", fg=self._error)
                return
            self._log("OTP", "INFO", "OTP verification started", f"email={email}")
            status_lbl.config(text="Verifying OTP...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.client.verify_otp(email, otp)
                if result.get("success"):
                    self._log("OTP", "SUCCESS", "OTP verified successfully", f"email={email}")
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
                    self._log("OTP", "ERROR", "OTP verification failed", str(err))
                    status_lbl.config(text=f"OTP verification failed: {err}", fg=self._error)
            except Exception as e:
                self._log_error("OTP", e, "OTP verification exception")
                status_lbl.config(text=f"OTP error: {str(e)}", fg=self._error)

        otp_btn_frame = tk.Frame(otp_frame, bg=self._card_bg)
        send_otp_btn = tk.Button(otp_btn_frame, text="Send OTP", command=do_send_otp,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=16, pady=10, cursor="hand2")
        send_otp_btn.pack(side="left", padx=(0, 8))
        verify_otp_btn = tk.Button(otp_btn_frame, text="Verify OTP", command=do_verify_otp,
                                   font=("Segoe UI", 11, "bold"),
                                   bg=self._primary, fg="white", relief="flat",
                                   padx=16, pady=10, cursor="hand2")
        verify_otp_btn.pack(side="left")

        def do_activate():
            if not otp_verified["done"]:
                self._log("ACTIVATION", "WARNING", "Activate clicked but OTP not verified")
                status_lbl.config(text="Please verify OTP before activating.", fg=self._error)
                return
            key = validated["key"]
            self._log("ACTIVATION", "INFO", "Activation request started")
            status_lbl.config(text="Activating license...", fg=self._text_secondary)
            dialog.update()
            try:
                self._log("ACTIVATION", "INFO", "Waiting for API response")
                result = self.engine.activate(key)
                self._log("ACTIVATION", "INFO", "API response received")
                if result.get("success"):
                    if result.get('already_activated'):
                        self._log("ACTIVATION", "INFO", "Already activated on this device")
                        status_lbl.config(
                            text="License already activated on this device. You can continue using the application.",
                            fg=self._success)
                        dialog.after(2000, dialog.destroy)
                        return
                    self._log("ACTIVATION", "SUCCESS", "Activation successful")
                    data = result.get("data", result)
                    data["customer_name"] = validated["data"].get("customer_name", "")
                    data["customer_email"] = validated["data"].get("customer_email", "")
                    self._status = self.engine.get_status()
                    self._refresh_display()
                    self._refresh_hardware_display()
                    self._unlock_application()
                    dialog.destroy()
                    self._log("UI", "INFO", "Creating Activation Success dialog")
                    self._show_activation_confirmation(self._root, data, key)
                else:
                    err_data = result.get('error', {})
                    err_code = ''
                    if isinstance(err_data, dict):
                        err_code = err_data.get('code', '')
                    err = result.get("message", result.get("error", "Unknown error"))
                    self._log("ACTIVATION", "ERROR", f"Activation failed: {err_code}", err)
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
                self._log_error("ACTIVATION", e, "Activation exception")
                status_lbl.config(text=f"Activation error: {str(e)}", fg=self._error)

        activate_btn = tk.Button(activate_frame, text="Activate License", command=do_activate,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._success, fg="white", relief="flat",
                                 padx=16, pady=10, cursor="hand2")

        dialog.wait_window()

    def _on_send_otp_inline(self, email, status_lbl):
        if not email:
            self._log("OTP", "ERROR", "No customer email available for OTP")
            status_lbl.config(text="No customer email available for OTP.", fg=self._error)
            return
        self._log("OTP", "INFO", "Sending activation OTP", f"email={email}")
        status_lbl.config(text="Sending OTP...", fg=self._text_secondary)
        status_lbl.update()
        try:
            result = self.client.send_otp(email)
            if result.get("success"):
                self._log("OTP", "SUCCESS", "OTP sent successfully", f"email={email}")
                status_lbl.config(text=f"OTP sent to {email}. Enter code below.", fg=self._success)
            else:
                err = result.get('error', result.get('message', 'Failed to send OTP'))
                if isinstance(err, dict):
                    err = err.get('message', str(err))
                self._log("OTP", "ERROR", "OTP send failed", str(err))
                status_lbl.config(text=f"OTP send failed: {err}", fg=self._error)
        except Exception as e:
            self._log_error("OTP", e, "OTP send exception")
            status_lbl.config(text=f"OTP error: {str(e)}", fg=self._error)

    def _renew_license_flow(self):
        self._log("RENEWAL", "INFO", "Opening Renewal dialog")
        LiveLog.log("Opening Renewal", "Dialog displayed")
        dialog = tk.Toplevel(self._root)
        dialog.title("Renew License")
        dialog.geometry("620x700")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Renew License", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))

        # Phase 1: Enter License Key
        phase1 = tk.Frame(frame, bg=self._card_bg)
        phase1.pack(fill="x", padx=0, pady=0)

        tk.Label(phase1, text="Enter Last License Key *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 2))
        key_var = tk.StringVar()
        tk.Entry(phase1, textvariable=key_var, font=("Courier", 11),
                 relief="solid", bd=1).pack(fill="x", padx=16, pady=(0, 8))

        status_lbl = tk.Label(frame, text="", font=("Segoe UI", 9), bg=self._card_bg, wraplength=540)
        status_lbl.pack(padx=16, pady=(4, 0))

        # Phase 2: Customer Info (hidden until validated)
        info_frame = tk.Frame(frame, bg=self._card_bg)

        # Phase 3: Plan Selection (hidden until validated)
        plan_frame = tk.Frame(frame, bg=self._card_bg)
        selected_plan = tk.StringVar()
        validated_data: Dict[str, Any] = {}

        def do_validate():
            key = key_var.get().strip()
            if not key:
                status_lbl.config(text="License key is required.", fg=self._error)
                return
            status_lbl.config(text="Validating license...", fg=self._text_secondary)
            dialog.update()
            try:
                validate_result = self.engine.validate(key)
                if not validate_result.get('success') and validate_result.get('valid') is not True:
                    data = validate_result.get('data', validate_result)
                    err_code = validate_result.get('error', {}).get('code', '') or data.get('error', {}).get('code', '')
                    err_msg = validate_result.get('error', {}).get('message', '') or validate_result.get('message', '')
                    if err_code in ('LICENSE_REVOKED', 'LICENSE_INACTIVE', 'LICENSE_DELETED'):
                        status_lbl.config(text=f"License {err_code.replace('LICENSE_', '').lower()}. Contact support.", fg=self._error)
                        return
                    if err_code != 'LICENSE_EXPIRED':
                        status_lbl.config(text=f"Validation failed: {err_msg}", fg=self._error)
                        return
                    status_lbl.config(text="License expired. Proceeding with renewal...", fg=self._warning)
                else:
                    status_lbl.config(text="License valid. Loading information...", fg=self._success)
                dialog.update()

                validated_data.clear()
                validated_data.update(validate_result.get('data', validate_result))

                # Show customer/license info
                phase1.pack_forget()
                info_frame.pack(fill="x", padx=0, pady=8)

                info_fields = [
                    ("Customer Name", validated_data.get('customer_name', 'N/A')),
                    ("Email", validated_data.get('customer_email', 'N/A')),
                    ("Product", validated_data.get('product_name', 'N/A')),
                    ("Current Plan", validated_data.get('plan', 'N/A')),
                    ("Current Expiry", validated_data.get('expiry_date', 'N/A')),
                    ("License Status", validated_data.get('status', 'N/A')),
                    ("Days Remaining", str(validated_data.get('days_left', 0))),
                ]
                for label, value in info_fields:
                    row = tk.Frame(info_frame, bg=self._card_bg)
                    row.pack(fill="x", padx=16, pady=(1, 1))
                    tk.Label(row, text=label + ":", font=("Segoe UI", 10, "bold"),
                             bg=self._card_bg, fg=self._text_primary, width=18, anchor="w").pack(side="left")
                    tk.Label(row, text=value, font=("Segoe UI", 10),
                             bg=self._card_bg, fg=self._text_secondary, anchor="w").pack(side="left", fill="x")

                # Load plans
                status_lbl.config(text="Loading available plans...", fg=self._text_secondary)
                dialog.update()
                try:
                    plans_result = self.client.get_available_plans(key)
                    plans = []
                    if plans_result.get('success') and plans_result.get('plans'):
                        plans = plans_result['plans']
                except Exception:
                    plans = []

                if plans:
                    plan_frame.pack(fill="x", padx=0, pady=8)
                    for widget in plan_frame.winfo_children():
                        widget.destroy()

                    tk.Label(plan_frame, text="Available Paid Plans", font=("Segoe UI", 11, "bold"),
                             bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(4, 6))

                    plan_buttons = []
                    for plan in plans:
                        rb = tk.Radiobutton(plan_frame, text=f"{plan.get('name', 'N/A')} - {plan.get('description', plan.get('duration', ''))}",
                                            variable=selected_plan, value=plan.get('name', ''),
                                            font=("Segoe UI", 10), bg=self._card_bg,
                                            anchor="w", wraplength=480)
                        rb.pack(fill="x", padx=32, pady=(2, 2))
                        plan_buttons.append(rb)

                    keep_rb = tk.Radiobutton(plan_frame, text="Keep current plan",
                                             variable=selected_plan, value=validated_data.get('plan', ''),
                                             font=("Segoe UI", 10), bg=self._card_bg,
                                             anchor="w", wraplength=480)
                    keep_rb.pack(fill="x", padx=32, pady=(2, 6))
                    plan_buttons.append(keep_rb)
                else:
                    tk.Label(plan_frame, text="No alternative plans available. Current plan will be renewed.",
                             font=("Segoe UI", 10), bg=self._card_bg, fg=self._text_secondary).pack(
                        anchor="w", padx=16, pady=(4, 8))

                # Show Send button
                send_btn.pack(fill="x", padx=16, pady=(8, 12))

            except Exception as e:
                self._log_error("RENEWAL", e, "Renewal validation exception")
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        def do_send():
            key = key_var.get().strip()
            status_lbl.config(text="Sending renewal request...", fg=self._text_secondary)
            dialog.update()
            try:
                result = self.engine.create_communication(
                    category='renewal',
                    customer_email=validated_data.get('customer_email', ''),
                    customer_name=validated_data.get('customer_name', ''),
                    subject=f"License Renewal Request - {key}",
                    message=f"Renewal requested for license {key}.",
                    license_key=key,
                    hardware_id=self.hardware.get_fingerprint(),
                )
                if result.get('success'):
                    messagebox.showinfo("Request Submitted",
                                        "Your renewal request has been submitted.\nOur team will contact you.",
                                        parent=dialog)
                    dialog.destroy()
                elif result.get('queued'):
                    messagebox.showinfo("Request Queued",
                                        "Your renewal request has been queued.\nIt will be sent when connection is restored.",
                                        parent=dialog)
                    dialog.destroy()
                else:
                    err = result.get('message', result.get('error', 'Failed'))
                    status_lbl.config(text=f"Failed: {err}", fg=self._error)
            except Exception as e:
                self._log_error("RENEWAL", e, "Renewal send exception")
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        validate_btn = tk.Button(frame, text="Validate License", command=do_validate,
                                 font=("Segoe UI", 11, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=16, pady=10, cursor="hand2")
        validate_btn.pack(fill="x", padx=16, pady=(8, 4))

        send_btn = tk.Button(frame, text="Submit Renewal Request", command=do_send,
                             font=("Segoe UI", 11, "bold"),
                             bg=self._success, fg="white", relief="flat",
                             padx=16, pady=10, cursor="hand2")

        dialog.wait_window()

    def _reactivate_license(self):
        self._log("ACTIVATION", "INFO", "Opening Reactivation dialog")
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
                self._log_error("ACTIVATION", e, "Reactivation send exception")
                status_lbl.config(text=f"Error: {str(e)}", fg=self._error)

        tk.Button(frame, text="Submit Reactivation Request", command=do_send,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._warning, fg="white", relief="flat",
                  padx=16, pady=10, cursor="hand2").pack(fill="x", padx=16, pady=(8, 12))

        dialog.wait_window()

    def _view_hardware_status(self):
        hw_id = self.hardware.get_fingerprint()
        try:
            import socket
            device_name = socket.gethostname()
        except Exception:
            device_name = 'N/A'
        system_name = platform.node() or 'N/A'
        os_name = f"{platform.system()} {platform.release()}"
        dialog = tk.Toplevel(self._root)
        dialog.title("Hardware Status")
        dialog.geometry("500x400")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(frame, text="Hardware Status", font=("Segoe UI", 16, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", padx=16, pady=(12, 8))
        info_lines = [
            ("Hardware Status:", "Ready"),
            ("Binding Status:", "Not Bound"),
            ("Hardware ID:", hw_id),
            ("Device Name:", device_name),
            ("System Name:", system_name),
            ("Operating System:", os_name),
            ("Runtime:", RUNTIME_TYPE),
            ("SDK Version:", "1.0"),
        ]
        for label, value in info_lines:
            row = tk.Frame(frame, bg=self._card_bg)
            row.pack(fill="x", padx=16, pady=(2, 2))
            tk.Label(row, text=label, font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary, width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10),
                     bg=self._card_bg, fg=self._text_secondary, anchor="w").pack(side="left", fill="x", expand=True)
        tk.Button(frame, text="Close", command=dialog.destroy,
                  font=("Segoe UI", 11, "bold"),
                  bg=self._text_secondary, fg="white", relief="flat",
                  padx=16, pady=8, cursor="hand2").pack(pady=(16, 12))
        dialog.wait_window()

    def _contact_support(self):
        self._show_communication_dialog('support', 'Contact Support')

    def _sales_enquiry(self):
        self._show_communication_dialog('sales', 'Sales Enquiry')

    def _show_communication_dialog(self, category: str, title: str):
        dialog = tk.Toplevel(self._root)
        dialog.title(title)
        dialog.geometry("520x600")
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
                  padx=16, pady=10, cursor="hand2").pack(fill="x", padx=16, pady=(8, 20))

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
                          padx=16, pady=10, cursor="hand2").pack(
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
                          padx=16, pady=10, cursor="hand2").pack(
                    padx=12, pady=(0, 12))
        except Exception:
            pass
