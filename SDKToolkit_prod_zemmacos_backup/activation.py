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


class StatusBadge(tk.Canvas):
    def __init__(self, parent, text, color, bg):
        self._color = color
        self._text = text
        super().__init__(parent, width=0, height=22, bg=bg, highlightthickness=0)
        self._draw(text, color)

    def _draw(self, text, color):
        self.delete('all')
        self._color = color
        self._text = text
        w = len(text) * 8 + 20
        r = 4
        self.config(width=w)
        self.create_rounded_rect(0, 0, w, 22, r, fill=color, outline=color)
        self.create_text(w // 2, 11, text=text, fill='white',
                          font=('Segoe UI', 8, 'bold'))

    def set(self, text, color):
        self._draw(text, color)

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
                  x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
                  x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kw)


class ActionButton(tk.Canvas):
    def __init__(self, parent, text, color, command, width=160, height=36, **kw):
        self._color = color
        self._hover_color = self._adjust_color(color, 1.15)
        self._disabled_color = '#9ca3af'
        self._cmd = command
        self._disabled = False
        self._loading = False
        self._text = text
        r = 6
        super().__init__(parent, width=width, height=height, bg=parent.cget('bg'),
                          highlightthickness=0, **kw)
        self._width = width
        self._height = height
        self._r = r
        self._draw_normal()
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonRelease-1>', lambda e: self._draw_normal() if not self._disabled and not self._loading else None)
        self.configure(cursor='hand2')

    @staticmethod
    def _adjust_color(hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _draw_normal(self):
        self.delete('all')
        c = self._disabled_color if self._disabled else self._color
        self.create_rounded_rect(0, 0, self._width, self._height, self._r, fill=c, outline=c)
        text = 'Loading...' if self._loading else self._text
        self.create_text(self._width // 2, self._height // 2, text=text,
                          fill='white', font=('Segoe UI', 10, 'bold'))

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
                  x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
                  x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kw)

    def _on_enter(self, event):
        if not self._disabled and not self._loading:
            self._draw_hover()

    def _on_leave(self, event):
        if not self._disabled and not self._loading:
            self._draw_normal()

    def _draw_hover(self):
        self.delete('all')
        c = self._hover_color
        self.create_rounded_rect(0, 0, self._width, self._height, self._r, fill=c, outline=c)
        self.create_text(self._width // 2, self._height // 2, text=self._text,
                          fill='white', font=('Segoe UI', 10, 'bold'))

    def _on_click(self, event):
        if not self._disabled and not self._loading:
            self._cmd()

    def set_disabled(self, disabled):
        self._disabled = disabled
        self._draw_normal()

    def set_loading(self, loading):
        self._loading = loading
        self._draw_normal()

    def set_text(self, text):
        self._text = text
        if not self._loading:
            self._draw_normal()


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
        self._init_completed = {'hardware': False, 'products': False}
        self._initialized = False
        self._hardware_ok = False
        self._products_ok = False
        self.branding = self.config.get('branding', {})
        self._primary = '#1e40af'
        self._secondary = '#6b7280'
        self._bg = '#f3f4f6'
        self._card_bg = '#ffffff'
        self._text_primary = '#111827'
        self._text_secondary = '#6b7280'
        self._success = '#16a34a'
        self._warning = '#ea580c'
        self._error = '#dc2626'
        self._border = '#e5e7eb'
        self._badge_inactive = '#9ca3af'
        self._badge_verified = '#16a34a'
        self._badge_bound = '#16a34a'
        self._badge_failed = '#dc2626'

    def show(self) -> Dict[str, Any]:
        self._root = tk.Toplevel()
        self._root.title('UNIVERSAL LICENSE ACTIVATION')
        self._root.geometry('700x760')
        self._root.minsize(560, 680)
        self._root.resizable(True, True)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_closing)
        style = ttk.Style(self._root)
        style.theme_use('clam')
        style.configure('TScrollbar', background=self._card_bg, troughcolor=self._bg,
                         bordercolor=self._border, arrowcolor=self._text_secondary,
                         relief='flat')
        self._build_ui()
        self._center_window()
        self._status_label.config(text='Loading license information...')
        self._set_controls_disabled(True)
        self._root.after(200, self._initialize)
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

    def _make_card(self, parent, title):
        frame = tk.Frame(parent, bg=self._card_bg, highlightbackground=self._border,
                          highlightcolor=self._border, highlightthickness=1)
        header = tk.Frame(frame, bg=self._card_bg)
        header.pack(fill='x', padx=14, pady=(10, 3))
        tk.Label(header, text=title, font=('Segoe UI', 11, 'bold'),
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        sep = tk.Frame(frame, bg=self._border, height=1)
        sep.pack(fill='x', padx=14, pady=(0, 6))
        body = tk.Frame(frame, bg=self._card_bg)
        body.pack(fill='x', padx=14, pady=(0, 10))
        return frame, body

    def _build_ui(self):
        root = self._root

        header_frame = tk.Frame(root, bg=self._bg)
        header_frame.pack(fill='x', padx=24, pady=(24, 6))
        tk.Label(header_frame, text='UNIVERSAL LICENSE ACTIVATION',
                  font=('Segoe UI', 20, 'bold'), bg=self._bg, fg=self._text_primary).pack(anchor='w')
        tk.Label(header_frame, text='Activate your license on this device',
                  font=('Segoe UI', 10), bg=self._bg, fg=self._text_secondary).pack(anchor='w', pady=(1, 0))

        canvas = tk.Canvas(root, bg=self._bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self._bg)
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self._canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True, padx=(24, 0), pady=(0, 10))
        scrollbar.pack(side='right', fill='y', padx=(0, 24), pady=(0, 10))

        def _on_canvas_configure(event):
            canvas.itemconfig(self._canvas_window, width=event.width - 4)
        canvas.bind('<Configure>', _on_canvas_configure)

        _F = ('Segoe UI', 9)
        _FB = ('Segoe UI', 9, 'bold')
        _FC = ('Courier', 10)

        # Hardware Card
        hw_card, hw_body = self._make_card(scroll_frame, 'Hardware')

        self._hw_status = tk.Label(hw_body, text='Fetching hardware information...',
                                    font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._hw_status.pack(anchor='w', pady=(0, 6))

        hw_info_frame = tk.Frame(hw_body, bg=self._card_bg)
        hw_info_frame.pack(fill='x')
        self._hw_id_label = tk.Label(hw_info_frame, text='Hardware ID: --',
                                      font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._hw_id_label.pack(anchor='w', pady=(1, 0))
        self._hw_device_label = tk.Label(hw_info_frame, text=f'Device: {self._device_name}',
                                          font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._hw_device_label.pack(anchor='w', pady=(1, 0))
        self._hw_platform_label = tk.Label(hw_info_frame, text=f'Platform: {self._platform}',
                                            font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._hw_platform_label.pack(anchor='w', pady=(1, 0))

        bound_row = tk.Frame(hw_body, bg=self._card_bg)
        bound_row.pack(fill='x', pady=(4, 0))
        tk.Label(bound_row, text='Device Bound:', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._hw_bound_badge = StatusBadge(bound_row, 'Not Bound', self._badge_inactive, self._card_bg)
        self._hw_bound_badge.pack(side='left', padx=(6, 0))

        hw_card.pack(fill='x', pady=(0, 10))

        # Customer Card
        c_card, c_body = self._make_card(scroll_frame, 'Customer')

        cname_row = tk.Frame(c_body, bg=self._card_bg)
        cname_row.pack(fill='x', pady=(0, 6))
        tk.Label(cname_row, text='Customer Name', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._customer_name_entry = tk.Entry(cname_row, textvariable=self._customer_name_var,
                                              font=_F, relief='solid', bd=1,
                                              highlightbackground=self._border, state='disabled')
        self._customer_name_entry.pack(fill='x', pady=(2, 0))

        cemail_row = tk.Frame(c_body, bg=self._card_bg)
        cemail_row.pack(fill='x', pady=(0, 6))
        tk.Label(cemail_row, text='Email', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._customer_email_entry = tk.Entry(cemail_row, textvariable=self._customer_email_var,
                                               font=_F, relief='solid', bd=1,
                                               highlightbackground=self._border, state='disabled')
        self._customer_email_entry.pack(fill='x', pady=(2, 0))

        cphone_row = tk.Frame(c_body, bg=self._card_bg)
        cphone_row.pack(fill='x', pady=(0, 0))
        tk.Label(cphone_row, text='Mobile Number', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._customer_phone_entry = tk.Entry(cphone_row, textvariable=self._customer_phone_var,
                                               font=_F, relief='solid', bd=1,
                                               highlightbackground=self._border, state='disabled')
        self._customer_phone_entry.pack(fill='x', pady=(2, 0))

        c_card.pack(fill='x', pady=(0, 10))

        # Trial Card
        t_card, t_body = self._make_card(scroll_frame, 'Trial')

        trial_grid = tk.Frame(t_body, bg=self._card_bg)
        trial_grid.pack(fill='x')
        self._trial_started_label = tk.Label(trial_grid, text='Started: --',
                                              font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._trial_started_label.pack(anchor='w', pady=(1, 0))
        self._trial_ends_label = tk.Label(trial_grid, text='Ends: --',
                                           font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._trial_ends_label.pack(anchor='w', pady=(1, 0))
        self._trial_days_label = tk.Label(trial_grid, text='Days Remaining: --',
                                           font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._trial_days_label.pack(anchor='w', pady=(1, 0))

        tstatus_row = tk.Frame(t_body, bg=self._card_bg)
        tstatus_row.pack(fill='x', pady=(4, 0))
        tk.Label(tstatus_row, text='Trial Status:', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._trial_badge = StatusBadge(tstatus_row, '--', self._badge_inactive, self._card_bg)
        self._trial_badge.pack(side='left', padx=(6, 0))

        t_card.pack(fill='x', pady=(0, 10))

        # License Card
        l_card, l_body = self._make_card(scroll_frame, 'License')

        product_row = tk.Frame(l_body, bg=self._card_bg)
        product_row.pack(fill='x', pady=(0, 6))
        tk.Label(product_row, text='Product', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._product_combo = ttk.Combobox(product_row, font=_F, state='disabled')
        self._product_combo.pack(fill='x', pady=(2, 0))
        self._product_combo.bind('<<ComboboxSelected>>', self._on_product_selected)

        plan_row = tk.Frame(l_body, bg=self._card_bg)
        plan_row.pack(fill='x', pady=(0, 6))
        tk.Label(plan_row, text='Plan', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._plan_combo = ttk.Combobox(plan_row, font=_F, state='disabled')
        self._plan_combo.pack(fill='x', pady=(2, 0))

        lk_row = tk.Frame(l_body, bg=self._card_bg)
        lk_row.pack(fill='x', pady=(0, 6))
        tk.Label(lk_row, text='License Key', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._license_entry = tk.Entry(lk_row, font=_FC, relief='solid',
                                        bd=1, highlightbackground=self._border, state='disabled')
        self._license_entry.pack(fill='x', pady=(2, 0))

        expiry_row = tk.Frame(l_body, bg=self._card_bg)
        expiry_row.pack(fill='x', pady=(0, 6))
        tk.Label(expiry_row, text='License Expiry', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._expiry_var = tk.StringVar(value='--')
        tk.Label(expiry_row, textvariable=self._expiry_var,
                  font=_F, bg=self._card_bg, fg=self._text_secondary).pack(anchor='w', pady=(2, 0))

        astatus_row = tk.Frame(l_body, bg=self._card_bg)
        astatus_row.pack(fill='x', pady=(0, 6))
        tk.Label(astatus_row, text='Activation Status:', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._activation_badge = StatusBadge(astatus_row, 'Inactive', self._badge_inactive, self._card_bg)
        self._activation_badge.pack(side='left', padx=(6, 0))

        dev_row = tk.Frame(l_body, bg=self._card_bg)
        dev_row.pack(fill='x', pady=(0, 0))
        tk.Label(dev_row, text='Device Limit', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(anchor='w')
        self._device_limit_var = tk.StringVar(value='-- / --')
        tk.Label(dev_row, textvariable=self._device_limit_var,
                  font=_F, bg=self._card_bg, fg=self._text_secondary).pack(anchor='w', pady=(2, 0))

        lic_days_row = tk.Frame(l_body, bg=self._card_bg)
        lic_days_row.pack(fill='x', pady=(4, 0))
        tk.Label(lic_days_row, text='Days Remaining:', font=_FB,
                  bg=self._card_bg, fg=self._text_primary).pack(side='left')
        self._license_days_label = tk.Label(lic_days_row, text='--',
                                              font=_F, bg=self._card_bg, fg=self._text_secondary)
        self._license_days_label.pack(side='left', padx=(6, 0))

        l_card.pack(fill='x', pady=(0, 10))

        # Status label
        self._status_label = tk.Label(scroll_frame, text='Detecting hardware...',
                                       font=_F, bg=self._bg, fg=self._text_secondary)
        self._status_label.pack(anchor='w', pady=(0, 6))

        # Buttons
        btn_frame = tk.Frame(scroll_frame, bg=self._bg)
        btn_frame.pack(fill='x', pady=(0, 10))

        self._refresh_btn = ActionButton(btn_frame, 'Refresh', self._secondary,
                                          self._on_refresh, width=140, height=36)
        self._refresh_btn.pack(side='left', padx=(0, 10))
        self._refresh_btn.set_disabled(True)

        self._activate_btn = ActionButton(btn_frame, 'Activate License', self._primary,
                                           self._on_activate, width=170, height=36)
        self._activate_btn.pack(side='left')
        self._activate_btn.set_disabled(True)

        # Device Binding Notice
        warn_bg = '#fef2f2'
        warn_border = '#fecaca'
        warn_text = '#991b1b'
        warn_text2 = '#7f1d1d'
        warning_frame = tk.Frame(scroll_frame, bg=warn_bg, highlightbackground=warn_border,
                                  highlightcolor=warn_border, highlightthickness=1)
        warning_frame.pack(fill='x', pady=(0, 10))

        warn_header = tk.Frame(warning_frame, bg=warn_bg)
        warn_header.pack(fill='x', padx=14, pady=(10, 3))
        tk.Label(warn_header, text='⚠ Device Binding Notice',
                  font=('Segoe UI', 11, 'bold'), bg=warn_bg, fg=warn_text).pack(anchor='w')

        warn_sep = tk.Frame(warning_frame, bg=warn_border, height=1)
        warn_sep.pack(fill='x', padx=14, pady=(0, 6))

        warn_body = tk.Frame(warning_frame, bg=warn_bg)
        warn_body.pack(fill='x', padx=14, pady=(0, 10))

        support_email = (self.config.get('branding', {})
                         .get('support_email', 'support@websmithdigital.com'))
        tk.Label(warn_body,
                 text='This device will be permanently linked to this license.',
                 font=_F, bg=warn_bg, fg=warn_text2,
                 wraplength=660, justify='left').pack(anchor='w', pady=(0, 3))
        tk.Label(warn_body,
                 text='For device replacement or hardware unbinding, contact:',
                 font=_F, bg=warn_bg, fg=warn_text,
                 wraplength=660, justify='left').pack(anchor='w')
        tk.Label(warn_body,
                 text=support_email,
                 font=('Segoe UI', 9, 'underline'), bg=warn_bg,
                 fg=self._primary, cursor='hand2',
                 wraplength=660, justify='left').pack(anchor='w')

        company = self.branding.get('company_name', '') or self.product_name or 'License'
        footer = tk.Label(root, text=f'Protected by {company}',
                           font=('Segoe UI', 9), bg=self._bg, fg='#9ca3af')
        footer.pack(side='bottom', pady=(0, 14))

    def _initialize(self):
        self._init_completed = {'hardware': False, 'products': False}
        self._root.after(0, self._detect_hardware)
        self._root.after(0, self._fetch_products)

    def _try_enable(self):
        if all(self._init_completed.values()) and not self._initialized:
            self._initialized = True
            if self._hardware_ok and self._products_ok:
                self._set_controls_disabled(False)
                self._status_label.config(
                    text='Initialization complete. Enter license key, click Refresh.',
                    fg=self._text_secondary
                )
            else:
                reasons = []
                if not self._hardware_ok:
                    reasons.append('hardware detection failed')
                if not self._products_ok:
                    reasons.append('no products available')
                self._status_label.config(
                    text=f'Initialization failed: {"; ".join(reasons)}. Close and retry.',
                    fg=self._error
                )

    def _detect_hardware(self):
        try:
            self._hardware_id = self.hardware.get_fingerprint()
            if not self._hardware_id:
                self._hw_status.config(text='Unable to detect hardware. Please retry.', fg=self._error)
                self._status_label.config(text='Hardware detection failed. Close and retry.', fg=self._error)
                self._hardware_ok = False
                return
            self._hw_id_label.config(text=f'Hardware ID: {self._hardware_id}')
            self._hw_status.config(text='Hardware verified. Activation available.', fg=self._success)
            self._hardware_ok = True
        except Exception as e:
            self._hw_status.config(text=f'Unable to detect hardware: {str(e)}', fg=self._error)
            self._status_label.config(text=f'Hardware error: {str(e)}', fg=self._error)
            self._hardware_ok = False
        finally:
            self._init_completed['hardware'] = True
            self._try_enable()

    def _fetch_products(self):
        try:
            result = self.client.get_products()
            products = result.get('products', []) if result.get('success') else result.get('products', [])
            if not products:
                self._status_label.config(text='No products available from server.', fg=self._error)
                self._products_ok = False
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
            self._products_ok = True
            if names:
                self._product_combo.set(names[0])
                self._on_product_selected()
        except Exception as e:
            self._status_label.config(text=f'Failed to load products: {str(e)}', fg=self._error)
            self._products_ok = False
        finally:
            self._init_completed['products'] = True
            self._try_enable()

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
        self._refresh_btn.set_disabled(disabled)
        self._activate_btn.set_disabled(disabled)
        state = 'disabled' if disabled else 'normal'
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
        self._status_label.config(text='Validating license...', fg=self._text_secondary)
        self._refresh_btn.set_loading(True)
        self._root.update()
        try:
            result = self.client.validate_license(license_key, self._hardware_id)
            if result.get('valid') or result.get('data', {}).get('valid'):
                data = result.get('data', result)
                self._validate_data = data
                self._license_key = license_key
                self._update_ui(data)

                # Auto-detect product + plan from validated license data
                api_plan = data.get('plan', '')
                if api_plan:
                    found = False
                    for pid, plans in self._plans_cache.items():
                        for pl in plans:
                            if pl.get('name') == api_plan:
                                for i, pname in enumerate(self._product_combo['values']):
                                    if i < len(self._product_ids) and self._product_ids[i] == pid:
                                        self._product_combo.set(pname)
                                        self._on_product_selected()
                                        self._plan_combo.set(api_plan)
                                        found = True
                                        break
                                if found:
                                    break
                        if found:
                            break

                self._status_label.config(text='License validated successfully. All fields auto-filled.', fg=self._success)
                self._activate_btn.set_disabled(False)
                self._fetch_trial_status()
            else:
                err_msg = result.get('message', result.get('error', 'License validation failed'))
                self._status_label.config(text=f'Validation failed: {err_msg}', fg=self._error)
        except Exception as e:
            self._status_label.config(text=f'Validation error: {str(e)}', fg=self._error)
        finally:
            self._refresh_btn.set_loading(False)

    def _fetch_trial_status(self):
        try:
            trial_result = self.client.get_trial_status(self._hardware_id)
            if isinstance(trial_result, dict) and trial_result.get('data', {}).get('has_trial'):
                data = trial_result['data']
                self._trial_data = data
                self._trial_started_label.config(
                    text=f"Started: {data.get('started_at', '--')}"
                )
                self._trial_ends_label.config(
                    text=f"Ends: {data.get('expiry_date', '--')}"
                )
                self._trial_days_label.config(
                    text=f"Days Remaining: {data.get('days_left', 0)}"
                )
                status = data.get('status', 'unknown')
                status_color = self._badge_verified if status == 'active' else self._badge_failed
                label = 'Active' if status == 'active' else status.capitalize()
                self._trial_badge.set(label, status_color)
        except Exception:
            self._trial_badge.set('Unavailable', self._badge_inactive)

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

        days_left = data.get('days_left', data.get('days_remaining', 0))
        if days_left and days_left > 0:
            self._license_days_label.config(
                text=f'{days_left} day(s) left',
                fg=self._success
            )
        elif days_left == 0 and expiry and expiry != '--':
            self._license_days_label.config(text='Expired', fg=self._error)
        else:
            self._license_days_label.config(text='--', fg=self._text_secondary)

        max_dev = data.get('max_devices', '--')
        dev_count = data.get('device_count', data.get('active_devices', 0))
        self._device_limit_var.set(f'{dev_count} / {max_dev}')

        status = data.get('status', 'unknown')
        if status == 'active':
            self._activation_badge.set('Bound', self._badge_bound)
        else:
            self._activation_badge.set(status.capitalize(), self._badge_inactive)

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
            self._activate_btn.set_disabled(False)
            self._activate_btn.set_text('Activate License')
            return
        self._status_label.config(text='Activating license...', fg=self._text_secondary)
        self._activate_btn.set_loading(True)
        self._root.update()
        try:
            result = self.client.activate_license(license_key, self._hardware_id)
            if result.get('success') or result.get('data', {}).get('success'):
                data = result.get('data', result)
                self._activated = True
                self._license_key = license_key
                self._activation_badge.set('Bound', self._badge_bound)
                self._hw_bound_badge.set('Bound', self._badge_bound)
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
            self._activate_btn.set_loading(False)
