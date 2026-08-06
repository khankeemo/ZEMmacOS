"""Universal License Center - single customer experience for all license operations

UI LAYER ONLY (SDK V2): no business logic, no API calls, no cache writes,
no events. Everything is delegated to LicenseEngine; the ULC subscribes to
LicenseStatusChanged and re-renders from the event payload.
"""
import json
import os
import platform
import sys
import tkinter as tk
import webbrowser
from typing import Any, Callable, Dict, Optional

from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .welcome import WelcomeDialog
from .universal_success_dialog import SuccessDialog
from .live_log import LiveLog
from .single_instance import SingleInstance
from .validation import OTP_INVALID_MESSAGE
from .universal_email_dialog import UniversalEmailDialog
from .dialog_manager import DialogManager
from .event_bus import EventBus
from .workflow_progress import WorkflowProgress, format_timer

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
        self._events_bound = False

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

        self._trial_consumed = self.engine.is_onboarding_complete()

        self._log("SDK", "INFO", "Opening Universal License Center",
                  f"Status: {status}, trial_consumed={self._trial_consumed}")
        LiveLog.log("Opening Universal License Center",
                     f"Status: {status}, trial_consumed={self._trial_consumed}")
        return self._show_license_center(trial_consumed=self._trial_consumed)

    def _show_welcome(self) -> Dict[str, Any]:
        LiveLog.log("Opening Welcome Dialog")
        self._log("WELCOME", "INFO", "Opening Welcome Dialog")
        welcome = WelcomeDialog(
            engine=self.engine,
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
        DialogManager.error(self._root, title, message)

    def _show_inactive_license_dialog(self) -> None:
        """Shown when the backend confirms the license was removed
        (deleted / inactive / revoked / not found). Stale values are already
        cleared by the engine; the customer can activate a valid license or
        generate a request."""
        if getattr(self, '_inactive_dialog_open', False):
            return
        self._inactive_dialog_open = True
        parent = self._root if (self._root and self._root.winfo_exists()) else None
        dialog = tk.Toplevel(parent) if parent else tk.Toplevel()
        dialog.title("Inactive License")
        dialog.geometry("460x330")
        dialog.configure(bg=self._bg)
        dialog.resizable(False, False)
        if parent:
            dialog.transient(parent)
            dialog.grab_set()

        def cleanup():
            self._inactive_dialog_open = False
            try:
                dialog.destroy()
            except Exception:
                pass

        dialog.protocol("WM_DELETE_WINDOW", cleanup)

        header = tk.Frame(dialog, bg=self._error, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="License Inactive",
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._error).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=28, pady=22)
        main.pack(fill="both", expand=True)

        tk.Label(main,
                 text="This license is inactive or no longer exists.\n"
                      "Please contact your administrator or activate using a valid license.",
                 font=("Segoe UI", 11), fg=self._text_primary,
                 bg=self._card_bg, justify="center", wraplength=400).pack(pady=(4, 18))

        btn_frame = tk.Frame(main, bg=self._card_bg)
        btn_frame.pack(fill="x")

        def do_activate():
            cleanup()
            self._activate_license()

        def do_generate_request():
            cleanup()
            UniversalEmailDialog(self, "Generate Request", "general").show()

        tk.Button(btn_frame, text="Activate License", command=do_activate,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(fill="x", pady=(0, 8))
        tk.Button(btn_frame, text="Generate Request", command=do_generate_request,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._success, fg="white", relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(fill="x")

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
        self._bind_events()
        self._build_ui()
        self._refresh_display()
        self._refresh_hardware_display()
        if self._status and self._status.status == 'inactive':
            self._root.after(100, self._show_inactive_license_dialog)
        self._center_window()
        self._root.wait_window()
        return {"status": self._status.to_dict() if self._status else None,
                "unlocked": self._app_unlocked,
                "trial_consumed": trial_consumed}

    # ====================================================================
    # Event subscription (Phase 3 — LicenseStatusChanged is the single channel)
    # ====================================================================

    def _bind_events(self):
        if self._events_bound:
            return
        EventBus.subscribe_status_changed(self._on_status_changed)
        EventBus.subscribe("workflow.progress", self._on_workflow_progress)
        self._events_bound = True

    def _unbind_events(self):
        if not self._events_bound:
            return
        EventBus.unsubscribe_status_changed(self._on_status_changed)
        EventBus.unsubscribe("workflow.progress", self._on_workflow_progress)
        self._events_bound = False

    def _on_status_changed(self, status: Optional[LicenseStatus]):
        """Single UI refresh path — every engine state mutation converges here.
        The ULC never polls or refreshes itself after workflows."""
        self._status = status or self._status
        self._initialized = True
        if not self._root or not self._root.winfo_exists():
            return
        self._refresh_display()
        self._rebuild_buttons()

    def _on_workflow_progress(self, stage: str, detail: str = ""):
        if not self._root or not self._root.winfo_exists():
            return
        label = getattr(self, '_output_label', None)
        if label is not None:
            try:
                text = stage if not detail else f"{stage} — {detail}"
                label.config(text=text, fg=self._text_secondary)
            except Exception:
                pass

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

        self._render_buttons()

        self._output_label = tk.Label(main, text="", font=("Segoe UI", 9),
                                       bg=self._bg, fg=self._text_secondary,
                                       wraplength=540, justify="left")
        self._output_label.pack(fill="x", pady=(8, 0))

    def _render_buttons(self):
        """One button builder for every status — used by _build_ui and
        _rebuild_buttons so the same state can never render two layouts."""
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

    def _refresh_from_server(self) -> Optional[LicenseStatus]:
        """Fetch the latest backend state (Refresh / Startup). Single call via
        the engine; the LicenseStatusChanged event re-renders the UI exactly
        once. A server-confirmed removal (deleted / inactive / revoked / not
        found) clears stale license values and triggers the Inactive License
        dialog. Returns the refreshed status (or current when offline)."""
        if not self.engine:
            return self._status
        try:
            new_status = self.engine.refresh()
        except Exception as e:
            LiveLog.log("refresh.error", f"Refresh failed: {e}")
            return self._status
        if new_status is None:
            LiveLog.log("refresh.offline", "Backend unreachable - keeping current status")
            return self._status
        LiveLog.log("refresh.success", f"License refreshed from server (status: {new_status.status})")
        prev_valid = bool(self._status and self._status.valid)
        self._status = new_status
        self._initialized = True
        if prev_valid and not new_status.valid:
            LiveLog.log("License removed on server",
                        f"Server reports {new_status.status} - stale values cleared")
        if new_status.status == 'inactive':
            root = self._root if (self._root and self._root.winfo_exists()) else None
            if root:
                root.after(100, self._show_inactive_license_dialog)
        return new_status

    def _refresh_ui(self):
        try:
            if not self._root or not self._root.winfo_exists():
                return
        except Exception:
            return
        # One refresh: the engine re-syncs with the backend once and fires
        # LicenseStatusChanged exactly once; _on_status_changed re-renders.
        try:
            LiveLog.log("refresh.start", "Refreshing license with the server")
            self._refresh_from_server()
        except Exception:
            return
        self._refresh_hardware_display()

    def _rebuild_buttons(self):
        if not self._btn_frame or not self._btn_frame.winfo_exists():
            return
        for child in self._btn_frame.winfo_children():
            child.destroy()
        self._render_buttons()

    def _on_ulc_close(self):
        self._unbind_events()
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
        LiveLog.log("Activation started", "Opening pre-activation dialog")
        self._show_pre_activation_dialog("activate")

    def _renew_license_flow(self):
        LiveLog.log("Renewal started", "Opening pre-renewal dialog")
        self._show_pre_activation_dialog("renew")

    def _show_pre_activation_dialog(self, mode: str):
        """Pre-activation / pre-renewal choice dialog (commercial standard):

        [ Buy License ]      → opens the software store (URL derived from config)
        [ Existing License ] → continues with activation / renewal workflow
        """
        is_activate = mode == 'activate'
        title = "Activate License" if is_activate else "Renew License"

        dialog = tk.Toplevel(self._root)
        dialog.title(title)
        dialog.geometry("440x300")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.resizable(False, False)

        header = tk.Frame(dialog, bg=self._primary, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=title,
                 font=("Segoe UI", 16, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=18)
        main.pack(fill="both", expand=True)

        tk.Label(main,
                 text="How would you like to continue?",
                 font=("Segoe UI", 12, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(pady=(0, 6))
        tk.Label(main,
                 text="Buy a new license from the software store,\n"
                      "or continue with an existing license.",
                 font=("Segoe UI", 10),
                 bg=self._card_bg, fg=self._text_secondary,
                 justify="center", wraplength=360).pack(pady=(0, 14))

        def do_buy():
            self._open_store()

        def do_existing():
            dialog.destroy()
            self._show_key_flow_dialog(mode)

        tk.Button(main, text="Buy License", command=do_buy,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(fill="x", pady=(0, 8))
        tk.Button(main, text="Existing License", command=do_existing,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._success, fg="white", relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(fill="x")

        dialog.wait_window()

    def _open_store(self):
        """Open the software store in the default browser.

        The store URL comes from one central configuration location
        (config/api-config.json → store.url)."""
        from .config import get_store_url
        url = get_store_url(self.config)
        if not url:
            LiveLog.log("Software store URL not configured", "store.url is empty in api-config.json")
            return
        LiveLog.log("Opening software store", url)
        try:
            webbrowser.open(url)
        except Exception as e:
            LiveLog.log("Failed to open store", str(e))

    def _show_key_flow_dialog(self, mode: str):
        """Mandatory activation/renewal workflow (Rule 0A-4):

        Enter License Key → Validate License API
          → fail: exact backend message, NO OTP, NO Activate
          → pass: Send OTP → Verify OTP → Enable Activate/Renew
        """
        is_activate = mode == 'activate'
        title = "Activate License" if is_activate else "Renew License"
        final_label = "Activate License" if is_activate else "Proceed with Renewal"

        dialog = tk.Toplevel(self._root)
        dialog.title(title)
        dialog.geometry("560x640")
        dialog.configure(bg=self._bg)
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.resizable(False, False)

        header = tk.Frame(dialog, bg=self._primary, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=title,
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=18)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Enter your license key:",
                 font=("Segoe UI", 11),
                 bg=self._card_bg, fg=self._text_secondary).pack(anchor="w", pady=(0, 6))
        key_entry = tk.Entry(main, font=("Consolas", 13), width=30,
                             relief="solid", bd=1, justify="center")
        key_entry.pack(fill="x", pady=(0, 6))
        if self.engine and self.engine.get_license_key():
            key_entry.insert(0, self.engine.get_license_key())
        key_entry.focus()

        hw_id = self.hardware.get_fingerprint()[:16] + "..."
        tk.Label(main, text=f"Hardware: {hw_id}",
                 font=("Segoe UI", 9), bg=self._card_bg, fg="#9ca3af").pack(anchor="w")

        status_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                bg=self._card_bg, fg=self._error,
                                wraplength=500, justify="left")
        status_label.pack(fill="x", pady=(8, 0))

        details_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                 bg=self._card_bg, fg=self._text_primary,
                                 justify="left", wraplength=500)
        details_label.pack(fill="x", pady=(6, 0))

        validate_btn = tk.Button(main, text="Validate License",
                                 font=("Segoe UI", 12, "bold"),
                                 bg=self._primary, fg="white", relief="flat",
                                 padx=16, pady=8, cursor="hand2")
        validate_btn.pack(fill="x", pady=(10, 4))

        otp_row = tk.Frame(main, bg=self._card_bg)
        otp_row.pack(fill="x", pady=(4, 0))
        otp_entry = tk.Entry(otp_row, font=("Segoe UI", 13), relief="solid",
                             bd=1, justify="center", width=10)
        otp_entry.pack(side="left", fill="x", expand=True)
        otp_entry.config(state='disabled')
        send_otp_btn = tk.Button(otp_row, text="Send OTP",
                                 font=("Segoe UI", 10, "bold"),
                                 bg=self._text_secondary, fg="white",
                                 relief="flat", state='disabled',
                                 padx=10, pady=6, cursor="hand2")
        send_otp_btn.pack(side="left", padx=(8, 0))
        verify_btn = tk.Button(otp_row, text="Verify OTP",
                               font=("Segoe UI", 10, "bold"),
                               bg=self._success, fg="white", relief="flat",
                               state='disabled', padx=10, pady=6, cursor="hand2")
        verify_btn.pack(side="left", padx=(8, 0))

        final_btn = tk.Button(main, text=final_label,
                              font=("Segoe UI", 12, "bold"),
                              bg=self._primary, fg="white", relief="flat",
                              state='disabled', padx=16, pady=8, cursor="hand2")
        final_btn.pack(fill="x", pady=(10, 4))

        tk.Button(main, text="Cancel", font=("Segoe UI", 11),
                  bg="#e5e7eb", fg=self._text_primary, relief="flat",
                  command=dialog.destroy, cursor="hand2",
                  padx=12, pady=4).pack(fill="x")

        state = {"validated": False, "otp_verified": False, "email": "",
                 "timer_id": None, "otp_expires_at": 0.0}

        def _set_status(text, fg):
            status_label.config(text=text, fg=fg)

        def _update_otp_timer():
            if state["timer_id"] is not None:
                try:
                    dialog.after_cancel(state["timer_id"])
                except Exception:
                    pass
                state["timer_id"] = None
            import time as _time
            remaining = int(state["otp_expires_at"] - _time.time())
            if remaining <= 0:
                state["otp_expires_at"] = 0.0
                _set_status("OTP expired. Request a new OTP.", self._error)
                otp_entry.config(state='disabled')
                verify_btn.config(state='disabled')
                send_otp_btn.config(state='normal', text='Send OTP')
                return
            _set_status(f"OTP sent — expires in {format_timer(remaining)}",
                        self._success)
            state["timer_id"] = dialog.after(1000, _update_otp_timer)

        def do_validate():
            key = key_entry.get().strip()
            if not key:
                _set_status("Please enter a license key", self._error)
                return
            validate_btn.config(state='disabled', text='Validating...')
            _set_status("Validating license with the server...", self._text_secondary)
            result = self.engine.validate_license_key(key)

            lic = result.get('license') or {}
            cust = result.get('customer') or {}
            err = result.get('error') or {}
            api_status = result.get('status', '')

            if result.get('already_activated'):
                LiveLog.log("Already activated", "This device already has this license")
                DialogManager.info(dialog, "Already Activated",
                                   "Already activated on this device. Continue using application.")
                try:
                    self.engine.refresh()
                except Exception:
                    pass
                status = self.engine.get_status()
                if status:
                    self._status = status
                    self._initialized = True
                if self._status and self._status.valid:
                    self._app_unlocked = True
                dialog.destroy()
                return

            if not is_activate and result.get('new_customer'):
                _set_status("You're a new customer. Please activate your license first.", self._warning)
                validate_btn.config(state='normal', text='Validate License')
                otp_entry.config(state='disabled')
                send_otp_btn.config(state='disabled')
                verify_btn.config(state='disabled')
                final_btn.config(state='normal', text='Activate License',
                                 command=lambda: (dialog.destroy(), self._activate_license()))
                details_label.config(text="")
                state["validated"] = False
                return

            if not result.get('validated'):
                msg = result.get('message', 'License validation could not be completed. '
                                            'Please check the license key and try again, or contact support.')
                LiveLog.log("operation.error", f"License validation failed: {msg}")
                _set_status(str(msg), self._error)
                validate_btn.config(state='normal', text='Validate License')
                otp_entry.config(state='disabled')
                send_otp_btn.config(state='disabled')
                verify_btn.config(state='disabled')
                final_btn.config(state='disabled')
                details_label.config(text="")
                state["validated"] = False
                return

            state["validated"] = True
            state["otp_verified"] = False
            state["email"] = cust.get('email', '')
            validate_btn.config(state='normal', text='Validate License')
            send_otp_btn.config(state='normal')
            verify_btn.config(state='disabled')
            otp_entry.config(state='disabled')
            otp_entry.delete(0, 'end')
            final_btn.config(state='disabled')
            lines = []
            if cust.get('name'):
                lines.append(f"Customer: {cust['name']}")
            if state["email"]:
                lines.append(f"Email: {state['email']}")
            if self._product_name:
                lines.append(f"Product: {self._product_name}")
            if lic.get('plan'):
                lines.append(f"Plan: {lic['plan']}")
            if lic.get('expiry_date'):
                lines.append(f"Expiry: {lic['expiry_date']}")
            if lic.get('days_remaining') is not None:
                lines.append(f"Days remaining: {lic['days_remaining']}")
            elif lic.get('days_left') is not None:
                lines.append(f"Days remaining: {lic['days_left']}")
            if not is_activate:
                try:
                    renewal_info = self.engine.verify_license_for_renewal(key)
                    if renewal_info.get('success') and renewal_info.get('valid'):
                        lines.append("")
                        lines.append("RENEWAL DETAILS")
                        if renewal_info.get('is_expired'):
                            lines.append("Status: EXPIRED — eligible for renewal")
                        if renewal_info.get('days_left') is not None:
                            lines.append(f"Current days left: {renewal_info['days_left']}")
                        available = renewal_info.get('available_plans') or []
                        if available:
                            lines.append("Available renewal options:")
                            for p in available:
                                mark = " (current)" if p.get('is_current_plan') else ""
                                lines.append(f"  - {p.get('name', '')} — {p.get('duration', '')}{mark}")
                except Exception:
                    pass
            if not lines:
                lines.append("License validated successfully.")
            details_label.config(text="\n".join(lines))
            _set_status("License validated. Send the OTP to continue.", self._success)

        def do_send_otp():
            if not state["validated"]:
                return
            email = state["email"]
            if not email:
                _set_status("No registered email was found for this license.", self._error)
                return
            send_otp_btn.config(state='disabled', text='Sending...')
            _set_status("Sending OTP...", self._text_secondary)
            try:
                result = self.engine.send_otp(email)
            except Exception as e:
                _set_status(str(e), self._error)
                send_otp_btn.config(state='normal', text='Send OTP')
                return
            if result.get('success'):
                import time as _time
                state["otp_expires_at"] = _time.time() + int(result.get('expires_in', 300))
                otp_entry.config(state='normal')
                verify_btn.config(state='normal')
                send_otp_btn.config(state='normal', text='Resend OTP')
                _update_otp_timer()
            else:
                msg = result.get('message') or result.get('error') or 'Failed to send OTP'
                _set_status(str(msg), self._error)
                send_otp_btn.config(state='normal', text='Send OTP')

        def do_verify_otp():
            if not state["validated"]:
                return
            otp = otp_entry.get().strip()
            if not otp or len(otp) < 4:
                _set_status("Enter the OTP code", self._error)
                return
            verify_btn.config(state='disabled', text='Verifying...')
            try:
                result = self.engine.verify_otp(state["email"], otp)
            except Exception as e:
                _set_status(str(e), self._error)
                verify_btn.config(state='normal', text='Verify OTP')
                return
            if result.get('success'):
                state["otp_verified"] = True
                verify_btn.config(state='normal', text='Verify OTP')
                otp_entry.config(state='disabled')
                final_btn.config(state='normal')
                _set_status("OTP verified. Proceed with the final step.", self._success)
            else:
                otp_entry.delete(0, 'end')
                _set_status(OTP_INVALID_MESSAGE, self._error)
                verify_btn.config(state='normal', text='Verify OTP')
                otp_entry.focus()

        def do_final():
            if not state["validated"] or not state["otp_verified"]:
                return
            key = key_entry.get().strip()
            final_btn.config(state='disabled', text='Processing...')
            try:
                if is_activate:
                    result = self.engine.activate(key)
                    operation = "activation"
                else:
                    result = self.engine.renew(license_key=key)
                    operation = "renewal"
            except Exception as e:
                _set_status(str(e), self._error)
                final_btn.config(state='normal', text=final_label)
                return
            if result.get('success') or result.get('already_activated'):
                status = self.engine.get_status()
                if status:
                    self._status = status
                    self._initialized = True
                self._app_unlocked = True
                LiveLog.log("general.unlocked", f"{operation} completed — application unlocked")
                dialog.destroy()
                self._show_success_dialog(operation)
            else:
                err = result.get('error') or result.get('data') or result
                msg = err.get('message') if isinstance(err, dict) else str(err)
                # Rule 5 & 8: surface the real server message verbatim; only when
                # the server supplied no message at all use an actionable local
                # phrasing (what / why / next) rather than a bare "failed".
                if not msg:
                    action = "Activation" if is_activate else "Renewal"
                    msg = (f"{action} could not be completed. "
                           f"The server did not return a reason. Please contact support "
                           f"at {self._support_email or 'your provider'} for assistance.")
                LiveLog.log("operation.error", msg)
                _set_status(str(msg), self._error)
                final_btn.config(state='normal', text=final_label)

        validate_btn.config(command=do_validate)
        send_otp_btn.config(command=do_send_otp)
        verify_btn.config(command=do_verify_otp)
        final_btn.config(command=do_final)
        key_entry.bind('<Return>', lambda e: do_validate())
        otp_entry.bind('<Return>', lambda e: do_verify_otp())
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
                self.engine.mark_onboarding_complete()
                self._app_unlocked = True
                LiveLog.log("Trial activated", "Showing success dialog")
                self._show_success_dialog("trial")
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

    def _contact_support(self):
        LiveLog.log("Opening support request", "Showing support dialog")
        UniversalEmailDialog(self, "Contact Support", "support").show()

    def _sales_enquiry(self):
        LiveLog.log("Opening sales enquiry", "Showing sales dialog")
        UniversalEmailDialog(self, "Sales Enquiry", "sales").show()

    def _renewal_request(self):
        LiveLog.log("Opening renewal request", "Showing renewal dialog")
        UniversalEmailDialog(self, "Renewal Request", "renewal").show()

    def _activation_request(self):
        LiveLog.log("Opening activation request", "Showing activation dialog")
        UniversalEmailDialog(self, "Activation Request", "activation").show()

    def _reactivation_request(self):
        LiveLog.log("Opening reactivation request", "Showing reactivation dialog")
        UniversalEmailDialog(self, "Reactivation Request", "reactivation").show()

    def _license_request(self):
        LiveLog.log("Opening license request", "Showing license dialog")
        UniversalEmailDialog(self, "License Request", "license").show()


    def _view_hardware_status(self):
        LiveLog.log("Viewing hardware status")
        status = self.engine.view_hardware_status()
        msg = f"Current Hardware ID: {status.get('current_hardware_id', 'N/A')[:16]}..."
        if status.get('registered_hardware_id'):
            msg += f"\nRegistered Hardware ID: {status['registered_hardware_id'][:16]}..."
            msg += f"\nMatch: {status.get('matched', False)}"
        msg += f"\n\n{status.get('message', '')}"
        DialogManager.info(self._root, "Hardware Status", msg)

    def _view_conversations(self):
        LiveLog.log("Viewing conversations")
        email = self._status.customer_email if self._status else ''
        if not email:
            DialogManager.info(self._root, "Conversations", "No customer email available.")
            return
        result = self.engine.list_conversations(email)
        conversations = result.get('conversations', [])
        if not conversations:
            DialogManager.info(self._root, "Conversations", "No conversations found.")
            return
        msg = "\n\n".join([
            f"ID: {c.get('id', 'N/A')}\nCategory: {c.get('category', 'N/A')}\nStatus: {c.get('status', 'N/A')}\nSubject: {c.get('subject', 'N/A')}\nCreated: {c.get('created_at', 'N/A')}"
            for c in conversations[:10]
        ])
        DialogManager.info(self._root, "Conversations", msg)

    def _view_notifications(self):
        LiveLog.log("Viewing notifications")
        email = self._status.customer_email if self._status else ''
        if not email:
            DialogManager.info(self._root, "Notifications", "No customer email available.")
            return
        result = self.engine.get_notifications(email)
        notifications = result.get('notifications', [])
        if not notifications:
            DialogManager.info(self._root, "Notifications", "No notifications found.")
            return
        msg = "\n\n".join([
            f"{n.get('title', 'N/A')}\n{n.get('message', 'N/A')}\n{n.get('created_at', 'N/A')}"
            for n in notifications[:10]
        ])
        DialogManager.info(self._root, "Notifications", msg)
