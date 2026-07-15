"""Activation Dialog - standalone license activation window"""
import json
import os
import platform
import socket
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, List, Optional

from .client import ApiClient
from .hardware import HardwareDetector
from .cache import CacheManager


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


class ActivationDialog:
    def __init__(self, client: ApiClient, product_name: Optional[str] = None,
                 cache: Optional[CacheManager] = None):
        self.config = _load_api_config()
        self.client = client
        self.product_name = product_name or self.config.get('product', {}).get('name', '')
        self.cache = cache or CacheManager(self.config)
        self.hardware = HardwareDetector()
        self._root: Optional[tk.Toplevel] = None
        self._hardware_id: Optional[str] = None
        self._device_name: str = socket.gethostname()
        self._platform: str = platform.system() or 'Unknown'
        self._license_key: Optional[str] = None
        self._validate_data: Optional[Dict[str, Any]] = None
        self._trial_data: Optional[Dict[str, Any]] = None
        self._activated: bool = False
        self._cancelled: bool = False
        self._customer_data: Dict[str, str] = {}
        self._customer_name_var = tk.StringVar(value='')
        self._customer_email_var = tk.StringVar(value='')
        self._customer_phone_var = tk.StringVar(value='')
        self._products: List[Dict[str, Any]] = []
        self._plans_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._product_ids: List[str] = []
        self._plan_ids: List[str] = []
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

    def show(self) -> Dict[str, Any]:
        self._root = tk.Toplevel()
        self._root.title('UNIVERSAL LICENSE ACTIVATION')
        self._root.geometry('620x760')
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_closing)
        self._build_ui()
        self._center_window()
        self._root.after(500, self._detect_hardware)
        self._root.wait_window()
        return {
            'activated': self._activated,
            'cancelled': self._cancelled,
            'license_key': self._license_key,
        }

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

        header_frame = tk.Frame(root, bg=self._bg)
        header_frame.pack(fill='x', padx=30, pady=(25, 5))
        tk.Label(header_frame, text='UNIVERSAL LICENSE ACTIVATION',
                 font=('Helvetica', 20, 'bold'), bg=self._bg, fg=self._text_primary).pack(anchor='w')
        tk.Label(header_frame, text='Activate your license on this device',
                 font=('Helvetica', 10), bg=self._bg, fg=self._text_secondary).pack(anchor='w', pady=(2, 0))

        canvas = tk.Canvas(root, bg=self._bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self._bg)
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw', width=590)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True, padx=(30, 0), pady=(0, 10))
        scrollbar.pack(side='right', fill='y', padx=(0, 30), pady=(0, 10))

        # Hardware Section
        self._hw_frame = tk.LabelFrame(scroll_frame, text='Hardware', font=('Helvetica', 11, 'bold'),
                                        fg=self._text_primary, bg=self._card_bg,
                                        relief='solid', bd=1, padx=15, pady=10)
        self._hw_frame.pack(fill='x', pady=(0, 10))

        self._hw_status = tk.Label(self._hw_frame, text='Fetching hardware information...',
                                    font=('Helvetica', 10), bg=self._card_bg, fg=self._text_secondary)
        self._hw_status.pack(anchor='w', pady=(0, 8))

        hw_info_frame = tk.Frame(self._hw_frame, bg=self._card_bg)
        hw_info_frame.pack(fill='x')
        self._hw_id_label = tk.Label(hw_info_frame, text='Hardware ID: --',
                                      font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._hw_id_label.pack(anchor='w')
        self._hw_device_label = tk.Label(hw_info_frame, text=f'Device: {self._device_name}',
                                          font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._hw_device_label.pack(anchor='w')
        self._hw_platform_label = tk.Label(hw_info_frame, text=f'Platform: {self._platform}',
                                            font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._hw_platform_label.pack(anchor='w')
        self._hw_device_bound_label = tk.Label(hw_info_frame, text='Device Bound: No',
                                                font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._hw_device_bound_label.pack(anchor='w')

        # Customer Section
        self._customer_frame = tk.LabelFrame(scroll_frame, text='Customer', font=('Helvetica', 11, 'bold'),
                                              fg=self._text_primary, bg=self._card_bg,
                                              relief='solid', bd=1, padx=15, pady=10)
        self._customer_frame.pack(fill='x', pady=(0, 10))

        cname_row = tk.Frame(self._customer_frame, bg=self._card_bg)
        cname_row.pack(fill='x', pady=(0, 6))
        tk.Label(cname_row, text='Customer Name:', font=('Helvetica', 9, 'bold'),
                 bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._customer_name_entry = tk.Entry(cname_row, textvariable=self._customer_name_var,
                                              font=('Helvetica', 9), relief='solid', bd=1,
                                              highlightbackground=self._border, state='disabled')
        self._customer_name_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        cemail_row = tk.Frame(self._customer_frame, bg=self._card_bg)
        cemail_row.pack(fill='x', pady=(0, 6))
        tk.Label(cemail_row, text='Email:', font=('Helvetica', 9, 'bold'),
                 bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._customer_email_entry = tk.Entry(cemail_row, textvariable=self._customer_email_var,
                                               font=('Helvetica', 9), relief='solid', bd=1,
                                               highlightbackground=self._border, state='disabled')
        self._customer_email_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        cphone_row = tk.Frame(self._customer_frame, bg=self._card_bg)
        cphone_row.pack(fill='x', pady=(0, 6))
        tk.Label(cphone_row, text='Mobile Number:', font=('Helvetica', 9, 'bold'),
                 bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._customer_phone_entry = tk.Entry(cphone_row, textvariable=self._customer_phone_var,
                                               font=('Helvetica', 9), relief='solid', bd=1,
                                               highlightbackground=self._border, state='disabled')
        self._customer_phone_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Trial Section
        self._trial_frame = tk.LabelFrame(scroll_frame, text='Trial', font=('Helvetica', 11, 'bold'),
                                           fg=self._text_primary, bg=self._card_bg,
                                           relief='solid', bd=1, padx=15, pady=10)
        self._trial_frame.pack(fill='x', pady=(0, 10))

        self._trial_started_label = tk.Label(self._trial_frame, text='Trial Started: --',
                                              font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._trial_started_label.pack(anchor='w')
        self._trial_ends_label = tk.Label(self._trial_frame, text='Trial Ends: --',
                                           font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._trial_ends_label.pack(anchor='w')
        self._trial_days_label = tk.Label(self._trial_frame, text='Days Remaining: --',
                                           font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._trial_days_label.pack(anchor='w')
        self._trial_status_label = tk.Label(self._trial_frame, text='Trial Status: --',
                                             font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._trial_status_label.pack(anchor='w')

        # License Section
        self._license_frame = tk.LabelFrame(scroll_frame, text='License', font=('Helvetica', 11, 'bold'),
                                             fg=self._text_primary, bg=self._card_bg,
                                             relief='solid', bd=1, padx=15, pady=10)
        self._license_frame.pack(fill='x', pady=(0, 10))

        # Product Combobox
        product_row = tk.Frame(self._license_frame, bg=self._card_bg)
        product_row.pack(fill='x', pady=(0, 6))
        tk.Label(product_row, text='Product:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._product_combo = ttk.Combobox(product_row, font=('Helvetica', 9),
                                            state='disabled', width=40)
        self._product_combo.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self._product_combo.bind('<<ComboboxSelected>>', self._on_product_selected)

        # Plan Combobox
        plan_row = tk.Frame(self._license_frame, bg=self._card_bg)
        plan_row.pack(fill='x', pady=(0, 6))
        tk.Label(plan_row, text='Plan:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._plan_combo = ttk.Combobox(plan_row, font=('Helvetica', 9),
                                         state='disabled', width=40)
        self._plan_combo.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # License Key Entry
        lk_row = tk.Frame(self._license_frame, bg=self._card_bg)
        lk_row.pack(fill='x', pady=(0, 6))
        tk.Label(lk_row, text='License Key:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._license_entry = tk.Entry(lk_row, font=('Courier', 10), relief='solid',
                                        bd=1, highlightbackground=self._border, state='disabled')
        self._license_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # License Expiry
        expiry_row = tk.Frame(self._license_frame, bg=self._card_bg)
        expiry_row.pack(fill='x', pady=(0, 6))
        tk.Label(expiry_row, text='License Expiry:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._expiry_var = tk.StringVar(value='--')
        self._expiry_label = tk.Label(expiry_row, textvariable=self._expiry_var,
                                       font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._expiry_label.pack(side='left', padx=(8, 0))

        # Activation Status
        act_row = tk.Frame(self._license_frame, bg=self._card_bg)
        act_row.pack(fill='x', pady=(0, 6))
        tk.Label(act_row, text='Activation Status:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._activation_var = tk.StringVar(value='Not activated')
        self._activation_label = tk.Label(act_row, textvariable=self._activation_var,
                                           font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._activation_label.pack(side='left', padx=(8, 0))

        # Max Devices Info
        dev_row = tk.Frame(self._license_frame, bg=self._card_bg)
        dev_row.pack(fill='x', pady=(0, 6))
        tk.Label(dev_row, text='Device Limit:', font=('Helvetica', 9, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._device_limit_var = tk.StringVar(value='-- / --')
        self._device_limit_label = tk.Label(dev_row, textvariable=self._device_limit_var,
                                              font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary)
        self._device_limit_label.pack(side='left', padx=(8, 0))

        # Buttons
        btn_frame = tk.Frame(scroll_frame, bg=self._bg)
        btn_frame.pack(fill='x', pady=(5, 10))

        self._refresh_btn = tk.Button(btn_frame, text='Refresh', font=('Helvetica', 11, 'bold'),
                                       bg=self._secondary, fg='white', relief='flat',
                                       command=self._on_refresh, cursor='hand2', state='disabled')
        self._refresh_btn.pack(side='left', padx=(0, 10))

        self._activate_btn = tk.Button(btn_frame, text='Activate License', font=('Helvetica', 11, 'bold'),
                                        bg=self._primary, fg='white', relief='flat',
                                        command=self._on_activate, cursor='hand2', state='disabled')
        self._activate_btn.pack(side='left')

        # Status Label
        self._status_label = tk.Label(scroll_frame, text='Detecting hardware...',
                                       font=('Helvetica', 10), bg=self._bg, fg=self._text_secondary)
        self._status_label.pack(anchor='w', pady=(0, 5))

        # Permanent Hardware Binding Warning
        warning_frame = tk.LabelFrame(scroll_frame, text='Device Binding Notice',
                                       font=('Helvetica', 11, 'bold'),
                                       fg=self._error, bg=self._card_bg,
                                       relief='solid', bd=1, padx=15, pady=10)
        warning_frame.pack(fill='x', pady=(0, 10))
        support_email = (self.config.get('branding', {})
                         .get('support_email', 'support@websmithdigital.com'))
        tk.Label(warning_frame,
                 text='This device will be permanently linked to this license.',
                 font=('Helvetica', 9), bg=self._card_bg, fg=self._text_primary,
                 wraplength=520, justify='left').pack(anchor='w', pady=(0, 4))
        tk.Label(warning_frame,
                 text='For device replacement or hardware unbinding, contact:',
                 font=('Helvetica', 9), bg=self._card_bg, fg=self._text_secondary,
                 wraplength=520, justify='left').pack(anchor='w')
        tk.Label(warning_frame,
                 text=support_email,
                 font=('Helvetica', 9, 'underline'), bg=self._card_bg,
                 fg=self._primary, cursor='hand2',
                 wraplength=520, justify='left').pack(anchor='w')

        company = self.branding.get('company_name', '') or self.product_name or 'License'
        footer = tk.Label(root, text=f'Protected by {company}',
                          font=('Helvetica', 9), bg=self._bg, fg='#9ca3af')
        footer.pack(side='bottom', pady=(0, 15))

    def _detect_hardware(self):
        try:
            self._hardware_id = self.hardware.get_fingerprint()
            if not self._hardware_id:
                self._hw_status.config(text='Unable to detect hardware. Please retry.', fg=self._error)
                self._set_controls_disabled(True)
                self._status_label.config(text='Hardware detection failed. Close and retry.', fg=self._error)
                return
            self._hw_id_label.config(text=f'Hardware ID: {self._hardware_id}')
            self._hw_status.config(text='Hardware verified. Activation available.', fg=self._success)
            self._status_label.config(text='Loading products...', fg=self._text_secondary)
            self._root.update()
            self._fetch_products()
        except Exception as e:
            self._hw_status.config(text=f'Unable to detect hardware: {str(e)}', fg=self._error)
            self._set_controls_disabled(True)
            self._status_label.config(text=f'Hardware error: {str(e)}', fg=self._error)

    def _fetch_products(self):
        try:
            result = self.client.get_products()
            products = result.get('products', []) if result.get('success') else []
            if not products:
                self._status_label.config(text='No products available from server.', fg=self._error)
                self._set_controls_disabled(True)
                return
            self._products = products
            self._plans_cache = {}
            names = []
            self._product_ids = []
            for p in products:
                pid = p.get('id', p.get('product_id', ''))
                name = p.get('name', '')
                names.append(name)
                self._product_ids.append(pid)
                plans = p.get('plans', [])
                self._plans_cache[pid] = plans
            self._product_combo['values'] = names
            if names:
                self._product_combo.set(names[0])
                self._on_product_selected()
            self._set_controls_disabled(False)
            self._status_label.config(
                text=f'Loaded {len(products)} product(s). Select product, plan, enter license key, click Refresh.',
                fg=self._text_secondary
            )
        except Exception as e:
            self._status_label.config(text=f'Failed to load products: {str(e)}', fg=self._error)
            self._set_controls_disabled(True)

    def _on_product_selected(self, event=None):
        name = self._product_combo.get()
        pid = ''
        for i, pname in enumerate(self._product_combo['values']):
            if pname == name:
                if i < len(self._product_ids):
                    pid = self._product_ids[i]
                break
        plans = self._plans_cache.get(pid, [])
        plan_names = [pl.get('name', '') for pl in plans]
        self._plan_ids = [str(pl.get('id', '')) for pl in plans]
        self._plan_combo['values'] = plan_names
        if plan_names:
            self._plan_combo.set(plan_names[0])
        else:
            self._plan_combo.set('')
        self._plan_combo.state(['!disabled'] if plan_names else ['disabled'])

    def _set_controls_disabled(self, disabled: bool):
        state = 'disabled' if disabled else 'normal'
        self._refresh_btn.config(state=state)
        self._activate_btn.config(state=state)
        self._license_entry.config(state=state)
        self._product_combo.state(['disabled'] if disabled else ['!disabled'])
        if not disabled and self._plan_combo['values']:
            self._plan_combo.state(['!disabled'])
        else:
            self._plan_combo.state(['disabled'])
        if hasattr(self, '_customer_name_entry'):
            self._customer_name_entry.config(state=state)
            self._customer_email_entry.config(state=state)
            self._customer_phone_entry.config(state=state)

    def _on_closing(self):
        if not self._activated:
            self._cancelled = True
        try:
            self._root.destroy()
        except Exception:
            pass
        if self._cancelled:
            sys.exit(0)

    def _get_selected_product_id(self) -> str:
        name = self._product_combo.get()
        for i, pname in enumerate(self._product_combo['values']):
            if pname == name:
                if i < len(self._product_ids):
                    return self._product_ids[i]
        return ''

    def _get_selected_plan_id(self) -> str:
        name = self._plan_combo.get()
        for i, pname in enumerate(self._plan_combo['values']):
            if pname == name:
                if i < len(self._plan_ids):
                    return self._plan_ids[i]
        return ''

    def _get_selected_plan_name(self) -> str:
        return self._plan_combo.get()

    def _on_refresh(self):
        license_key = self._license_entry.get().strip()
        if not license_key:
            self._status_label.config(text='Please enter a license key.', fg=self._error)
            return
        selected_product = self._product_combo.get()
        selected_plan = self._plan_combo.get()
        if not selected_product:
            self._status_label.config(text='Please select a product.', fg=self._error)
            return
        if not selected_plan:
            self._status_label.config(text='Please select a plan.', fg=self._error)
            return
        self._status_label.config(text='Validating license...', fg=self._text_secondary)
        self._refresh_btn.config(state='disabled', text='Validating...')
        self._root.update()
        try:
            result = self.client.validate_license(license_key, self._hardware_id)
            if result.get('valid') or result.get('data', {}).get('valid'):
                data = result.get('data', result)
                api_product = data.get('product_name', '')
                api_plan = data.get('plan', '')
                if api_product and api_product != selected_product:
                    self._status_label.config(
                        text=f'Product mismatch: license is for "{api_product}", selected "{selected_product}".',
                        fg=self._error
                    )
                    return
                if api_plan and api_plan != selected_plan:
                    self._status_label.config(
                        text=f'Plan mismatch: license is for "{api_plan}", selected "{selected_plan}".',
                        fg=self._error
                    )
                    return
                self._validate_data = data
                self._license_key = license_key
                self._update_ui(data)
                self._status_label.config(text='License validated successfully.', fg=self._success)
                self._activate_btn.config(state='normal')
                self._fetch_trial_status()
            else:
                err_msg = result.get('message', result.get('error', 'License validation failed'))
                self._status_label.config(text=f'Validation failed: {err_msg}', fg=self._error)
        except Exception as e:
            self._status_label.config(text=f'Validation error: {str(e)}', fg=self._error)
        finally:
            self._refresh_btn.config(state='normal', text='Refresh')

    def _fetch_trial_status(self):
        try:
            trial_result = self.client.get_trial_status(self._hardware_id)
            if isinstance(trial_result, dict) and trial_result.get('data', {}).get('has_trial'):
                data = trial_result['data']
                self._trial_data = data
                self._trial_started_label.config(
                    text=f"Trial Started: {data.get('started_at', '--')}"
                )
                self._trial_ends_label.config(
                    text=f"Trial Ends: {data.get('expiry_date', '--')}"
                )
                self._trial_days_label.config(
                    text=f"Days Remaining: {data.get('days_left', 0)}"
                )
                status = data.get('status', 'unknown')
                status_color = self._success if status == 'active' else self._error
                self._trial_status_label.config(
                    text=f'Trial Status: {status.capitalize()}',
                    fg=status_color
                )
        except Exception:
            self._trial_status_label.config(text='Trial Status: Unavailable', fg=self._text_secondary)

    def _update_ui(self, data: Dict[str, Any]):
        cname = data.get('customer_name') or data.get('customerName', '')
        cemail = data.get('customer_email') or data.get('customerEmail', '')
        cphone = data.get('customer_phone') or data.get('customerPhone', '')
        self._customer_name_var.set(cname)
        self._customer_email_var.set(cemail)
        self._customer_phone_var.set(cphone)
        for entry in (self._customer_name_entry, self._customer_email_entry,
                       self._customer_phone_entry):
            entry.config(state='normal')
        self._customer_data = {'name': cname, 'email': cemail, 'phone': cphone}

        api_product = data.get('product_name', '')
        api_plan = data.get('plan', '')
        if api_product:
            self._product_combo.set(api_product)
        if api_plan:
            self._plan_combo.set(api_plan)
        expiry = data.get('expiry_date', '--')
        if expiry and 'T' in expiry:
            expiry = expiry.split('T')[0]
        self._expiry_var.set(expiry)

        max_dev = data.get('max_devices', '--')
        dev_count = data.get('device_count', data.get('active_devices', 0))
        self._device_limit_var.set(f'{dev_count} / {max_dev}')

        status = data.get('status', 'unknown')
        if status == 'active':
            self._activation_var.set('Activated')
            self._activation_label.config(fg=self._success)
            self._hw_device_bound_label.config(text='Device Bound: Yes')
        else:
            self._activation_var.set(status.capitalize())
            self._activation_label.config(fg=self._text_secondary)

    def _sync_customer(self) -> bool:
        name = self._customer_name_var.get().strip()
        email = self._customer_email_var.get().strip()
        phone = self._customer_phone_var.get().strip()
        if not name or not email:
            self._status_label.config(text='Customer name and email are required.', fg=self._error)
            return False
        try:
            result = self.client.update_customer(name, email, phone, self._hardware_id)
            if result.get('success'):
                self._customer_data = {'name': name, 'email': email, 'phone': phone}
                return True
            err = result.get('error', 'Failed to save customer')
            self._status_label.config(text=f'Customer sync failed: {err}', fg=self._error)
            return False
        except Exception as e:
            self._status_label.config(text=f'Customer sync error: {str(e)}', fg=self._error)
            return False

    def _on_activate(self):
        license_key = self._license_entry.get().strip()
        if not license_key:
            self._status_label.config(text='Please enter a license key.', fg=self._error)
            return
        if not self._hardware_id:
            self._status_label.config(text='Hardware not detected. Please restart.', fg=self._error)
            return
        if not self._validate_data:
            self._status_label.config(text='Please click Refresh first to validate the license.', fg=self._error)
            return
        max_dev = self._validate_data.get('max_devices', 0)
        dev_count = self._validate_data.get('device_count', self._validate_data.get('active_devices', 0))
        if max_dev and dev_count >= max_dev:
            self._status_label.config(
                text=f'Device limit reached ({dev_count}/{max_dev}). Deactivate another device first.',
                fg=self._error
            )
            return
        self._status_label.config(text='Syncing customer data...', fg=self._text_secondary)
        self._root.update()
        if not self._sync_customer():
            self._activate_btn.config(state='normal', text='Activate License')
            return
        self._status_label.config(text='Activating license...', fg=self._text_secondary)
        self._activate_btn.config(state='disabled', text='Activating...')
        self._root.update()
        try:
            result = self.client.activate_license(license_key, self._hardware_id)
            if result.get('success') or result.get('data', {}).get('success'):
                data = result.get('data', result)
                self._activated = True
                self._license_key = license_key
                self._activation_var.set('Activated')
                self._activation_label.config(fg=self._success)
                self._hw_device_bound_label.config(text='Device Bound: Yes')
                msg = data.get('message', 'License activated successfully')
                if data.get('already_activated'):
                    msg = 'License already activated on this device'
                self._status_label.config(text=msg, fg=self._success)
                expiry = data.get('expiry_date', '--')
                if expiry and 'T' in expiry:
                    expiry = expiry.split('T')[0]
                self._expiry_var.set(expiry)
                dcount = data.get('device_count', 0)
                self._device_limit_var.set(f'{dcount} / {max_dev}')
                self.cache.invalidate_license_status()
                self._root.after(1000, lambda: self._on_refresh())
            else:
                err = result.get('message', result.get('error', 'Activation failed'))
                self._status_label.config(text=f'Activation failed: {err}', fg=self._error)
        except Exception as e:
            self._status_label.config(text=f'Activation error: {str(e)}', fg=self._error)
        finally:
            self._activate_btn.config(state='normal', text='Activate License')
