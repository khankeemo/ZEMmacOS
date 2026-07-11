"""Welcome Dialog - Native Tkinter onboarding dialog"""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict
from .client import Client
from .hardware import HardwareFingerprint
from .cache import CacheManager


def _load_api_config() -> Dict:
    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'api-config.json')
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


_COUNTRIES_CACHE: list = []


class WelcomeDialog:
    def __init__(self, client: Client, product_name: Optional[str] = None,
                 cache: Optional[CacheManager] = None):
        self.config = _load_api_config()
        self.client = client
        self.product_name = product_name or self.config.get('product', {}).get('name', '')
        safe_name = self.product_name or 'License'
        self.cache = cache or CacheManager(safe_name)
        self.hardware = HardwareFingerprint.generate_fingerprint()
        self._result: Optional[Dict] = None
        self._root: Optional[tk.Tk] = None
        self._countries = []
        self._selected_country = None
        self._otp_sent = False
        self._trial_enabled = self.config.get('trial', {}).get('enabled', False)

    def is_onboarding_complete(self) -> bool:
        return self.cache.is_onboarding_complete()

    def show(self) -> Dict:
        if not self._trial_enabled:
            return {'skipped': True, 'message': 'Trial onboarding is not enabled'}

        if self.is_onboarding_complete():
            return {'skipped': True, 'message': 'Onboarding already completed'}

        self._result = None
        self._root = tk.Tk()
        self._root.title(self.product_name or 'License')
        self._root.geometry('480x580')
        self._root.resizable(False, False)
        self._root.configure(bg='#f0f2f5')

        self._build_ui()
        self._center_window()
        self._load_countries()

        self._root.mainloop()
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
                          bg='#f0f2f5', fg='#1a1a2e')
        header.pack(pady=(30, 5))

        sub = tk.Label(root, text='Complete your registration to start the trial',
                       font=('Helvetica', 11), bg='#f0f2f5', fg='#6b7280')
        sub.pack(pady=(0, 20))

        frame = tk.Frame(root, bg='#ffffff', bd=1, relief='solid',
                         highlightbackground='#e5e7eb')
        frame.pack(fill='both', expand=True, padx=30, pady=(0, 20))

        padding = {'padx': 20, 'pady': 5}

        tk.Label(frame, text='Name *', font=('Helvetica', 11, 'bold'),
                 fg='#1a1a2e', bg='#ffffff').pack(anchor='w', **padding)
        self._name_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                     bd=1, highlightbackground='#d1d5db')
        self._name_entry.pack(fill='x', padx=20, pady=(0, 10))
        self._name_entry.focus()

        tk.Label(frame, text='Email *', font=('Helvetica', 11, 'bold'),
                 fg='#1a1a2e', bg='#ffffff').pack(anchor='w', **padding)
        self._email_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                      bd=1, highlightbackground='#d1d5db')
        self._email_entry.pack(fill='x', padx=20, pady=(0, 10))

        tk.Label(frame, text='Mobile Number *', font=('Helvetica', 11, 'bold'),
                 fg='#1a1a2e', bg='#ffffff').pack(anchor='w', **padding)

        mobile_frame = tk.Frame(frame, bg='#ffffff')
        mobile_frame.pack(fill='x', padx=20, pady=(0, 10))

        self._country_var = tk.StringVar(value='+91 India')
        self._country_menu = ttk.Combobox(mobile_frame, textvariable=self._country_var,
                                           width=14, state='readonly', font=('Helvetica', 11))
        self._country_menu.pack(side='left')

        self._mobile_entry = tk.Entry(mobile_frame, font=('Helvetica', 12), relief='solid',
                                       bd=1, highlightbackground='#d1d5db')
        self._mobile_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        tk.Label(frame, text='Company (optional)', font=('Helvetica', 11, 'bold'),
                 fg='#6b7280', bg='#ffffff').pack(anchor='w', **padding)
        self._company_entry = tk.Entry(frame, font=('Helvetica', 12), relief='solid',
                                        bd=1, highlightbackground='#d1d5db')
        self._company_entry.pack(fill='x', padx=20, pady=(0, 15))

        self._status_label = tk.Label(frame, text='', font=('Helvetica', 10),
                                       bg='#ffffff', fg='#10b981')
        self._status_label.pack(padx=20, pady=(0, 5))

        self._send_btn = tk.Button(frame, text='Send OTP', font=('Helvetica', 12, 'bold'),
                                    bg='#6366f1', fg='white', relief='flat',
                                    command=self._on_send_otp, cursor='hand2')
        self._send_btn.pack(fill='x', padx=20, pady=(0, 8))

        otp_frame = tk.Frame(frame, bg='#ffffff')
        otp_frame.pack(fill='x', padx=20, pady=(0, 5))

        self._otp_entry = tk.Entry(otp_frame, font=('Helvetica', 16), relief='solid',
                                    bd=1, highlightbackground='#d1d5db',
                                    justify='center', width=10)
        self._otp_entry.pack(side='left', fill='x', expand=True)
        self._otp_entry.config(state='disabled')

        self._verify_btn = tk.Button(otp_frame, text='Verify', font=('Helvetica', 12, 'bold'),
                                      bg='#10b981', fg='white', relief='flat',
                                      command=self._on_verify_otp, cursor='hand2',
                                      state='disabled')
        self._verify_btn.pack(side='left', padx=(8, 0))

        self._error_label = tk.Label(frame, text='', font=('Helvetica', 10),
                                      bg='#ffffff', fg='#ef4444')
        self._error_label.pack(padx=20, pady=(5, 10))

        brand = self.config.get('branding', {}).get('company_name', '') or self.product_name or 'License'
        footer = tk.Label(self._root, text=f'Protected by {brand}',
                          font=('Helvetica', 9), bg='#f0f2f5', fg='#9ca3af')
        footer.pack(side='bottom', pady=(0, 15))

    def _load_countries(self):
        global _COUNTRIES_CACHE
        if _COUNTRIES_CACHE:
            self._set_countries(_COUNTRIES_CACHE)
            return
        try:
            result = self.client.get_countries()
            if result.get('success') and result.get('data'):
                _COUNTRIES_CACHE = result['data']
                self._set_countries(_COUNTRIES_CACHE)
        except Exception:
            self._set_countries([
                {'code': 'IN', 'name': 'India', 'dial': '+91'},
                {'code': 'US', 'name': 'United States', 'dial': '+1'},
                {'code': 'GB', 'name': 'United Kingdom', 'dial': '+44'},
            ])

    def _set_countries(self, countries):
        self._countries = countries
        labels = [f"{c.get('dial', '')} {c.get('name', '')}" for c in countries]
        self._country_menu['values'] = labels
        india_idx = next((i for i, c in enumerate(countries) if c.get('dial') == '+91'), 0)
        self._country_menu.current(india_idx)
        self._selected_country = countries[india_idx]

        def on_select(event):
            idx = self._country_menu.current()
            if 0 <= idx < len(countries):
                self._selected_country = countries[idx]

        self._country_menu.bind('<<ComboboxSelected>>', on_select)

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
            result = self.client.send_otp(email)
            if result.get('success'):
                self._otp_sent = True
                self._status_label.config(text='OTP sent to your email', fg='#10b981')
                self._otp_entry.config(state='normal')
                self._verify_btn.config(state='normal')
                self._send_btn.config(text='Resend OTP', state='normal')
            else:
                self._show_error(result.get('error', 'Failed to send OTP'))
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
            result = self.client.verify_otp(email, otp)
            if result.get('success'):
                self._complete_onboarding()
            else:
                self._show_error(result.get('error', 'Invalid OTP'))
                self._verify_btn.config(state='normal', text='Verify')
        except Exception as e:
            self._show_error(str(e))
            self._verify_btn.config(state='normal', text='Verify')

    def _complete_onboarding(self):
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        mobile = self._mobile_entry.get().strip()
        company = self._company_entry.get().strip()
        country_code = self._selected_country.get('dial', '+91') if self._selected_country else '+91'
        hardware_id = self.hardware['fingerprint']

        self._status_label.config(text='Activating trial...', fg='#6366f1')
        self._root.update()

        try:
            self.client.store_customer(name, email, mobile, country_code, company, hardware_id)
            self.client.start_trial(email, name, {
                'mobile': mobile,
                'country_code': country_code,
                'company_name': company,
                'hardware_id': hardware_id
            })
            self.cache.set_onboarding_complete()

            self._result = {
                'name': name,
                'email': email,
                'hardware_id': hardware_id,
                'onboarding_complete': True
            }
            self._status_label.config(text='Trial activated! You can now use the software.', fg='#10b981')
            self._root.after(2000, self._root.destroy)
        except Exception as e:
            self._show_error(str(e))
            self._verify_btn.config(state='normal', text='Verify')

    def _show_error(self, msg):
        self._error_label.config(text=msg)

    def _clear_error(self):
        self._error_label.config(text='')
