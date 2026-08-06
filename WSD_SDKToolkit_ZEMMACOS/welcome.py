"""Welcome Dialog - Customer onboarding with OTP verification and trial generation

UI LAYER ONLY (SDK V2): OTP, registration and cache writes are delegated to
LicenseEngine; this dialog renders the form, validates fields inline and
reports progress through the shared WorkflowProgress stages.
"""
import json
import os
import time as _time
import traceback
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from .license_engine import LicenseEngine
from .client import ApiError
from .validation import (FieldIndicator, OTP_INVALID_MESSAGE,
                         is_valid_email, is_valid_mobile, mobile_digits_error)
from .workflow_progress import WorkflowProgress, format_timer

SDK_VERSION = "1.0.0"
RUNTIME_TYPE = "python"


_COUNTRIES_CACHE: list = []


class WelcomeDialog:
    def __init__(self, engine: Optional[LicenseEngine] = None,
                 product_name: str = '',
                 log_fn: Optional[Callable[[str, str, str, Optional[str]], None]] = None,
                 client: Optional[Any] = None,
                 hardware: Optional[Any] = None,
                 cache: Optional[Any] = None):
        # ``client`` / ``hardware`` / ``cache`` are accepted for backward
        # compatibility only — all operations go through the engine.
        self.engine = engine
        self.product_name = product_name
        self._log_fn = log_fn
        self._result: Optional[Dict[str, Any]] = None
        self._root: Optional[tk.Toplevel] = None
        self._countries = []
        self._selected_country = None
        self._otp_sent = False
        self._otp_expires_at = 0.0
        self._otp_timer_id = None
        branding = (engine.config.get('branding', {})
                    if engine is not None else {})
        self._primary = branding.get('primary_color', '#6366f1')
        self._bg = '#f0f2f5'
        self._card_bg = '#ffffff'
        self._text_primary = '#1a1a2e'
        self._text_secondary = '#6b7280'
        self._success = '#10b981'
        self._error = '#ef4444'
        self._border = '#d1d5db'

    def is_onboarding_complete(self) -> bool:
        if self.engine is not None:
            return self.engine.is_onboarding_complete()
        return False

    def show(self) -> Dict[str, Any]:
        if self.is_onboarding_complete():
            return {'skipped': True, 'message': 'Onboarding already completed'}
        self._result = None
        self._root = tk.Toplevel()
        self._root.title(self.product_name or 'Welcome')
        self._root.geometry('480x650')
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_closing)
        self._build_ui()
        self._center_window()
        self._load_countries()
        self._root.wait_window()
        return self._result or {'skipped': True}

    def _log(self, category: str, level: str, message: str, detail: Optional[str] = None):
        if self._log_fn:
            try:
                self._log_fn(category, level, message, detail)
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
        self._root.geometry(f'{w}x{h}+{x}+{y}')

    def _build_ui(self):
        root = self._root

        header = tk.Frame(root, bg=self._primary, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text='Welcome',
                 font=('Segoe UI', 20, 'bold'),
                 fg='white', bg=self._primary).pack(expand=True)

        sub = tk.Label(root, text='Complete your registration to start the trial',
                       font=('Segoe UI', 11), bg=self._bg, fg=self._text_secondary)
        sub.pack(pady=(12, 16))
        frame = tk.Frame(root, bg=self._card_bg, bd=1, relief='solid',
                         highlightbackground=self._border)
        frame.pack(fill='both', expand=True, padx=30, pady=(0, 20))
        padding = {'padx': 20, 'pady': 4}
        tk.Label(frame, text='Name *', font=('Segoe UI', 11),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        self._name_entry = tk.Entry(frame, font=('Segoe UI', 12), relief='solid',
                                     bd=1, highlightbackground=self._border)
        self._name_entry.pack(fill='x', padx=20, pady=(0, 10))
        self._name_entry.focus()
        tk.Label(frame, text='Email *', font=('Segoe UI', 11),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        email_row = tk.Frame(frame, bg=self._card_bg)
        email_row.pack(fill='x', padx=20, pady=(0, 10))
        self._email_entry = tk.Entry(email_row, font=('Segoe UI', 12), relief='solid',
                                      bd=1, highlightbackground=self._border)
        self._email_entry.pack(side='left', fill='x', expand=True)
        self._email_indicator_label = tk.Label(email_row, text='', font=('Segoe UI', 12, 'bold'),
                                               bg=self._card_bg, fg=self._success)
        self._email_indicator_label.pack(side='left', padx=(6, 0))
        self._email_indicator = FieldIndicator(self._email_indicator_label,
                                               success_color=self._success,
                                               error_color=self._error)
        self._email_entry.bind('<KeyRelease>', self._update_email_indicator)
        tk.Label(frame, text='Mobile Number *', font=('Segoe UI', 11),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        mobile_frame = tk.Frame(frame, bg=self._card_bg)
        mobile_frame.pack(fill='x', padx=20, pady=(0, 10))
        self._country_var = tk.StringVar()
        self._country_menu = ttk.Combobox(mobile_frame, textvariable=self._country_var,
                                           width=14, state='readonly', font=('Segoe UI', 11))
        self._country_menu.pack(side='left')
        self._mobile_entry = tk.Entry(mobile_frame, font=('Segoe UI', 12), relief='solid',
                                       bd=1, highlightbackground=self._border)
        self._mobile_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self._mobile_indicator_label = tk.Label(mobile_frame, text='', font=('Segoe UI', 12, 'bold'),
                                                bg=self._card_bg, fg=self._success)
        self._mobile_indicator_label.pack(side='left', padx=(6, 0))
        self._mobile_indicator = FieldIndicator(self._mobile_indicator_label,
                                                success_color=self._success,
                                                error_color=self._error)
        self._mobile_entry.bind('<KeyRelease>', self._update_mobile_indicator)
        tk.Label(frame, text='Company (optional)', font=('Segoe UI', 11),
                 fg=self._text_secondary, bg=self._card_bg).pack(anchor='w', **padding)
        self._company_entry = tk.Entry(frame, font=('Segoe UI', 12), relief='solid',
                                        bd=1, highlightbackground=self._border)
        self._company_entry.pack(fill='x', padx=20, pady=(0, 12))
        self._status_label = tk.Label(frame, text='', font=('Segoe UI', 10),
                                       bg=self._card_bg, fg=self._success)
        self._status_label.pack(padx=20, pady=(0, 4))
        self._send_btn = tk.Button(frame, text='Send OTP', font=('Segoe UI', 12, 'bold'),
                                   bg=self._primary, fg='white', relief='flat',
                                   command=self._on_send_otp, cursor='hand2',
                                   padx=12, pady=7)
        self._send_btn.pack(fill='x', padx=20, pady=(0, 8))
        otp_frame = tk.Frame(frame, bg=self._card_bg)
        otp_frame.pack(fill='x', padx=20, pady=(0, 5))
        self._otp_entry = tk.Entry(otp_frame, font=('Segoe UI', 16), relief='solid',
                                    bd=1, highlightbackground=self._border,
                                    justify='center', width=10)
        self._otp_entry.pack(side='left', fill='x', expand=True)
        self._otp_entry.config(state='disabled')
        self._verify_btn = tk.Button(otp_frame, text='Verify', font=('Segoe UI', 12, 'bold'),
                                     bg=self._success, fg='white', relief='flat',
                                     command=self._on_verify_otp, cursor='hand2',
                                     state='disabled',
                                     padx=12, pady=7)
        self._verify_btn.pack(side='left', padx=(8, 0))
        self._error_label = tk.Label(frame, text='', font=('Segoe UI', 10),
                                      bg=self._card_bg, fg=self._error)
        self._error_label.pack(padx=20, pady=(5, 16))
        company = self.product_name or 'License'
        footer = tk.Label(self._root, text=f'Protected by {company}',
                          font=('Segoe UI', 9), bg=self._bg, fg='#9ca3af')
        footer.pack(side='bottom', pady=(0, 22))

    def _load_countries(self):
        global _COUNTRIES_CACHE
        if _COUNTRIES_CACHE:
            self._set_countries(_COUNTRIES_CACHE)
            return
        try:
            result = self.engine.get_countries()
            if isinstance(result, dict) and result.get('data'):
                countries = result['data']
                if isinstance(countries, list) and countries:
                    _COUNTRIES_CACHE = countries
                    self._set_countries(countries)
                    return
        except Exception:
            pass
        self._set_countries([])

    def _set_countries(self, countries: list):
        self._countries = countries
        if not countries:
            return
        labels = [f"{c.get('dial', '')} {c.get('name', '')}" for c in countries]
        self._country_menu['values'] = labels
        self._country_menu.current(0)
        self._selected_country = countries[0] if countries else None

        def on_select(event):
            idx = self._country_menu.current()
            if 0 <= idx < len(countries):
                self._selected_country = countries[idx]
                self._update_mobile_indicator()

        self._country_menu.bind('<<ComboboxSelected>>', on_select)

    def _update_email_indicator(self, event=None):
        if not hasattr(self, '_email_indicator'):
            return
        email = self._email_entry.get().strip()
        if not email:
            self._email_indicator.clear()
        elif is_valid_email(email):
            self._email_indicator.set_valid()
        else:
            self._email_indicator.set_invalid()

    def _update_mobile_indicator(self, event=None):
        if not hasattr(self, '_mobile_indicator'):
            return
        mobile = self._mobile_entry.get().strip()
        if not mobile:
            self._mobile_indicator.clear()
        elif is_valid_mobile(mobile, self._selected_country):
            self._mobile_indicator.set_valid()
        else:
            self._mobile_indicator.set_invalid()

    def _on_closing(self):
        self._result = {'skipped': True, 'closed': True}
        try:
            self._root.destroy()
        except Exception:
            pass

    def _on_send_otp(self):
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        mobile = self._mobile_entry.get().strip()
        if not name:
            self._show_error('Name is required')
            return
        if not is_valid_email(email):
            self._show_error('Valid email is required')
            self._update_email_indicator()
            return
        mobile_error = mobile_digits_error(mobile, self._selected_country)
        if not mobile or mobile_error:
            self._show_error(mobile_error or 'Valid mobile number is required')
            self._update_mobile_indicator()
            return
        if not self._selected_country:
            self._show_error('Please select a country code')
            return
        self._log("OTP", "INFO", "Sending welcome OTP", f"email={email}")
        self._send_btn.config(state='disabled', text='Sending...')
        self._clear_error()
        try:
            result = self.engine.send_otp(email)
            if result.get('success'):
                self._otp_sent = True
                self._log("OTP", "SUCCESS", "Welcome OTP sent successfully", f"email={email}")
                expires_in = result.get('expires_in', 300)
                self._start_otp_timer(expires_in)
                self._otp_entry.config(state='normal')
                self._verify_btn.config(state='normal')
                self._send_btn.config(text='Resend OTP', state='normal')
            else:
                err_detail = result.get('error', result.get('message', 'Failed to send OTP'))
                self._log("OTP", "ERROR", "Welcome OTP send failed", str(err_detail))
                self._show_error('Failed to send OTP. Please check your email address and try again.')
                self._send_btn.config(state='normal', text='Send OTP')
        except Exception as e:
            self._log("OTP", "ERROR", "Welcome OTP send exception", str(e))
            self._show_error('An unexpected error occurred. Please try again later.')
            self._send_btn.config(state='normal', text='Send OTP')

    def _on_verify_otp(self):
        email = self._email_entry.get().strip()
        otp = self._otp_entry.get().strip()
        if not otp or len(otp) < 4:
            self._show_error('Enter the OTP code')
            return
        self._log("OTP", "INFO", "OTP verification started", f"email={email}")
        self._verify_btn.config(state='disabled', text='Verifying...')
        self._clear_error()
        try:
            result = self.engine.verify_otp(email, otp)
            if result.get('success'):
                self._log("OTP", "SUCCESS", "OTP verified successfully", f"email={email}")
                if result.get('customer_exists'):
                    self._handle_existing_customer()
                else:
                    self._complete_onboarding()
            else:
                self._otp_entry.delete(0, 'end')
                err_detail = result.get('error', result.get('message', 'Invalid OTP'))
                self._log("OTP", "ERROR", "OTP verification failed", str(err_detail))
                self._show_error(OTP_INVALID_MESSAGE)
                self._verify_btn.config(state='normal', text='Verify')
                self._otp_entry.focus()
        except ApiError as e:
            if e.status_code and 400 <= e.status_code < 500:
                self._otp_entry.delete(0, 'end')
                err_data = e.data if isinstance(e.data, dict) else {}
                err_msg = err_data.get('message', err_data.get('error', e.message))
                self._log("OTP", "ERROR", "OTP verification failed", str(err_msg))
                self._show_error(OTP_INVALID_MESSAGE)
                self._verify_btn.config(state='normal', text='Verify')
                self._otp_entry.focus()
            else:
                self._log("OTP", "ERROR", "OTP verification server error", str(e))
                self._show_error('An unexpected error occurred. Please try again later.')
                self._verify_btn.config(state='normal', text='Verify')
        except Exception as e:
            self._log("OTP", "ERROR", "OTP verification exception", str(e))
            self._show_error('An unexpected error occurred. Please try again later.')
            self._verify_btn.config(state='normal', text='Verify')

    def _handle_existing_customer(self):
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        self.engine.mark_onboarding_complete()
        self.engine.set_customer_email(email)
        self._status_label.config(text='Customer already exists — opening License Center...', fg=self._primary)
        self._root.update()
        _time.sleep(1)
        self._result = {
            'name': name, 'email': email,
            'onboarding_complete': True, 'trial_consumed': True,
            'customer_exists': True
        }
        self._root.destroy()

    def _complete_onboarding(self):
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        mobile = self._mobile_entry.get().strip()
        company = self._company_entry.get().strip()
        country_code = self._selected_country.get('code', '') if self._selected_country else ''
        hardware_id = self.engine.get_hardware_id()
        self._status_label.config(text='Creating your account...', fg=self._primary)
        self._root.update()
        try:
            register_result = self.engine.register_customer(
                name=name, email=email, mobile=mobile,
                country_code=country_code, hardware_id=hardware_id,
                company_name=company
            )
            if not register_result.get('success'):
                err = register_result.get('message', register_result.get('error', 'Registration failed'))
                self._log("WELCOME", "ERROR", "Registration failed", err)
                self._show_error(err)
                self._verify_btn.config(state='normal', text='Verify')
                return
            self.engine.mark_onboarding_complete()
            self.engine.set_customer_email(email)
            customer_data = {
                'mobile': mobile,
                'country_code': country_code,
                'company_name': company,
                'hardware_id': hardware_id,
            }
            self._result = {
                'name': name,
                'email': email,
                'hardware_id': hardware_id,
                'mobile': mobile,
                'country_code': country_code,
                'company_name': company,
                'customer_data': customer_data,
                'onboarding_complete': True,
                'trial_started': True,
            }
            self._status_label.config(text='Registration complete! Activating trial...', fg=self._success)
            self._root.after(2000, self._root.destroy)
        except Exception as e:
            tb = traceback.format_exc()
            self._log("WELCOME", "ERROR", "Onboarding exception", str(e))
            for tb_line in tb.strip().split("\n"):
                self._log("WELCOME", "ERROR", f"  {tb_line}")
            self._show_error(str(e))
            self._verify_btn.config(state='normal', text='Verify')

    def _show_error(self, msg: str):
        self._error_label.config(text=msg, font=('Segoe UI', 10))

    def _clear_error(self):
        self._error_label.config(text='')

    def _start_otp_timer(self, expires_in: int = 300):
        if self._otp_timer_id is not None:
            self._root.after_cancel(self._otp_timer_id)
            self._otp_timer_id = None
        self._otp_expires_at = _time.time() + expires_in
        self._update_otp_timer()

    def _update_otp_timer(self):
        remaining = int(self._otp_expires_at - _time.time())
        if remaining <= 0:
            self._otp_expires_at = 0.0
            self._status_label.config(text='OTP expired. Request a new OTP.', fg=self._error)
            self._otp_entry.config(state='disabled')
            self._verify_btn.config(state='disabled')
            self._otp_timer_id = None
            return
        self._status_label.config(text=f'OTP sent — expires in {format_timer(remaining)}', fg=self._success)
        self._otp_timer_id = self._root.after(1000, self._update_otp_timer)
