"""Custom Activation Dialog — auto-closes after successful activation.

Replaces SDK ActivationDialog which does not close on its own.
Uses the SDK client for all API calls so no backend logic is duplicated.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional


class ActivationDialog:
    """Simplified activation dialog — license key entry + validate + activate.

    Closes automatically 1.5 s after successful activation so the caller
    can proceed with post-activation (refresh, congrats, restart).
    """

    def __init__(self, client, product_name: str = '', cache=None):
        self._client = client
        self._product_name = product_name
        self._cache = cache

        self._root: Optional[tk.Toplevel] = None
        self._hardware_id: Optional[str] = None
        self._license_key: Optional[str] = None
        self._activated: bool = False
        self._cancelled: bool = False

        # colour palette
        self._primary = '#1e40af'
        self._bg = '#f5f7fb'
        self._card_bg = '#ffffff'
        self._text = '#111827'
        self._text_sec = '#6b7280'
        self._success = '#16a34a'
        self._error = '#dc2626'
        self._border = '#dbe3ef'

    def show(self) -> Dict[str, Any]:
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return {'activated': self._activated, 'cancelled': True}

        self._root = tk.Toplevel()
        self._root.title('Activate License')
        self._root.geometry('520x440')
        self._root.minsize(480, 400)
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_closing)
        self._root.bind('<Escape>', lambda e: self._on_closing())

        self._build_ui()
        self._center()
        self._detect_hardware()
        self._root.wait_window()

        return {
            'activated': self._activated,
            'cancelled': self._cancelled,
            'license_key': self._license_key,
        }

    def _center(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f'{w}x{h}+{x}+{y}')

    def _card(self, parent):
        f = tk.Frame(parent, bg=self._card_bg,
                     highlightbackground=self._border, highlightthickness=1, bd=0)
        return f

    def _build_ui(self):
        root = self._root

        hdr = tk.Frame(root, bg=self._bg)
        hdr.pack(fill='x', padx=24, pady=(24, 6))
        tk.Label(hdr, text='Activate License',
                 font=('Segoe UI', 18, 'bold'),
                 bg=self._bg, fg=self._text).pack(anchor='w')
        tk.Label(hdr, text='Enter your license key to activate this device',
                 font=('Segoe UI', 10),
                 bg=self._bg, fg=self._text_sec).pack(anchor='w', pady=(1, 0))

        body_frame = tk.Frame(root, bg=self._bg)
        body_frame.pack(fill='both', expand=True, padx=24, pady=(10, 10))

        # Hardware card
        hw_card = self._card(body_frame)
        hw_card.pack(fill='x', pady=(0, 14))
        hw_inner = tk.Frame(hw_card, bg=self._card_bg, padx=20, pady=12)
        hw_inner.pack(fill='both')
        tk.Label(hw_inner, text='Hardware',
                 font=('Segoe UI', 11, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor='w', pady=(0, 6))
        self._hw_id_label = tk.Label(hw_inner, text='Hardware ID: detecting...',
                                      font=('Segoe UI', 9),
                                      bg=self._card_bg, fg=self._text_sec)
        self._hw_id_label.pack(anchor='w')
        self._hw_status = tk.Label(hw_inner, text='',
                                    font=('Segoe UI', 9),
                                    bg=self._card_bg, fg=self._text_sec)
        self._hw_status.pack(anchor='w')

        # License card
        lic_card = self._card(body_frame)
        lic_card.pack(fill='x', pady=(0, 14))
        lic_inner = tk.Frame(lic_card, bg=self._card_bg, padx=20, pady=12)
        lic_inner.pack(fill='both')

        tk.Label(lic_inner, text='License Key',
                 font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor='w', pady=(0, 4))
        key_row = tk.Frame(lic_inner, bg=self._card_bg)
        key_row.pack(fill='x')
        self._key_entry = tk.Entry(key_row, font=('Consolas', 11),
                                    bg=self._card_bg, fg=self._text,
                                    insertbackground=self._primary,
                                    highlightbackground=self._border,
                                    highlightthickness=1, relief='flat', bd=2)
        self._key_entry.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 8))
        self._key_entry.bind('<Return>', lambda e: self._on_refresh())
        self._key_entry.bind('<KP_Enter>', lambda e: self._on_refresh())
        self._key_entry.focus()

        self._refresh_btn = tk.Button(key_row, text='Refresh', command=self._on_refresh,
                                       font=('Segoe UI', 10, 'bold'),
                                       fg='white', bg=self._primary,
                                       activebackground=self._primary,
                                       bd=0, padx=16, pady=6, cursor='hand2')
        self._refresh_btn.pack(side='right')
        self._refresh_btn.bind('<Return>', lambda e: self._on_refresh())
        self._refresh_btn.bind('<KP_Enter>', lambda e: self._on_refresh())

        # Status label
        self._status_label = tk.Label(body_frame, text='',
                                       font=('Segoe UI', 10),
                                       bg=self._bg, fg=self._text_sec)
        self._status_label.pack(anchor='w', pady=(0, 10))

        # Activate button
        self._activate_btn = tk.Button(body_frame, text='Activate License',
                                        command=self._on_activate,
                                        font=('Segoe UI', 12, 'bold'),
                                        fg='white', bg=self._primary,
                                        activebackground=self._primary,
                                        bd=0, padx=20, pady=10, cursor='hand2',
                                        state='disabled')
        self._activate_btn.pack(fill='x', ipady=4)
        self._activate_btn.bind('<Return>', lambda e: self._on_activate())
        self._activate_btn.bind('<KP_Enter>', lambda e: self._on_activate())

    def _detect_hardware(self):
        try:
            from WSD_SDKToolkit_ZEMMACOS.hardware import HardwareDetector as _HD
            hw = _HD()
            self._hardware_id = hw.get_fingerprint()
            if self._hardware_id:
                self._hw_id_label.config(text=f'Hardware ID: {self._hardware_id[:20]}...')
                self._hw_status.config(text='Hardware detected', fg=self._success)
            else:
                self._hw_status.config(text='Hardware detection failed', fg=self._error)
        except Exception as e:
            self._hw_status.config(text=f'Error: {e}', fg=self._error)

    def _set_loading(self, loading: bool, button=None):
        state = 'disabled' if loading else 'normal'
        if button:
            button.config(state=state, text='Loading...' if loading else None)
        else:
            self._refresh_btn.config(state=state)
            self._activate_btn.config(state=state)

    def _on_closing(self):
        if not self._activated:
            self._cancelled = True
        try:
            self._root.destroy()
        except Exception:
            pass

    def _on_refresh(self):
        key = self._key_entry.get().strip()
        if not key:
            self._status_label.config(text='Enter a license key first.', fg=self._error)
            return

        def _do():
            self._root.after(0, lambda: self._status_label.config(
                text='Validating license...', fg=self._text_sec))
            try:
                import requests as _req
                hw_id = self._hardware_id or ''
                result = self._client.validate_license(key, hw_id)
                data = result.get('data', result)
                if data.get('valid'):
                    self._license_key = key
                    self._root.after(0, lambda: self._on_validate_success(data))
                else:
                    err = data.get('message', data.get('error', 'License not valid'))
                    self._root.after(0, lambda: self._status_label.config(
                        text=f'Validation failed: {err}', fg=self._error))
            except Exception as e:
                self._root.after(0, lambda: self._status_label.config(
                    text=f'Validation error: {e}', fg=self._error))

        threading.Thread(target=_do, daemon=True).start()

    def _on_validate_success(self, data: Dict[str, Any]):
        self._status_label.config(text='License validated successfully. You may now activate.',
                                   fg=self._success)
        self._activate_btn.config(state='normal')
        self._refresh_btn.config(state='normal')

    def _on_activate(self):
        key = self._key_entry.get().strip()
        if not key:
            self._status_label.config(text='Enter a license key.', fg=self._error)
            return
        if not self._hardware_id:
            self._status_label.config(text='Hardware not detected.', fg=self._error)
            return

        self._activate_btn.config(state='disabled', text='Activating...')
        self._refresh_btn.config(state='disabled')

        def _do():
            try:
                result = self._client.activate_license(key, self._hardware_id)
                data = result.get('data', result)
                if result.get('success') or data.get('success') or data.get('already_activated'):
                    self._activated = True
                    self._license_key = key
                    if self._cache:
                        try:
                            self._cache.invalidate_license_status()
                        except Exception:
                            pass
                    self._root.after(0, self._on_activate_success)
                else:
                    err = result.get('message', result.get('error', 'Activation failed'))
                    self._root.after(0, lambda: self._on_activate_error(err))
            except Exception as e:
                self._root.after(0, lambda: self._on_activate_error(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _on_activate_success(self):
        self._status_label.config(text='License activated successfully!', fg=self._success)
        self._activate_btn.config(text='Activated', state='disabled',
                                   bg=self._success, activebackground=self._success)
        self._root.after(1500, self._close_and_return)

    def _on_activate_error(self, err: str):
        self._status_label.config(text=f'Activation failed: {err}', fg=self._error)
        self._activate_btn.config(state='normal', text='Activate License',
                                   bg=self._primary, activebackground=self._primary)
        self._refresh_btn.config(state='normal')

    def _close_and_return(self):
        try:
            self._root.destroy()
        except Exception:
            pass
