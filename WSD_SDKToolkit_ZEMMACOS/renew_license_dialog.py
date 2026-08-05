"""Renew License Dialog — dedicated renewal workflow for the Universal
License Center (AWS-01).

Flow: enter existing license key → verify via the backend → unlock →
auto-fill license details (read-only) → fetch active paid plans → plan
dropdown (same-plan renewal / upgrade / downgrade) → auto renewal summary →
dummy payment simulator → generate payment/transaction ids → launch the
Universal Email Dialog (pre-filled; only reason/notes editable) → send the
renewal request. No real payment provider is ever contacted.
"""
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import tkinter as tk

from .live_log import LiveLog
from .license_engine import LicenseStatus
from .universal_email_dialog import UniversalEmailDialog

__all__ = ["RenewLicenseDialog"]

SUPPORT_EMAIL = "support@websmithdigital.com"


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _get(data: Dict[str, Any], *paths: str, default: str = "") -> str:
    """First non-empty scalar value across dotted paths (nested dicts)."""
    for path in paths:
        node: Any = data
        matched = True
        for part in path.split('.'):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                matched = False
                break
        if not matched:
            continue
        if isinstance(node, str) and node.strip():
            return node.strip()
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return str(node)
    return default


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in ("1", "true", "yes", "active", "paid")


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace('Z', '+00:00')
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text[:19])
    except ValueError:
        return None


def _plan_is_showable(plan: Dict[str, Any]) -> bool:
    """Only active paid plans — never trial, deleted, inactive or expired."""
    if not isinstance(plan, dict):
        return False
    name = _to_text(plan.get('name') or plan.get('plan_name')).lower()
    plan_type = _to_text(plan.get('type') or plan.get('plan_type')).lower()
    if _is_truthy(plan.get('is_trial_plan')) or plan_type == 'trial' or 'trial' in name:
        return False
    if plan.get('is_active') is not None and not _is_truthy(plan.get('is_active')):
        return False
    if _is_truthy(plan.get('is_deleted')) or plan.get('deleted_at'):
        return False
    status = _to_text(plan.get('status')).lower()
    if status in ('deleted', 'inactive', 'expired', 'archived', 'disabled'):
        return False
    expiry = _parse_date(plan.get('expires_at') or plan.get('expiry_date') or plan.get('valid_until'))
    if expiry is not None and expiry < datetime.now():
        return False
    return True


def _plan_duration_days(plan: Dict[str, Any]) -> Optional[int]:
    for key in ('duration_days', 'default_expiry_days', 'validity_days'):
        value = plan.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    for key in ('duration', 'validity'):
        text = _to_text(plan.get(key)).lower()
        if not text:
            continue
        if 'year' in text or 'yr' in text:
            match = re.search(r'(\d+)', text)
            return (int(match.group(1)) if match else 1) * 365
        if 'month' in text or 'mo' in text:
            match = re.search(r'(\d+)', text)
            return (int(match.group(1)) if match else 1) * 30
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
    return None


def _plan_is_lifetime(plan: Dict[str, Any]) -> bool:
    text = " ".join(_to_text(plan.get(k)) for k in ('duration', 'name', 'validity')).lower()
    return 'lifetime' in text or 'perpetual' in text or 'one-time' in text


def _format_amount(plan: Dict[str, Any]) -> str:
    value = plan.get('price')
    if value is None:
        value = plan.get('amount')
    if value is None:
        value = plan.get('cost')
    if value is None or value == '':
        return "—"
    if isinstance(value, bool):
        value = str(value)
    elif isinstance(value, (int, float)):
        if float(value).is_integer():
            value = f"{int(value):,}"
        else:
            value = f"{float(value):,.2f}"
    currency = _to_text(plan.get('currency') or plan.get('currency_code') or plan.get('currency_symbol'))
    return f"{value} {currency}".strip() if currency else str(value)


