"""Universal License Center - single customer experience for all license operations"""
import json
import os
import platform
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from .client import ApiClient, ApiError
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog
from .universal_success_dialog import SuccessDialog
from .live_log import LiveLog
from .single_instance import SingleInstance

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
                 on_license_ready: Optional[Callable[[bool], None]] = None,
                 log_fn: Optional[Callable[[str, str, str, Optional[str]], None]] = None,
                 initial_status: Optional[LicenseStatus] = None,
                 reentry: bool = False):
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
        self._status: Optional[LicenseStatus] = initial_status
        self._initialized = initial_status is not None
        self._root: Optional[tk.Toplevel] = None
        self._app_unlocked = False
        self._trial_consumed = False
        self._reentry = reentry

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
        return self._status.status in ('licensed', 'trial')

    def _unlock_application(self):
        self._app_unlocked = True
        if self.on_license_ready:
            self.on_license_ready(True)

    def _lock_application(self):
        self._app_unlocked = False
        if self.on_license_ready:
            self.on_license_ready(False)

    def show(self) -> Dict[str, Any]:
        _lock_path = os.path.join(tempfile.gettempdir(), 'UniversalLicenseCenter.opencode.lock')
        try:
            if os.path.exists(_lock_path):
                os.unlink(_lock_path)
        except Exception:
            pass
        self._instance_lock = SingleInstance('UniversalLicenseCenter')
        self._log("SDK", "INFO", "License Center started", "Application lock engaged")
        LiveLog.log("License Center started", "Application lock engaged")
        if not self._reentry:
            self._lock_application()

        # ULC must never run the Decision Engine.
        # Decision Engine runs once during LicenseEngine.initialize() in main.py.
        if not self._status:
            self._log("SDK", "WARNING", "ULC shown without pre-initialised status",
                      "Defaulting to no_license. Decision Engine must be called before ULC.")
            self._status = LicenseStatus(
                valid=False, status='no_license',
                hardware_id=self.hardware.get_fingerprint(),
                message='No license or trial was found. Start a Free Trial or activate your license.'
            )
        self._initialized = True

        status = self._status.status if self._status else 'no_license'
        self._log("SDK", "INFO", f"Using pre-initialised status: {status}")
        LiveLog.log("ULC using status", f"Status: {status}")

        if self._status and self._status.valid and not self._reentry:
            self._unlock_application()
            self._log("SDK", "INFO", "Valid license detected — launching application directly")
            LiveLog.log("License valid", "Launching application directly")
            return {'action': 'launch', 'status': self._status.to_dict(), 'unlocked': True}

        self._trial_consumed = self.cache.peek_onboarding_complete()

        self._log("SDK", "INFO", "Opening Universal License Center",
                  f"Status: {status}, trial_consumed={self._trial_consumed}")
        LiveLog.log("Opening Universal License Center",
                     f"Status: {status}, trial_consumed={self._trial_consumed}")
        return self._show_license_center(trial_consumed=self._trial_consumed)

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

    def _show_success_dialog(self, operation: str = "activation") -> None:
        if not self._status:
            return
        LiveLog.log("Showing Success Dialog", f"Operation: {operation}")
        SuccessDialog(
            parent=self._root,
            status=self._status,
            product_name=self._product_name,
            operation=operation,
            engine=self.engine,
            reentry=self._reentry,
        ).show()
        if self._reentry:
            self._on_ulc_close()

    def _show_error_dialog(self, title: str, message: str) -> None:
        LiveLog.log("Showing Error Dialog", f"{title}: {message}")
        messagebox.showerror(title, message, parent=self._root)

    def _destroy_ulc(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None

    def _show_license_center(self, trial_consumed: bool = False) -> Dict[str, Any]:
        # ULC must never run the Decision Engine.
        # LicenseEngine.initialize() already determined the status.
        # We use the pre-initialised initial_status passed from startup.
        pre_status = self._status.status if self._status else 'None'
        LiveLog.log("Opening Universal License Center",
                     f"Status: {pre_status}, "
                     f"trial_consumed={trial_consumed}")
        self._trial_consumed = trial_consumed
        self._root = tk.Toplevel()
        self._root.title("Universal License Center")
        self._root.geometry("680x880")
        self._root.minsize(600, 700)
        self._root.resizable(True, True)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_ulc_close)
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

        self._btn_frame = tk.Frame(main, bg=self._bg)
        self._btn_frame.pack(fill="both", expand=True)

        status = self._status.status if self._status else 'no_license'
        is_valid = self._status.valid if self._status else False
        is_expired = status == 'expired'
        is_trial = status == 'trial'
        is_paid = status == 'licensed' and is_valid
        is_deactivated = status == 'deactivated'
        is_force_reactivation = status == 'force_reactivation'
        is_inactive = status == 'inactive'
        is_trial_consumed = status == 'trial_consumed'

        refresh_btn = ("Refresh", self._refresh_ui, self._text_secondary)
        close_btn = ("Close", self._on_ulc_close, "#e5e7eb")
        exit_btn = ("Exit", self._on_ulc_close, "#e5e7eb")
        if self._reentry:
            exit_btn = close_btn

        if is_trial:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_paid:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("View Hardware Status", self._view_hardware_status, self._text_secondary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_expired:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Conversations", self._view_conversations, self._text_secondary),
                ("View Notifications", self._view_notifications, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_deactivated:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_force_reactivation:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                refresh_btn,
                close_btn,
            ]
        elif is_inactive:
            support_label = f"Contact Support ({self._support_email})" if self._support_email else "Contact Support"
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                (support_label, self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_trial_consumed:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        else:
            if self._trial_consumed:
                buttons = [
                    ("Activate License", self._activate_license, self._primary),
                    ("Renew License", self._renew_license_flow, self._primary),
                    ("Sales Enquiry", self._sales_enquiry, self._text_secondary),
                    ("Contact Support", self._contact_support, self._text_secondary),
                    refresh_btn,
                    exit_btn,
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
                    refresh_btn,
                    close_btn,
                ]

        for text, cmd, color in buttons:
            if color == "#e5e7eb":
                btn = tk.Button(self._btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11),
                                bg=color, fg=self._text_primary,
                                relief="flat", padx=12, pady=8, cursor="hand2")
            else:
                btn = tk.Button(self._btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11, "bold"),
                                bg=color, fg="white", relief="flat",
                                padx=12, pady=8, cursor="hand2")
            btn.pack(fill="x", pady=(0, 6))

        self._output_label = tk.Label(main, text="", font=("Segoe UI", 9),
                                       bg=self._bg, fg=self._text_secondary,
                                       wraplength=540, justify="left")
        self._output_label.pack(fill="x", pady=(8, 0))

    def _refresh_ui(self):
        if not self._root or not self._root.winfo_exists():
            return
        # ULC must never run the Decision Engine.
        # Refresh only rebuilds the UI from the current pre-initialised status.
        if self._btn_frame and self._btn_frame.winfo_exists():
            for child in self._btn_frame.winfo_children():
                child.destroy()
        self._rebuild_buttons()
        self._refresh_display()
        self._refresh_hardware_display()

    def _rebuild_buttons(self):
        if not self._btn_frame or not self._btn_frame.winfo_exists():
            return
        status = self._status.status if self._status else 'no_license'
        is_valid = self._status.valid if self._status else False
        is_expired = status == 'expired'
        is_trial = status == 'trial'
        is_paid = status == 'licensed' and is_valid
        is_deactivated = status == 'deactivated'
        is_force_reactivation = status == 'force_reactivation'
        is_inactive = status == 'inactive'
        is_trial_consumed = status == 'trial_consumed'

        refresh_btn = ("Refresh", self._refresh_ui, self._text_secondary)
        close_btn = ("Close", self._on_ulc_close, "#e5e7eb")
        exit_btn = ("Exit", self._on_ulc_close, "#e5e7eb")
        if self._reentry:
            exit_btn = close_btn

        if is_trial:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_paid:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                ("View Hardware Status", self._view_hardware_status, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_expired:
            buttons = [
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_deactivated:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                refresh_btn,
                close_btn,
            ]
        elif is_force_reactivation:
            buttons = [
                ("Contact Support", self._contact_support, self._primary),
                refresh_btn,
                close_btn,
            ]
        elif is_inactive:
            support_label = f"Contact Support ({self._support_email})" if self._support_email else "Contact Support"
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                (support_label, self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        elif is_trial_consumed:
            buttons = [
                ("Activate License", self._activate_license, self._primary),
                ("Renew License", self._renew_license_flow, self._primary),
                ("Contact Support", self._contact_support, self._text_secondary),
                refresh_btn,
                close_btn,
            ]
        else:
            if self._trial_consumed:
                buttons = [
                    ("Activate License", self._activate_license, self._primary),
                    ("Renew License", self._renew_license_flow, self._primary),
                    ("Contact Support", self._contact_support, self._text_secondary),
                    refresh_btn,
                    exit_btn,
                ]
            else:
                buttons = [
                    ("Start Free Trial", self._start_trial, self._success),
                    ("Activate License", self._activate_license, self._primary),
                    ("Renew License", self._renew_license_flow, self._primary),
                    ("Contact Support", self._contact_support, self._text_secondary),
                    refresh_btn,
                    close_btn,
                ]

        for text, cmd, color in buttons:
            if color == "#e5e7eb":
                btn = tk.Button(self._btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11),
                                bg=color, fg=self._text_primary,
                                relief="flat", padx=12, pady=8, cursor="hand2")
            else:
                btn = tk.Button(self._btn_frame, text=text, command=cmd,
                                font=("Segoe UI", 11, "bold"),
                                bg=color, fg="white", relief="flat",
                                padx=12, pady=8, cursor="hand2")
            btn.pack(fill="x", pady=(0, 6))

    def _on_ulc_close(self):
        try:
            self._root.destroy()
        except Exception:
            pass
        if hasattr(self, '_instance_lock'):
            try:
                self._instance_lock._release()
            except Exception:
                pass
        # Exit behaviour decided dynamically at close time based on actual license validity
        if self._status and self._status.valid:
            return
        if not self._app_unlocked:
            LiveLog.log("ULC closed", "Application locked - exiting process")
            try:
                sys.exit(0)
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
            lines.append("Status: INACTIVE")
            lines.append(self._status.message or "Your license is inactive. Please contact support.")
            fg = self._error
        elif self._status.status == 'expired':
            lines.append("Status: EXPIRED")
            lines.append(self._status.message or "Your license has expired. Please renew.")
            if self._status.expiry_date:
                lines.append(f"Expired on: {self._status.expiry_date}")
            fg = self._error
        elif self._status.status == 'trial_consumed':
            lines.append("Status: TRIAL CONSUMED")
            lines.append("You have already used your free trial.")
            lines.append("Please activate a paid license.")
            fg = self._warning
        elif self._status.status == 'force_reactivation':
            lines.append("Status: REACTIVATION REQUIRED")
            lines.append(self._status.message or "Please reactivate your license.")
            fg = self._error
        elif self._status.status == 'trial':
            lines.append("Status: TRIAL ACTIVE")
            display_product = self._status.product_name or self._product_name
            if display_product:
                lines.append(f"Product: {display_product}")
            if self._status.plan:
                lines.append(f"Plan: {self._status.plan}")
            if self._status.customer_name:
                lines.append(f"Customer: {self._status.customer_name}")
            if self._status.customer_email:
                lines.append(f"Email: {self._status.customer_email}")
            if self._status.customer_mobile:
                lines.append(f"Mobile: {self._status.customer_mobile}")
            if self._status.license_key:
                lines.append(f"License Key: {self._status.license_key}")
            if self._status.days_left is not None:
                lines.append(f"Days remaining: {self._status.days_left}")
            if self._status.expiry_date:
                lines.append(f"Expires: {self._status.expiry_date}")
            fg = self._success
        elif self._status.status in ('active', 'licensed'):
            lines.append("Status: ACTIVE")
            display_product = self._status.product_name or self._product_name
            if display_product:
                lines.append(f"Product: {display_product}")
            if self._status.plan:
                lines.append(f"Plan: {self._status.plan}")
            if self._status.customer_name:
                lines.append(f"Customer: {self._status.customer_name}")
            if self._status.customer_email:
                lines.append(f"Email: {self._status.customer_email}")
            if self._status.customer_mobile:
                lines.append(f"Mobile: {self._status.customer_mobile}")
            if self._status.license_key:
                lines.append(f"License Key: {self._status.license_key}")
            if self._status.days_left is not None:
                lines.append(f"Days remaining: {self._status.days_left}")
            if self._status.expiry_date:
                lines.append(f"Expires: {self._status.expiry_date}")
            fg = self._success
        else:
            lines.append(f"Status: {self._status.status.upper()}")
            if self._status.message:
                lines.append(self._status.message)
            fg = self._text_secondary

        self._status_detail.config(text="\n".join(lines), fg=fg)

    def _refresh_hardware_display(self):
        try:
            hw_id = self.hardware.get_fingerprint()
            sys_info = self.hardware.get_identifiers()
            lines = [f"Hardware ID: {hw_id[:16]}..."]
            if sys_info.get('cpu_id'):
                lines.append(f"CPU: {sys_info['cpu_id'][:16]}...")
            os_str = sys_info.get('os_info', platform.system())
            lines.append(f"OS: {os_str}")
            hw_valid = bool(hw_id and len(hw_id) > 8)
            self._hw_detail.config(
                text="\n".join(lines),
                fg=self._success if hw_valid else self._error
            )
        except Exception:
            self._hw_detail.config(text="Hardware detection failed", fg=self._error)

    # ====================================================================
    # Workflow Methods
    # ====================================================================

    def _activate_license(self):
        LiveLog.log("Activation started", "Opening license entry dialog")
        dialog = tk.Toplevel(self._root)
        dialog.title("Activate License")
        dialog.geometry("480x380")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.resizable(False, False)

        header = tk.Frame(dialog, bg=self._primary, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Activate License",
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Enter your license key:",
                 font=("Segoe UI", 11),
                 bg=self._card_bg, fg=self._text_secondary).pack(anchor="w", pady=(0, 8))
        key_entry = tk.Entry(main, font=("Consolas", 14), width=30,
                              relief="solid", bd=1, justify="center")
        key_entry.pack(fill="x", pady=(0, 6))
        key_entry.focus()

        hw_id = self.hardware.get_fingerprint()[:16] + "..."
        tk.Label(main, text=f"Hardware: {hw_id}",
                 font=("Segoe UI", 9), bg=self._card_bg, fg="#9ca3af").pack(anchor="w")

        status_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                bg=self._card_bg, fg=self._error, wraplength=420, justify="left")
        status_label.pack(fill="x", pady=(8, 0))

        def do_activate():
            key = key_entry.get().strip()
            if not key:
                status_label.config(text="Please enter a license key")
                return
            try:
                LiveLog.log("Activating license", f"Key: {key[:8]}...")
                result = self.engine.activate(key)
                if result.get('success') and result.get('data', {}).get('already_activated'):
                    LiveLog.log("Already activated", "This device already has this license")
                    messagebox.showinfo("Already Activated",
                                        "Already activated on this device. Continue using application.")
                    dialog.destroy()
                    return
                if result.get('success'):
                    status = self.engine.get_status()
                    if status:
                        self._status = status
                        self._initialized = True
                        self.cache.set_license_status(status.to_dict())
                        self.cache.mark_has_ever_activated_paid_license()
                    self.cache.set_onboarding_complete()
                    self._app_unlocked = True
                    LiveLog.log("Activation successful", f"Key: {key[:8]}...")
                    dialog.destroy()
                    self._show_success_dialog("activation")
                    self._refresh_ui()
                else:
                    err_data = result.get('data', result)
                    err_msg = err_data.get('message', '') or err_data.get('error', 'Activation failed')
                    LiveLog.log("Activation failed", str(err_msg))
                    status_label.config(text=str(err_msg))
            except Exception as e:
                LiveLog.log("Activation error", str(e))
                status_label.config(text=str(e))

        btn_frame = tk.Frame(main, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="Activate", command=do_activate,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=20, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))
        tk.Button(btn_frame, text="Cancel",
                  font=("Segoe UI", 11),
                  bg="#e5e7eb", fg=self._text_primary, relief="flat",
                  command=dialog.destroy, cursor="hand2",
                  padx=12, pady=4).pack(fill="x")
        dialog.wait_window()

    def _start_trial(self):
        LiveLog.log("Trial started", "Opening Welcome Dialog")
        self._log("TRIAL", "INFO", "Starting trial flow")
        result = self._show_welcome()
        if result.get('trial_started'):
            email = result.get('email', '')
            name = result.get('name', '')
            customer_data = result.get('customer_data', {})
            LiveLog.log("Trial activating via engine", f"email={email}, name={name}")
            eng_result = self.engine.start_trial(email, name, customer_data)
            if eng_result.get('success'):
                LiveLog.log("Trial started on server", "Engine state updated")
                status = self.engine.get_status()
                if status:
                    self._status = status
                    self._initialized = True
                    LiveLog.log("Engine status updated", f"status={status.status}, valid={status.valid}")
                self.cache.set_onboarding_complete()
                self.engine._cache.set_onboarding_complete()
                self._app_unlocked = True
                LiveLog.log("Trial activated", "Showing success dialog")
                self._show_success_dialog("trial")
                self._refresh_ui()
            else:
                err_msg = eng_result.get('message', 'Trial activation failed')
                LiveLog.log("Trial server response", err_msg)
                self._show_error_dialog("Trial Error", err_msg)
        elif result.get('customer_exists'):
            self._trial_consumed = True
            LiveLog.log("Customer exists", "Trial already consumed, showing ULC")
            self._status_detail.config(
                text="This email has already used its free trial. Please Activate a License or Contact Sales.",
                fg=self._warning
            )
        elif result.get('closed'):
            LiveLog.log("Welcome dialog closed", "User closed the welcome dialog")
            self._on_ulc_close()

    def _renew_license_flow(self):
        LiveLog.log("Renewal started", "Opening license key entry")
        dialog = tk.Toplevel(self._root)
        dialog.title("Renew License")
        dialog.geometry("480x380")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        header = tk.Frame(dialog, bg=self._primary, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Renew License",
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Enter your license key:",
                 font=("Segoe UI", 11),
                 bg=self._card_bg, fg=self._text_secondary).pack(anchor="w", pady=(0, 8))
        key_entry = tk.Entry(main, font=("Consolas", 14), width=30,
                              relief="solid", bd=1, justify="center")
        key_entry.pack(fill="x", pady=(0, 6))
        key_entry.focus()
        if self.engine.get_license_key():
            key_entry.insert(0, self.engine.get_license_key())

        status_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                bg=self._card_bg, fg=self._error, wraplength=420, justify="left")
        status_label.pack(fill="x", pady=(6, 0))

        def do_renew():
            key = key_entry.get().strip()
            if not key:
                status_label.config(text="Please enter a license key")
                return
            try:
                LiveLog.log("Renewal started", f"Key: {key[:8]}...")
                self.engine._license_key = key
                eng_result = self.engine.renew()
                if eng_result.get('success'):
                    status = self.engine.get_status()
                    if status:
                        self._status = status
                        self._initialized = True
                    LiveLog.log("Renewal API success", "Engine state updated")
                    dialog.destroy()
                    self._show_success_dialog("renewal")
                    self._refresh_ui()
                else:
                    err_msg = eng_result.get('message', 'Renewal failed')
                    LiveLog.log("Renewal API failed", err_msg)
                    status_label.config(text=err_msg)
                    dialog.destroy()
                    return
            except Exception as e:
                LiveLog.log("Renewal error", str(e))
                status_label.config(text=str(e))

        btn_frame = tk.Frame(main, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="Proceed with Renewal", command=do_renew,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=20, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))
        tk.Button(btn_frame, text="Cancel",
                  font=("Segoe UI", 11),
                  bg="#e5e7eb", fg=self._text_primary, relief="flat",
                  command=dialog.destroy, cursor="hand2",
                  padx=12, pady=4).pack(fill="x")
        dialog.wait_window()

    def _contact_support(self):
        LiveLog.log("Opening support request", "Showing support dialog")
        self._show_request_dialog("Support", "support")

    def _sales_enquiry(self):
        LiveLog.log("Opening sales enquiry", "Showing sales dialog")
        self._show_request_dialog("Sales Enquiry", "sales")

    def _show_request_dialog(self, title: str, category: str, parent: Optional[tk.Widget] = None):
        dialog = tk.Toplevel(parent or self._root)
        dialog.title(title)
        dialog.geometry("580x633")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()

        header = tk.Frame(dialog, bg=self._primary, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=title,
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=16)
        main.pack(fill="both", expand=True)

        status = self._status

        def _add_field_row(parent_frame, label_text, entry_var, default_value):
            row = tk.Frame(parent_frame, bg=self._card_bg)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label_text}:", font=("Segoe UI", 10),
                     fg=self._text_secondary, bg=self._card_bg, width=14, anchor="w").pack(side="left")
            entry = tk.Entry(row, font=("Segoe UI", 10), relief="solid", bd=1,
                             textvariable=entry_var)
            entry.pack(side="left", fill="x", expand=True)
            if default_value:
                entry_var.set(default_value)
            return entry

        def _add_label_row(parent_frame, label_text, value_text):
            row = tk.Frame(parent_frame, bg=self._card_bg)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label_text}:", font=("Segoe UI", 10),
                     fg=self._text_secondary, bg=self._card_bg, width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value_text, font=("Segoe UI", 10, "bold"),
                     fg=self._text_primary, bg=self._card_bg, anchor="w").pack(side="left", fill="x", expand=True)

        customer_name_var = tk.StringVar()
        customer_email_var = tk.StringVar()

        _add_field_row(main, "Name", customer_name_var,
                       status.customer_name if status else "")
        _add_field_row(main, "Email", customer_email_var,
                       status.customer_email if status else "")
        _add_label_row(main, "Product", self._product_name)
        if status and status.plan:
            _add_label_row(main, "Plan", status.plan)
        if status and status.license_key:
            display_key = status.license_key[:8] + "..." if len(status.license_key) > 8 else status.license_key
            _add_label_row(main, "License Key", display_key)

        sep = tk.Frame(main, bg=self._border, height=1)
        sep.pack(fill="x", pady=12)

        tk.Label(main, text="Message:",
                 font=("Segoe UI", 11),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", pady=(0, 6))
        msg_text = tk.Text(main, font=("Segoe UI", 11), height=6,
                           relief="solid", bd=1)
        msg_text.pack(fill="x", pady=(0, 10))
        msg_text.focus()

        status_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                bg=self._card_bg, fg=self._success)
        status_label.pack(pady=(0, 5))

        def do_send():
            message = msg_text.get("1.0", "end-1c").strip()
            name = customer_name_var.get().strip()
            email = customer_email_var.get().strip()
            if not message:
                status_label.config(text="Please enter a message", fg=self._error)
                return
            if not name:
                status_label.config(text="Please enter your name", fg=self._error)
                return
            if not email or "@" not in email:
                status_label.config(text="Please enter a valid email address", fg=self._error)
                return
            try:
                LiveLog.log(f"Sending {category} request", f"Category: {category}")
                result = self.engine.create_communication(
                    category=category,
                    customer_email=email,
                    customer_name=name,
                    message=message,
                    license_key=status.license_key if status else '',
                    hardware_id=self.hardware.get_fingerprint(),
                    sdk_version=SDK_VERSION,
                    runtime_type=RUNTIME_TYPE,
                )
                if result.get('success'):
                    status_label.config(text="Message sent successfully!", fg=self._success)
                    LiveLog.log(f"{category} request sent", "Success")
                    dialog.after(1500, dialog.destroy)
                else:
                    if result.get('queued'):
                        status_label.config(text="Message queued - will send when online.", fg=self._warning)
                    else:
                        err = result.get('message', 'Failed to send message')
                        status_label.config(text=str(err), fg=self._error)
            except ApiError as e:
                LiveLog.log(f"{category} request error", f"{e.status_code}: {e.message}")
                status_label.config(text=e.message, fg=self._error)
            except Exception as e:
                LiveLog.log(f"{category} request error", str(e))
                status_label.config(text=str(e), fg=self._error)

        btn_frame = tk.Frame(main, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(8, 0))
        tk.Button(btn_frame, text="Send", command=do_send,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=20, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))
        tk.Button(btn_frame, text="Cancel",
                  font=("Segoe UI", 11),
                  bg="#e5e7eb", fg=self._text_primary, relief="flat",
                  command=dialog.destroy, cursor="hand2",
                  padx=12, pady=4).pack(fill="x")
        dialog.wait_window()

    def _view_hardware_status(self):
        LiveLog.log("Viewing hardware status")
        status = self.engine.view_hardware_status()
        msg = f"Current Hardware ID: {status.get('current_hardware_id', 'N/A')[:16]}..."
        if status.get('registered_hardware_id'):
            msg += f"\nRegistered Hardware ID: {status['registered_hardware_id'][:16]}..."
            msg += f"\nMatch: {status.get('matched', False)}"
        msg += f"\n\n{status.get('message', '')}"
        messagebox.showinfo("Hardware Status", msg, parent=self._root)

    def _view_conversations(self):
        LiveLog.log("Viewing conversations")
        email = self._status.customer_email if self._status else ''
        if not email:
            messagebox.showinfo("Conversations", "No customer email available.", parent=self._root)
            return
        result = self.engine.list_conversations(email)
        conversations = result.get('conversations', [])
        if not conversations:
            messagebox.showinfo("Conversations", "No conversations found.", parent=self._root)
            return
        msg = "\n\n".join([
            f"ID: {c.get('id', 'N/A')}\nCategory: {c.get('category', 'N/A')}\nStatus: {c.get('status', 'N/A')}\nSubject: {c.get('subject', 'N/A')}\nCreated: {c.get('created_at', 'N/A')}"
            for c in conversations[:10]
        ])
        messagebox.showinfo("Conversations", msg, parent=self._root)

    def _view_notifications(self):
        LiveLog.log("Viewing notifications")
        email = self._status.customer_email if self._status else ''
        if not email:
            messagebox.showinfo("Notifications", "No customer email available.", parent=self._root)
            return
        result = self.engine.get_notifications(email)
        notifications = result.get('notifications', [])
        if not notifications:
            messagebox.showinfo("Notifications", "No notifications found.", parent=self._root)
            return
        msg = "\n\n".join([
            f"{n.get('title', 'N/A')}\n{n.get('message', 'N/A')}\n{n.get('created_at', 'N/A')}"
            for n in notifications[:10]
        ])
        messagebox.showinfo("Notifications", msg, parent=self._root)
