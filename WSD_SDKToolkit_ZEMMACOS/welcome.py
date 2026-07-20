"""Welcome Dialog - tkinter onboarding dialog (reference implementation)"""
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional

from .client import ApiClient
from .hardware import HardwareDetector
from .cache import CacheManager


_COUNTRIES_CACHE: list = []


def _load_api_config() -> Dict[str, Any]:
    cfg_paths = [
        os.path.join(os.path.dirname(__file__), 'config', 'api-config.json'),
        os.path.join(os.getcwd(), 'config', 'api-config.json'),
    ]
    for cfg_path in cfg_paths:
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return {}


class WelcomeDialog:
    def __init__(self, client: ApiClient, product_name: Optional[str] = None,
                 cache: Optional[CacheManager] = None):
        self.config = _load_api_config()
        self.client = client
        self.product_name = product_name or self.config.get('product', {}).get('name', '')
        self.cache = cache or CacheManager(self.config)
        self.hardware = HardwareDetector()
        self._result: Optional[Dict[str, Any]] = None
        self._root: Optional[tk.Toplevel] = None
        self._countries = []
        self._selected_country = None
        self._otp_sent = False
        # Branding from config
        self.branding = self.config.get('branding', {})
        self._primary = self.branding.get('primary_color', '#6366f1')
        self._secondary = self.branding.get('secondary_color', '#4f46e5')
        self._bg = '#f0f2f5'
        self._card_bg = '#ffffff'
        self._text_primary = '#1a1a2e'
        self._text_secondary = '#6b7280'
        self._success = '#10b981'
        self._error = '#ef4444'
        self._border = '#d1d5db'
        # Feature flags
        self._trial_enabled = self.config.get('trial', {}).get('enabled', False)

    def is_onboarding_complete(self) -> bool:
        return self.cache.is_onboarding_complete()

    def show(self) -> Dict[str, Any]:
        if not self._trial_enabled:
            return {'skipped': True, 'message': 'Trial onboarding is not enabled'}
        if self.is_onboarding_complete():
            return {'skipped': True, 'message': 'Onboarding already completed'}
        self._result = None
        self._root = tk.Toplevel()
        self._root.title(self.product_name or 'License')
        self._root.geometry('480x580')
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient()  # Make transient to parent
        self._root.grab_set()   # Modal
        self._root.protocol('WM_DELETE_WINDOW', self._on_closing)
        self._build_ui()
        self._center_window()
        self._load_countries()
        self._root.wait_window()
        return self._result or {'skipped': True}

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
        header = tk.Label(root, text='Welcome', font=('Helvetica', 22, 'bold'),
                          bg=self._bg, fg=self._text_primary)
        header.pack(pady=(30, 5))
        sub = tk.Label(root, text='Complete your registration to start the trial',
                       font=('Helvetica', 11), bg=self._bg, fg=self._text_secondary)
        sub.pack(pady=(0, 20))
        frame = tk.Frame(root, bg=self._card_bg, bd=1, relief='solid',
                         highlightbackground=self._border)
        frame.pack(fill='both', expand=True, padx=30, pady=(0, 20))
        padding = {'padx': 20, 'pady': 5}
        tk.Label(frame, text='Name *', font=('Helvetica', 11, 'bold'),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        self._name_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                     bd=1, highlightbackground=self._border)
        self._name_entry.pack(fill='x', padx=20, pady=(0, 10))
        self._name_entry.focus()
        tk.Label(frame, text='Email *', font=('Helvetica', 11, 'bold'),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        self._email_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                      bd=1, highlightbackground=self._border)
        self._email_entry.pack(fill='x', padx=20, pady=(0, 10))
        tk.Label(frame, text='Mobile Number *', font=('Helvetica', 11, 'bold'),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor='w', **padding)
        mobile_frame = tk.Frame(frame, bg=self._card_bg)
        mobile_frame.pack(fill='x', padx=20, pady=(0, 10))
        self._country_var = tk.StringVar()
        self._country_menu = ttk.Combobox(mobile_frame, textvariable=self._country_var,
                                           width=14, state='readonly', font=('Helvetica', 11))
        self._country_menu.pack(side='left')
        self._mobile_entry = tk.Entry(mobile_frame, font=('Helvetica', 12), relief='solid',
                                       bd=1, highlightbackground=self._border)
        self._mobile_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        tk.Label(frame, text='Company (optional)', font=('Helvetica', 11, 'bold'),
                 fg=self._text_secondary, bg=self._card_bg).pack(anchor='w', **padding)
        self._company_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                        bd=1, highlightbackground=self._border)
        self._company_entry.pack(fill='x', padx=20, pady=(0, 15))
        self._status_label = tk.Label(frame, text='', font=('Helvetica', 10),
                                       bg=self._card_bg, fg=self._success)
        self._status_label.pack(padx=20, pady=(0, 5))
        self._send_btn = tk.Button(frame, text='Send OTP', font=('Helvetica', 12, 'bold'),
                                    bg=self._primary, fg='white', relief='flat',
                                    command=self._on_send_otp, cursor='hand2')
        self._send_btn.pack(fill='x', padx=20, pady=(0, 8))
        otp_frame = tk.Frame(frame, bg=self._card_bg)
        otp_frame.pack(fill='x', padx=20, pady=(0, 5))
        self._otp_entry = tk.Entry(otp_frame, font=('Helvetica', 16), relief='solid',
                                    bd=1, highlightbackground=self._border,
                                    justify='center', width=10)
        self._otp_entry.pack(side='left', fill='x', expand=True)
        self._otp_entry.config(state='disabled')
        self._verify_btn = tk.Button(otp_frame, text='Verify', font=('Helvetica', 12, 'bold'),
                                      bg=self._success, fg='white', relief='flat',
                                      command=self._on_verify_otp, cursor='hand2',
                                      state='disabled')
        self._verify_btn.pack(side='left', padx=(8, 0))
        self._error_label = tk.Label(frame, text='', font=('Helvetica', 10),
                                      bg=self._card_bg, fg=self._error)
        self._error_label.pack(padx=20, pady=(5, 10))
        company = self.branding.get('company_name', '') or self.product_name or 'License'
        footer = tk.Label(self._root, text=f'Protected by {company}',
                          font=('Helvetica', 9), bg=self._bg, fg='#9ca3af')
        footer.pack(side='bottom', pady=(0, 15))

    def _load_countries(self):
        global _COUNTRIES_CACHE
        if _COUNTRIES_CACHE:
            self._set_countries(_COUNTRIES_CACHE)
            return
        try:
            result = self.client._request('countries', {'action': 'list'})
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

        self._country_menu.bind('<<ComboboxSelected>>', on_select)

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
        if not email or '@' not in email:
            self._show_error('Valid email is required')
            return
        if not mobile or len(mobile) < 4:
            self._show_error('Valid mobile number is required')
            return
        if not self._selected_country:
            self._show_error('Please select a country code')
            return
        self._send_btn.config(state='disabled', text='Sending...')
        self._clear_error()
        try:
            result = self.client._request('auth/otp/send', {'email': email})
            if result.get('success'):
                self._otp_sent = True
                self._status_label.config(text='OTP sent to your email', fg=self._success)
                self._otp_entry.config(state='normal')
                self._verify_btn.config(state='normal')
                self._send_btn.config(text='Resend OTP', state='normal')
            else:
                self._show_error(result.get('error', result.get('message', 'Failed to send OTP')))
                self._send_btn.config(state='normal', text='Send OTP')
        except Exception as e:
            self._show_error(str(e))
            self._send_btn.config(state='normal', text='Send OTP')

    def _on_verify_otp(self):
        email = self._email_entry.get().strip()
        otp = self._otp_entry.get().strip()
        if not otp or len(otp) < 4:
            self._show_error('Enter the OTP code')
            return
        self._verify_btn.config(state='disabled', text='Verifying...')
        self._clear_error()
        try:
            result = self.client._request('auth/otp/verify', {'email': email, 'otp': otp})
            if result.get('success'):
                self._complete_onboarding()
            else:
                self._show_error(result.get('error', result.get('message', 'Invalid OTP')))
                self._verify_btn.config(state='normal', text='Verify')
        except Exception as e:
            self._show_error(str(e))
            self._verify_btn.config(state='normal', text='Verify')

    def _complete_onboarding(self):
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        mobile = self._mobile_entry.get().strip()
        company = self._company_entry.get().strip()
        country_code = self._selected_country.get('code', '') if self._selected_country else ''
        hardware_id = self.hardware.get_fingerprint()
        self._status_label.config(text='Completing registration...', fg=self._primary)
        self._root.update()
        try:
            self.client._request('customer/register', {
                'name': name, 'email': email, 'mobile': mobile,
                'country_code': country_code, 'company_name': company,
                'hardware_id': hardware_id
            })
            # Fetch trial status from server — server decides if trial is granted
            trial_result = self.client.get_trial_status(hardware_id)
            trial_data = trial_result.get('data', {})
            if not trial_data.get('has_trial'):
                # Request trial from server — server enforces business rules
                self.client.start_trial(email, name, {
                    'mobile': mobile, 'country_code': country_code,
                    'company_name': company, 'hardware_id': hardware_id
                })
            self.cache.set_onboarding_complete()
            self._result = {
                'name': name, 'email': email, 'hardware_id': hardware_id,
                'onboarding_complete': True
            }
            self._status_label.config(text='Registration complete! You can now use the software.', fg=self._success)
            self._root.after(2000, self._root.destroy)
        except Exception as e:
            self._show_error(str(e))
            self._verify_btn.config(state='normal', text='Verify')

    def _show_error(self, msg: str):
        self._error_label.config(text=msg)

    def _clear_error(self):
        self._error_label.config(text='')