def _friendly_error(exc: Exception) -> str:
    message = getattr(exc, 'message', None) or str(exc)
    if message.lower().startswith('api error'):
        message = re.sub(r'^api error \d+:\s*', '', message, flags=re.IGNORECASE).strip()
    if not message:
        return "License verification failed. Please try again."
    lower = message.lower()
    if 'timeout' in lower or 'connection' in lower:
        return "Unable to reach the license server. Please check your connection and try again."
    return message


class RenewLicenseDialog:
    """Renew License workflow dialog (single window, step-by-step unlock)."""

    def __init__(self, center: Any):
        self._center = center
        self._engine = center.engine
        self._hardware = center.hardware
        self._parent = getattr(center, '_root', None)
        self._primary = center._primary
        self._bg = center._bg
        self._card_bg = center._card_bg
        self._text_primary = center._text_primary
        self._text_secondary = center._text_secondary
        self._success = center._success
        self._error = center._error
        self._warning = center._warning
        self._border = center._border
        self._product_name = center._product_name
        self._support_email = getattr(center, '_support_email', '') or SUPPORT_EMAIL

        self._dialog: Optional[tk.Toplevel] = None
        self._status_label: Optional[tk.Label] = None
        self._readonly_entries: List[tk.Entry] = []
        self._vars: Dict[str, tk.StringVar] = {}
        self._plan_btn: Optional[tk.Menubutton] = None
        self._back_btn: Optional[tk.Button] = None
        self._proceed_btn: Optional[tk.Button] = None

        self._verified = False
        self._license_key = ""
        self._product = self._product_name
        self._current_plan_id = ""
        self._current_plan_name = ""
        self._current_expiry = ""
        self._license_status_text = ""
        self._customer_name = ""
        self._customer_email = ""
        self._customer_phone = ""

        self._plans: List[Dict[str, Any]] = []
        self._plan_labels: List[str] = []
        self._selected_plan: Dict[str, Any] = {}
        self._renewed_expiry_text = ""
        self._amount_text = ""
        self._payment: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def show(self) -> None:
        dialog = tk.Toplevel(self._parent)
        dialog.title("Renew License")
        dialog.geometry("880x880")
        dialog.minsize(780, 740)
        dialog.configure(bg=self._bg)
        dialog.resizable(True, True)
        if self._parent is not None:
            dialog.transient(self._parent)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", self._close)
        dialog.bind("<Escape>", lambda e: self._close())
        self._dialog = dialog

        self._key_var = tk.StringVar()
        self._vars = {
            name: tk.StringVar()
            for name in (
                "customer_name", "customer_email", "customer_phone", "product",
                "current_plan", "license_status", "license_expiry", "license_key",
                "selected_plan", "duration", "price", "description", "renewed_expiry",
                "summary_current", "summary_selected", "summary_current_expiry",
                "summary_renewed_expiry", "summary_amount",
            )
        }

        # ---- bottom action bar ----
        action_bar = tk.Frame(dialog, bg=self._card_bg)
        action_bar.pack(side="bottom", fill="x")
        tk.Frame(action_bar, bg=self._border, height=1).pack(fill="x")
        action_inner = tk.Frame(action_bar, bg=self._card_bg)
        action_inner.pack(fill="x", padx=20, pady=12)

        self._status_label = tk.Label(action_inner, text="", font=("Segoe UI", 9),
                                      fg=self._text_secondary, bg=self._card_bg, anchor="w")
        self._status_label.pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(action_inner, bg=self._card_bg)
        btn_frame.pack(side="right")

        self._back_btn = tk.Button(btn_frame, text="Back", font=("Segoe UI", 9),
                                   bg="#f3f4f6", fg=self._text_primary, relief="flat",
                                   padx=18, pady=6, cursor="hand2",
                                   activebackground="#e5e7eb", activeforeground=self._text_primary,
                                   command=self._go_back)
        self._back_btn.pack(side="left", padx=(0, 10))

        self._proceed_btn = tk.Button(btn_frame, text="Proceed to Payment",
                                      font=("Segoe UI", 9, "bold"),
                                      bg=self._primary, fg="white", relief="flat",
                                      padx=20, pady=6, cursor="hand2",
                                      activebackground=self._text_primary,
                                      activeforeground="white",
                                      command=self._proceed_to_payment)
        self._proceed_btn.pack(side="left")

        # ---- title bar ----
        title_bar = tk.Frame(dialog, bg=self._primary, height=56)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)
        title_inner = tk.Frame(title_bar, bg=self._primary)
        title_inner.pack(fill="both", padx=20, pady=10)

        close_btn = tk.Label(title_inner, text="✕", font=("Segoe UI", 14, "bold"),
                             fg="white", bg=self._primary, cursor="hand2", padx=6)
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff6b6b"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="white"))

        tk.Label(title_inner, text="🔑  Renew License",
                 font=("Segoe UI", 14, "bold"),
                 fg="white", bg=self._primary).pack(side="left")

        # ---- body ----
        body = tk.Frame(dialog, bg=self._bg)
        body.pack(fill="both", expand=True, pady=16)

        self._build_key_card(body)
        self._build_details_card(body)
        self._build_plan_card(body)
        self._build_summary_card(body)

        self._set_locked()
        self._set_status("Enter an existing license key and press Verify.", self._text_secondary)
        self._key_entry.focus_set()

        dialog.wait_window()

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------
    def _card(self, parent: tk.Widget, title: str) -> tk.Frame:
        card = tk.Frame(parent, bg=self._card_bg,
                        highlightthickness=1, highlightbackground=self._border,
                        highlightcolor=self._border, relief="flat")
        card.pack(fill="x", padx=18, pady=(0, 12))
        header = tk.Frame(card, bg=self._card_bg)
        header.pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(header, text=title, font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")
        return card

    def _readonly_pair(self, parent: tk.Widget, label: str, var_name: str,
                       row: int, column: int) -> None:
        cell = tk.Frame(parent, bg=self._card_bg)
        cell.grid(row=row, column=column, sticky="nsew", padx=(0, 10), pady=3)
        cell.columnconfigure(1, weight=1)
        tk.Label(cell, text=label, font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=13, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 6))
        entry = tk.Entry(cell, font=("Segoe UI", 9), relief="solid", bd=1,
                         bg="#f2f4f8", fg=self._text_primary,
                         readonlybackground="#f2f4f8", cursor="arrow",
                         textvariable=self._vars[var_name], state="disabled")
        entry.grid(row=0, column=1, sticky="ew")
        self._readonly_entries.append(entry)

    def _build_key_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "License Key")
        row = tk.Frame(card, bg=self._card_bg)
        row.pack(fill="x", padx=16, pady=(2, 12))
        tk.Label(row, text="License Key", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=11, anchor="w").pack(side="left", padx=(0, 6))
        self._key_entry = tk.Entry(row, font=("Consolas", 11), relief="solid", bd=1,
                                   bg="white", fg=self._text_primary,
                                   insertbackground=self._primary,
                                   highlightthickness=1, highlightbackground=self._border,
                                   highlightcolor=self._primary,
                                   textvariable=self._key_var)
        self._key_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self._key_entry.bind("<Return>", lambda e: self._do_verify())
        self._verify_btn = tk.Button(row, text="Verify", font=("Segoe UI", 9, "bold"),
                                     bg=self._primary, fg="white", relief="flat",
                                     padx=18, pady=6, cursor="hand2",
                                     activebackground=self._text_primary,
                                     activeforeground="white",
                                     command=self._do_verify)
        self._verify_btn.pack(side="left", padx=(8, 0))

    def _build_details_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "License Details")
        tk.Label(card, text="read-only · auto-filled", font=("Segoe UI", 8),
                 fg=self._text_secondary, bg=self._card_bg).pack(anchor="e", padx=16)
        grid = tk.Frame(card, bg=self._card_bg)
        grid.pack(fill="x", padx=16, pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        fields = (
            ("Customer Name", "customer_name"),
            ("Customer Email", "customer_email"),
            ("Customer Phone", "customer_phone"),
            ("Product", "product"),
            ("Current Plan", "current_plan"),
            ("License Status", "license_status"),
            ("License Expiry", "license_expiry"),
            ("License Key", "license_key"),
        )
        for index, (label, var_name) in enumerate(fields):
            self._readonly_pair(grid, label, var_name, index // 2, index % 2)

    def _build_plan_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "Select Renewal Plan")
        tk.Label(card, text="same-plan renewal · upgrade · downgrade",
                 font=("Segoe UI", 8),
                 fg=self._text_secondary, bg=self._card_bg).pack(anchor="e", padx=16)
        row = tk.Frame(card, bg=self._card_bg)
        row.pack(fill="x", padx=16, pady=(6, 2))
        tk.Label(row, text="Available Plans", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=13, anchor="w").pack(side="left", padx=(0, 6))
        self._plan_btn = tk.Menubutton(row, text="Select Plan  ▾",
                                       font=("Segoe UI", 9),
                                       bg=self._card_bg, fg=self._text_primary,
                                       relief="flat", bd=0, padx=6, pady=3,
                                       cursor="hand2", highlightthickness=0,
                                       activebackground="#e9ecf1",
                                       activeforeground=self._text_primary,
                                       width=30, anchor="w", state="disabled")
        self._plan_btn.pack(side="left")
        grid = tk.Frame(card, bg=self._card_bg)
        grid.pack(fill="x", padx=16, pady=(4, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        self._readonly_pair(grid, "Selected Plan", "selected_plan", 0, 0)
        self._readonly_pair(grid, "Duration", "duration", 0, 1)
        self._readonly_pair(grid, "Price", "price", 1, 0)
        self._readonly_pair(grid, "Renewal Expiry", "renewed_expiry", 1, 1)
        desc_cell = tk.Frame(card, bg=self._card_bg)
        desc_cell.pack(fill="x", padx=16, pady=(4, 14))
        tk.Label(desc_cell, text="Description", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=13, anchor="w").pack(side="left", padx=(0, 6))
        desc_entry = tk.Entry(desc_cell, font=("Segoe UI", 9), relief="solid", bd=1,
                              bg="#f2f4f8", fg=self._text_primary,
                              readonlybackground="#f2f4f8", cursor="arrow",
                              textvariable=self._vars["description"],
                              state="disabled")
        desc_entry.pack(side="left", fill="x", expand=True)
        self._readonly_entries.append(desc_entry)

    def _build_summary_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "Renewal Summary")
        grid = tk.Frame(card, bg=self._card_bg)
        grid.pack(fill="x", padx=16, pady=(2, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        self._readonly_pair(grid, "Current Plan", "summary_current", 0, 0)
        self._readonly_pair(grid, "Selected Plan", "summary_selected", 0, 1)
        self._readonly_pair(grid, "Current Expiry", "summary_current_expiry", 1, 0)
        self._readonly_pair(grid, "Renewed Expiry", "summary_renewed_expiry", 1, 1)
        self._readonly_pair(grid, "Amount", "summary_amount", 2, 0)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _set_locked(self) -> None:
        self._verified = False
        for entry in self._readonly_entries:
            entry.config(state="disabled")
        if self._plan_btn is not None:
            self._plan_btn.config(state="disabled")
        self._back_btn.config(state="disabled")
        self._proceed_btn.config(state="disabled")

    def _set_unlocked(self) -> None:
        self._verified = True
        for entry in self._readonly_entries:
            entry.config(state="readonly")
        self._plan_btn.config(state="normal")
        self._back_btn.config(state="normal")
        self._proceed_btn.config(state="normal")

    def _set_status(self, text: str, color: str) -> None:
        if self._status_label is not None:
            self._status_label.config(text=text, fg=color)

    # ------------------------------------------------------------------
    # Step 2 — verification
    # ------------------------------------------------------------------
    def _do_verify(self) -> None:
        if self._dialog is None:
            return
        key = self._key_var.get().strip()
        if not key:
            self._set_status("Please enter your license key.", self._error)
            self._key_entry.focus_set()
            return
        self._verify_btn.config(state="disabled", text="Verifying...")
        self._set_status("Verifying license key...", self._text_secondary)
        try:
            result = self._engine.verify_license_for_renewal(key)
        except Exception as exc:
            self._verify_btn.config(state="normal", text="Verify")
            self._set_status(_friendly_error(exc), self._error)
            LiveLog.log("Renewal verification error", str(exc))
            return
        if not result.get('success') or not result.get('valid'):
            self._verify_btn.config(state="normal", text="Verify")
            self._set_status(self._extract_error(result, "License validation failed."), self._error)
            return
        self._license_key = key
        self._apply_verification(result)
        self._verify_btn.config(state="normal", text="Verify")
        self._set_unlocked()
        self._set_status("License verified. Review the details and select a plan.", self._success)
        LiveLog.log("Renewal license verified", f"Key: {key[:8]}...")

    def _extract_error(self, result: Any, default: str) -> str:
        if not isinstance(result, dict):
            return default
        error = result.get('error')
        if isinstance(error, dict):
            return _to_text(error.get('message') or error.get('code')) or default
        if error:
            return _to_text(error) or default
        if result.get('message'):
            return _to_text(result['message'])
        if result.get('code'):
            return _to_text(result['code'])
        return default

    # ------------------------------------------------------------------
    # Step 3 — auto-fill license details (read-only)
    # ------------------------------------------------------------------
    def _apply_verification(self, result: Dict[str, Any]) -> None:
        details: Dict[str, Any] = {}
        try:
            details = self._engine.get_license_details(self._license_key) or {}
        except Exception:
            details = {}

        verified_license = result.get('license') if isinstance(result.get('license'), dict) else {}
        verified_customer = result.get('customer') if isinstance(result.get('customer'), dict) else {}
        details_license = details.get('license') if isinstance(details.get('license'), dict) else {}
        details_customer = details.get('customer') if isinstance(details.get('customer'), dict) else {}
        details_product = details.get('product') if isinstance(details.get('product'), dict) else {}
        details_plan = details.get('plan') if isinstance(details.get('plan'), dict) else {}

        self._customer_name = (
            _get(details_customer, 'name') or _get(details_license, 'customer_name')
            or _get(verified_customer, 'name') or _get(details, 'customer_name', 'name')
        )
        self._customer_email = (
            _get(details_customer, 'email') or _get(details_license, 'customer_email')
            or _get(verified_customer, 'email') or _get(details, 'customer_email', 'email')
        )
        self._customer_phone = (
            _get(details_customer, 'phone') or _get(details_customer, 'mobile')
            or _get(details_license, 'customer_phone', 'customer_mobile')
            or _get(verified_customer, 'phone', 'mobile')
        )
        self._product = (
            _get(details_product, 'name') or _get(details, 'product_name') or self._product_name
        )
        self._current_plan_name = (
            _get(details_plan, 'name') or _get(details_license, 'plan')
            or _get(result, 'plan', 'current_plan_name')
        )
        self._current_plan_id = (
            _get(details_plan, 'id') or _get(result, 'plan_id', 'current_plan_id')
        )
        self._current_expiry = (
            _get(details_license, 'expiry_date') or _get(verified_license, 'expiry_date')
            or _get(result, 'expiry_date') or _get(details, 'expiry_date')
        )

        api_status = (_get(details, 'status') or _get(result, 'status')).lower()
        if result.get('is_expired') or api_status == 'expired':
            self._license_status_text = "Expired (renewal eligible)"
        elif api_status in ('licensed', 'active'):
            self._license_status_text = "Active"
        elif api_status:
            self._license_status_text = api_status.capitalize()
        else:
            self._license_status_text = "Active"

        self._fetch_plans(result)
        self._fill_details_vars()

    def _fill_details_vars(self) -> None:
        self._vars['customer_name'].set(self._customer_name)
        self._vars['customer_email'].set(self._customer_email)
        self._vars['customer_phone'].set(self._customer_phone or "—")
        self._vars['product'].set(self._product or "—")
        self._vars['current_plan'].set(self._current_plan_name or "—")
        self._vars['license_status'].set(self._license_status_text)
        self._vars['license_expiry'].set(self._current_expiry or "—")
        self._vars['license_key'].set(self._license_key)
        self._vars['summary_current'].set(self._current_plan_name or "—")
        self._vars['summary_current_expiry'].set(self._current_expiry or "—")

    # ------------------------------------------------------------------
    # Step 4 — fetch active paid plans + Step 5/6 — dropdown selection
    # ------------------------------------------------------------------
    def _fetch_plans(self, verify_result: Dict[str, Any]) -> None:
        plans_result: Dict[str, Any] = {}
        try:
            plans_result = self._engine.get_available_plans(self._license_key) or {}
        except Exception:
            plans_result = {}

        raw_plans: List[Any] = []
        if isinstance(plans_result.get('plans'), list):
            raw_plans = plans_result['plans']
        elif isinstance(verify_result.get('available_plans'), list):
            raw_plans = verify_result['available_plans']

        current_plan_from_result = plans_result.get('current_plan')
        if isinstance(current_plan_from_result, dict):
            if not self._current_plan_name:
                self._current_plan_name = _get(current_plan_from_result, 'name')
            if not self._current_plan_id:
                self._current_plan_id = _get(current_plan_from_result, 'id')

        self._plans = []
        seen = set()
        for raw in raw_plans:
            if not isinstance(raw, dict) or not _plan_is_showable(raw):
                continue
            identity = _to_text(raw.get('id') or raw.get('plan_id') or raw.get('name'))
            if not identity or identity in seen:
                continue
            seen.add(identity)
            self._plans.append(raw)

        self._plan_labels = [self._plan_label(p) for p in self._plans]
        if self._plans:
            selected = None
            for plan in self._plans:
                if _to_text(plan.get('name')) == self._current_plan_name:
                    selected = plan
                    break
            if selected is None:
                selected = self._plans[0]
            self._rebuild_plan_menu(self._plan_label(selected))
            self._select_plan(selected)
        else:
            self._rebuild_plan_menu("No plans available")
            self._set_status("License verified, but no paid plans are available for renewal.",
                             self._warning)

    def _plan_label(self, plan: Dict[str, Any]) -> str:
        name = _to_text(plan.get('name') or plan.get('plan_name'))
        duration = _to_text(plan.get('duration'))
        if not duration:
            days = _plan_duration_days(plan)
            if days:
                duration = f"{days} days"
            elif _plan_is_lifetime(plan):
                duration = "Lifetime"
        return f"{name} — {duration}".strip(" —") if duration else name

    def _rebuild_plan_menu(self, selected_text: str) -> None:
        menu = tk.Menu(self._plan_btn, tearoff=0, bg="white", fg=self._text_primary,
                       activebackground=self._primary, activeforeground="white",
                       font=("Segoe UI", 9), relief="flat", bd=0)
        for label in self._plan_labels:
            menu.add_command(label=label,
                             command=lambda v=label: self._on_plan_selected(v))
        self._plan_btn.configure(menu=menu, text=f"{selected_text}  ▾")

    def _on_plan_selected(self, label: str) -> None:
        for plan in self._plans:
            if self._plan_label(plan) == label:
                self._select_plan(plan)
                self._set_status("Renewal summary updated. Proceed to payment when ready.",
                                 self._success)
                return

    def _select_plan(self, plan: Dict[str, Any]) -> None:
        self._selected_plan = plan
        label = self._plan_label(plan)
        self._plan_btn.config(text=f"{label}  ▾")
        self._vars['selected_plan'].set(_to_text(plan.get('name') or '—'))
        self._vars['duration'].set(self._duration_text(plan))
        self._vars['price'].set(_format_amount(plan))
        self._vars['description'].set(_to_text(plan.get('description')) or "—")
        self._renewed_expiry_text = self._compute_renewed_expiry(plan)
        self._vars['renewed_expiry'].set(self._renewed_expiry_text)
        self._amount_text = _format_amount(plan)
        self._vars['summary_selected'].set(_to_text(plan.get('name') or '—'))
        self._vars['summary_renewed_expiry'].set(self._renewed_expiry_text)
        self._vars['summary_amount'].set(self._amount_text)

    def _duration_text(self, plan: Dict[str, Any]) -> str:
        duration = _to_text(plan.get('duration'))
        if duration:
            return duration
        if _plan_is_lifetime(plan):
            return "Lifetime"
        days = _plan_duration_days(plan)
        return f"{days} days" if days else "—"

    def _compute_renewed_expiry(self, plan: Dict[str, Any]) -> str:
        if _plan_is_lifetime(plan):
            return "Lifetime"
        days = _plan_duration_days(plan)
        base = _parse_date(self._current_expiry)
        if base is None or base < datetime.now():
            base = datetime.now()
        if days:
            renewed = base + timedelta(days=days)
        else:
            renewed = base + timedelta(days=365)
        return renewed.strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _go_back(self) -> None:
        if self._dialog is None:
            return
        self._license_key = ""
        self._plans = []
        self._plan_labels = []
        self._selected_plan = {}
        self._payment = {}
        self._key_var.set("")
        for var in self._vars.values():
            var.set("")
        self._set_locked()
        self._plan_btn.config(text="Select Plan  ▾")
        self._verify_btn.config(state="normal", text="Verify")
        self._key_entry.focus_set()
        self._set_status("Enter a license key to start over.", self._text_secondary)

    def _proceed_to_payment(self) -> None:
        if not self._verified:
            return
        if not self._selected_plan:
            self._set_status("Select a plan before proceeding to payment.", self._error)
            return
        self._open_payment_dialog()

    # ------------------------------------------------------------------
    # Step 8 — dummy payment dialog (simulator only)
    # ------------------------------------------------------------------
    def _open_payment_dialog(self) -> None:
        if self._dialog is None:
            return
        plan_name = _to_text(self._selected_plan.get('name'))
        dialog = tk.Toplevel(self._dialog)
        dialog.title("Payment — Simulator")
        dialog.geometry("460x330")
        dialog.configure(bg=self._bg)
        dialog.transient(self._dialog)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        header = tk.Frame(dialog, bg=self._primary, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="💳  Payment — Simulator", font=("Segoe UI", 14, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        body = tk.Frame(dialog, bg=self._card_bg, padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"Plan: {plan_name}", font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg, anchor="w").pack(fill="x", pady=(0, 6))

        amount_row = tk.Frame(body, bg=self._card_bg)
        amount_row.pack(fill="x", pady=3)
        tk.Label(amount_row, text="Amount", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=12, anchor="w").pack(side="left")
        tk.Label(amount_row, text=self._amount_text, font=("Segoe UI", 11, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        status_row = tk.Frame(body, bg=self._card_bg)
        status_row.pack(fill="x", pady=3)
        tk.Label(status_row, text="Payment Status", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=12, anchor="w").pack(side="left")
        tk.Label(status_row, text="PENDING", font=("Segoe UI", 10, "bold"),
                 fg=self._warning, bg=self._card_bg).pack(side="left")

        tk.Label(body, text="This is a dummy payment dialog — no real payment is processed\n"
                            "and no payment provider (Razorpay / Stripe / PayPal / UPI) is contacted.",
                 font=("Segoe UI", 8), fg=self._text_secondary, bg=self._card_bg,
                 justify="left", anchor="w").pack(fill="x", pady=(14, 4))

        buttons = tk.Frame(body, bg=self._card_bg)
        buttons.pack(fill="x", side="bottom", pady=(8, 0))

        tk.Button(buttons, text="Cancel", font=("Segoe UI", 9),
                  bg="#f3f4f6", fg=self._text_primary, relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  activebackground="#e5e7eb", activeforeground=self._text_primary,
                  command=dialog.destroy).pack(side="left")

        tk.Button(buttons, text="Mark Payment Successful", font=("Segoe UI", 9, "bold"),
                  bg=self._success, fg="white", relief="flat",
                  padx=16, pady=6, cursor="hand2",
                  activebackground="#15803d", activeforeground="white",
                  command=lambda: self._mark_payment_successful(dialog)).pack(side="right")

    # ------------------------------------------------------------------
    # Step 9 — generate payment / transaction ids
    # ------------------------------------------------------------------
    def _mark_payment_successful(self, dialog: tk.Toplevel) -> None:
        now = datetime.now()
        self._payment = {
            "payment_id": "PAY-" + uuid.uuid4().hex[:10].upper(),
            "transaction_id": "TXN-" + uuid.uuid4().hex[:12].upper(),
            "payment_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_status": "Paid",
            "amount": self._amount_text,
        }
        LiveLog.log("Renewal payment marked successful",
                    f"Payment: {self._payment['payment_id']} · "
                    f"Transaction: {self._payment['transaction_id']}")
        try:
            dialog.destroy()
        except Exception:
            pass
        self._launch_email_dialog()

    # ------------------------------------------------------------------
    # Step 10 — launch the Universal Email Dialog (pre-filled)
    # ------------------------------------------------------------------
    def _launch_email_dialog(self) -> None:
        if self._dialog is not None:
            try:
                self._dialog.grab_release()
            except Exception:
                pass
            try:
                self._dialog.destroy()
            except Exception:
                pass
            self._dialog = None

        old_status = getattr(self._center, '_status', None)
        old_product = getattr(self._center, '_product_name', '')
        try:
            self._center._status = LicenseStatus(
                valid=True,
                status='licensed',
                expiry_date=self._current_expiry or None,
                plan=self._current_plan_name or None,
                license_key=self._license_key,
                customer_name=self._customer_name,
                customer_email=self._customer_email,
                customer_phone=self._customer_phone,
                product_name=self._product,
                hardware_id=self._hardware.get_fingerprint(),
            )
            self._center._product_name = self._product
            UniversalEmailDialog(
                self._center,
                "Renewal Request",
                "renewal",
                prefill=self._build_prefill(),
            ).show()
        finally:
            self._center._status = old_status
            self._center._product_name = old_product

    def _build_prefill(self) -> Dict[str, str]:
        return {
            "customer_name": self._customer_name,
            "customer_email": self._customer_email,
            "product": self._product or self._product_name,
            "plan": self._current_plan_name,
            "license_key": self._license_key,
            "subject": f"License Renewal Request — {self._product or self._product_name}",
            "message": self._build_renewal_message(),
        }

    def _build_renewal_message(self) -> str:
        request_time = self._payment.get(
            'payment_timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        lines = [
            "RENEWAL REQUEST (auto-generated)",
            "=" * 40,
            f"Customer Name     : {self._customer_name}",
            f"Customer Email    : {self._customer_email}",
            f"License Key       : {self._license_key}",
            f"Product           : {self._product or self._product_name}",
            f"Current Plan      : {self._current_plan_name or '—'}",
            f"Selected Plan     : {_to_text(self._selected_plan.get('name'))}",
            f"Current Expiry    : {self._current_expiry or '—'}",
            f"Renewed Expiry    : {self._renewed_expiry_text}",
            f"Payment ID        : {self._payment.get('payment_id', '')}",
            f"Transaction ID    : {self._payment.get('transaction_id', '')}",
            f"Payment Status    : {self._payment.get('payment_status', 'Paid')}",
            f"Request Time      : {request_time}",
            "",
            "Please review and process this renewal request.",
            "",
            "Additional Notes:",
        ]
        return "\n".join(lines)

    def _close(self) -> None:
        if self._dialog is not None:
            try:
                self._dialog.destroy()
            except Exception:
                pass
            self._dialog = None
