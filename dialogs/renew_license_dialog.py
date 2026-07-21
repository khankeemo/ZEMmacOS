"""Renew License Dialog — V2 Clean Architecture

Window 900×700, resizable, uses application theme.
License verification → customer info → license info → renewal request → send.
All DB/email logic lives in Websmith API; ZEMmacOS is UI-only via SDK bridge.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional


class RenewLicenseDialog:
    """Premium renewal dialog — 900×700, scrollable, card-based layout."""

    def __init__(self, parent, engine, *, license_key: str = '',
                 customer_name: str = '', email: str = '', mobile: str = ''):
        self._parent = parent
        self._engine = engine
        self._client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self.branding = self.config.get('branding', {})
        self.colors = self.branding.get('colors', {})
        self.labels = self.branding.get('labels', {})

        self._license_key = license_key
        self._customer_name = customer_name
        self._email = email
        self._mobile = mobile

        self._root: Optional[tk.Toplevel] = None
        self._verified = False
        self._license_data: Dict[str, Any] = {}
        self._product_id = ''
        self._plans_list: list[str] = []

        # Theme colours
        self._primary = self.colors.get('primary', '#1e40af')
        self._bg = self.colors.get('bg_page', '#f8f9fa')
        self._card_bg = self.colors.get('bg_card', '#ffffff')
        self._text = self.colors.get('text_primary', '#333333')
        self._text_sec = self.colors.get('text_secondary', '#555555')
        self._muted = self.colors.get('text_muted', '#888888')
        self._border = self.colors.get('border', '#dbe3ef')
        self._success = self.colors.get('success', '#16a34a')
        self._error = self.colors.get('error', '#dc2626')
        self._warning = self.colors.get('warning', '#ea580c')

        self._support_email = self.branding.get('support_email',
                                                 'support@websmithdigital.com')

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def show(self):
        self._build()
        self._center()
        self._root.wait_window()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build(self):
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._root = tk.Toplevel(self._parent)
        self._root.title(self.labels.get('renew_title', 'Renew License'))
        self._root.geometry('900x700')
        self._root.minsize(760, 600)
        self._root.resizable(True, True)
        self._root.configure(bg=self._bg)
        self._root.transient(self._parent)
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_close)
        self._root.bind('<Escape>', lambda e: self._on_close())

        # ── Scrollable canvas ──
        canvas = tk.Canvas(self._root, bg=self._bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._root, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self._bg)
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self._canvas_win = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_canvas_cfg(event):
            canvas.itemconfig(self._canvas_win, width=event.width - 4)
        canvas.bind('<Configure>', _on_canvas_cfg)

        content = tk.Frame(scroll_frame, bg=self._bg, padx=28, pady=24)
        content.pack(fill=tk.BOTH, expand=True)

        self._build_header(content)
        self._build_verification(content)
        self._build_customer_info(content)
        self._build_license_info(content)
        self._build_renewal_request(content)
        self._build_footer(content)

        # Pre-fill if known
        if self._license_key:
            self._var_license_key.set(self._license_key)
        if self._customer_name:
            self._var_cust_name.set(self._customer_name)
        if self._email:
            self._var_email.set(self._email)
        if self._mobile:
            self._var_mobile.set(self._mobile)

        self._set_fields_disabled(True)

    # ── Header Card ──
    def _build_header(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=18)
        inner.pack(fill=tk.BOTH)
        tk.Label(inner, text='Renew License',
                 font=('Segoe UI', 18, 'bold'),
                 bg=self._card_bg, fg=self._primary).pack(anchor=tk.W)
        tk.Label(inner,
                 text='Renew your subscription or request a new license from Websmith Digital.',
                 font=('Segoe UI', 10),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(4, 0))

    # ── License Verification ──
    def _build_verification(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='License Verification',
                 font=('Segoe UI', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 8))

        # License key row
        key_row = tk.Frame(inner, bg=self._card_bg)
        key_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(key_row, text='License Number',
                 font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(0, 4))

        input_row = tk.Frame(key_row, bg=self._card_bg)
        input_row.pack(fill=tk.X)
        self._var_license_key = tk.StringVar()
        self._entry_key = tk.Entry(
            input_row, textvariable=self._var_license_key,
            font=('Consolas', 11),
            bg=self._card_bg, fg=self._text,
            insertbackground=self._primary,
            highlightbackground=self._border, highlightthickness=1,
            relief=tk.FLAT, bd=2)
        self._entry_key.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        self._btn_verify = tk.Button(
            input_row, text='Verify', command=self._on_verify,
            font=('Segoe UI', 10, 'bold'),
            fg='white', bg=self._primary,
            activebackground=self._primary, activeforeground='white',
            bd=0, padx=20, pady=6, cursor='hand2')
        self._btn_verify.pack(side=tk.RIGHT)
        self._entry_key.bind('<Return>', lambda e: self._on_verify())
        self._entry_key.bind('<KP_Enter>', lambda e: self._on_verify())
        self._btn_verify.bind('<Return>', lambda e: self._on_verify())
        self._btn_verify.bind('<KP_Enter>', lambda e: self._on_verify())

        # Status row
        self._var_status = tk.StringVar(value='Not Verified')
        self._status_label = tk.Label(
            inner, textvariable=self._var_status,
            font=('Segoe UI', 10),
            bg=self._card_bg, fg=self._muted)
        self._status_label.pack(anchor=tk.W, pady=(4, 0))

    # ── Customer Information ──
    def _build_customer_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='Customer Information',
                 font=('Segoe UI', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_cust_name = tk.StringVar()
        self._var_email = tk.StringVar()
        self._var_mobile = tk.StringVar()

        self._entry_cust_name = None
        self._entry_email = None
        self._entry_mobile = None
        for lbl, var, entry_attr in [('Customer Name', self._var_cust_name, '_entry_cust_name'),
                         ('Email Address', self._var_email, '_entry_email'),
                         ('Mobile Number', self._var_mobile, '_entry_mobile')]:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 8))
            tk.Label(row, text=lbl, font=('Segoe UI', 10, 'bold'),
                     bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(0, 3))
            entry = tk.Entry(row, textvariable=var, font=('Segoe UI', 11),
                             bg=self._card_bg, fg=self._text,
                             insertbackground=self._primary,
                             highlightbackground=self._border, highlightthickness=1,
                             relief=tk.FLAT, bd=2)
            entry.pack(fill=tk.X, ipady=6)
            entry.bind('<Return>', lambda e: None)
            entry.bind('<KP_Enter>', lambda e: None)
            setattr(self, entry_attr, entry)

    # ── License Information ──
    def _build_license_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='License Information',
                 font=('Segoe UI', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_plan = tk.StringVar(value='--')
        self._var_lic_status = tk.StringVar(value='--')
        self._var_expiry = tk.StringVar(value='--')
        self._var_requested_plan = tk.StringVar(value='')

        for lbl, var in [('Current Plan', self._var_plan),
                         ('Status', self._var_lic_status),
                         ('Expiry Date', self._var_expiry)]:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 6))
            tk.Label(row, text=lbl + ':', font=('Segoe UI', 10, 'bold'),
                     bg=self._card_bg, fg=self._text_sec,
                     width=18, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, textvariable=var, font=('Segoe UI', 11, 'bold'),
                     bg=self._card_bg, fg=self._text).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Requested Plan dropdown
        plan_row = tk.Frame(inner, bg=self._card_bg)
        plan_row.pack(fill=tk.X, pady=(6, 4))
        tk.Label(plan_row, text='Requested Plan:', font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec,
                 width=18, anchor=tk.W).pack(side=tk.LEFT)
        self._plan_dropdown = ttk.Combobox(
            plan_row, textvariable=self._var_requested_plan,
            font=('Segoe UI', 11),
            state='readonly', width=30)
        self._plan_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ── Renewal Request ──
    def _build_renewal_request(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='Renewal Request',
                 font=('Segoe UI', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        # To
        row = tk.Frame(inner, bg=self._card_bg)
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text='To:', font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec, width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(row, text=self._support_email,
                 font=('Segoe UI', 11, 'bold'),
                 bg=self._card_bg, fg=self._primary).pack(side=tk.LEFT)

        # Subject
        row = tk.Frame(inner, bg=self._card_bg)
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text='Subject:', font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec, width=14, anchor=tk.W).pack(side=tk.LEFT)
        self._var_subject = tk.StringVar(value='License Renewal Request')
        tk.Label(row, textvariable=self._var_subject,
                 font=('Segoe UI', 11),
                 bg=self._card_bg, fg=self._text).pack(side=tk.LEFT)

        # Request Type (radio)
        tk.Label(inner, text='Request Type',
                 font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(6, 4))
        self._var_req_type = tk.StringVar(value='renew')
        radio_frame = tk.Frame(inner, bg=self._card_bg)
        radio_frame.pack(fill=tk.X, pady=(0, 6))
        for val, txt in [('renew', 'Renew Existing License'),
                         ('new', 'Request New License')]:
            tk.Radiobutton(radio_frame, text=txt, variable=self._var_req_type, value=val,
                           font=('Segoe UI', 10),
                           bg=self._card_bg, fg=self._text,
                           selectcolor=self._card_bg,
                           activebackground=self._card_bg,
                           indicatoron=True).pack(side=tk.LEFT, padx=(0, 20))

        # Message
        tk.Label(inner, text='Message',
                 font=('Segoe UI', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(6, 4))
        self._msg_text = tk.Text(inner, font=('Segoe UI', 10),
                                 bg=self._card_bg, fg=self._text,
                                 insertbackground=self._primary,
                                 highlightbackground=self._border,
                                 highlightthickness=1,
                                 relief=tk.FLAT, bd=2,
                                 height=5, wrap=tk.WORD)
        self._msg_text.pack(fill=tk.X)
        self._msg_text.insert(tk.END, 'Additional details...')
        self._msg_text.bind('<Control-Return>', lambda e: self._on_send())
        self._msg_text.bind('<Control-KP_Enter>', lambda e: self._on_send())

    # ── Footer Buttons ──
    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=self._bg)
        footer.pack(fill=tk.X, pady=(8, 0))

        sep = tk.Frame(footer, bg=self._border, height=1)
        sep.pack(fill=tk.X, pady=(0, 10))

        btn_frame = tk.Frame(footer, bg=self._bg)
        btn_frame.pack(fill=tk.X)

        self._btn_cancel = tk.Button(
            btn_frame, text='Cancel', command=self._on_close,
            font=('Segoe UI', 10),
            fg=self._text, bg=self.colors.get('bg_button', '#e5e7eb'),
            activebackground=self.colors.get('bg_button', '#e5e7eb'),
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_cancel.pack(side=tk.LEFT, padx=(0, 8))
        self._btn_cancel.bind('<Return>', lambda e: self._on_close())
        self._btn_cancel.bind('<KP_Enter>', lambda e: self._on_close())

        self._btn_reset = tk.Button(
            btn_frame, text='Reset', command=self._on_reset,
            font=('Segoe UI', 10),
            fg=self._text, bg=self.colors.get('bg_button', '#e5e7eb'),
            activebackground=self.colors.get('bg_button', '#e5e7eb'),
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_reset.pack(side=tk.LEFT, padx=(0, 8))
        self._btn_reset.bind('<Return>', lambda e: self._on_reset())
        self._btn_reset.bind('<KP_Enter>', lambda e: self._on_reset())

        self._btn_send = tk.Button(
            btn_frame, text='Send Request', command=self._on_send,
            font=('Segoe UI', 10, 'bold'),
            fg='white', bg=self._primary,
            activebackground=self._primary, activeforeground='white',
            bd=0, padx=20, pady=6, cursor='hand2')
        self._btn_send.pack(side=tk.RIGHT)
        self._btn_send.bind('<Return>', lambda e: self._on_send())
        self._btn_send.bind('<KP_Enter>', lambda e: self._on_send())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _card(self, parent) -> tk.Frame:
        return tk.Frame(parent, bg=self._card_bg,
                        highlightbackground=self._border,
                        highlightthickness=1, bd=0)

    def _center(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f'{w}x{h}+{x}+{y}')

    def _set_fields_disabled(self, disabled: bool):
        state = tk.DISABLED if disabled else tk.NORMAL
        for w in (self._entry_key,):
            w.config(state=state)
        for entry_attr in ('_entry_cust_name', '_entry_email', '_entry_mobile'):
            entry = getattr(self, entry_attr, None)
            if entry:
                entry.config(state=state)
        self._btn_verify.config(state=tk.DISABLED if disabled and not self._verified else tk.NORMAL)
        self._msg_text.config(state=state)

    def _fetch_plans(self, product_id: str):
        try:
            import requests as _requests
            base = self._client.base_url if self._client else ''
            api_ver = self._client.api_version if self._client else 'v1'
            url = f"{base}/api/{api_ver}/store/products?id={product_id}"
            resp = _requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get('products', []) if data.get('success') else data.get('products', [])
                if products:
                    plans = products[0].get('plans', [])
                    self._plans_list = [p.get('name', '') for p in plans if p.get('name')]
                    self._root.after(0, self._populate_plan_dropdown)
                    return
            self._root.after(0, lambda: self._populate_plan_dropdown(fallback=True))
        except Exception:
            self._root.after(0, lambda: self._populate_plan_dropdown(fallback=True))

    def _populate_plan_dropdown(self, fallback: bool = False):
        plan_names = self._plans_list if self._plans_list else []
        if fallback or not plan_names:
            current = self._var_plan.get()
            if current and current != '--':
                plan_names = [current]
            else:
                plan_names = []
        self._plan_dropdown['values'] = plan_names
        current = self._var_plan.get()
        if current in plan_names:
            self._var_requested_plan.set(current)
        elif plan_names:
            self._var_requested_plan.set(plan_names[0])
        else:
            self._var_requested_plan.set('')

    def _on_close(self):
        if self._root:
            self._root.destroy()
            self._root = None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_verify(self):
        key = self._var_license_key.get().strip()
        if not key:
            messagebox.showwarning('Input Required', 'Enter a license key.',
                                   parent=self._root)
            return

        self._btn_verify.config(state=tk.DISABLED, text='Verifying...')
        self._var_status.set('Verifying...')
        self._status_label.config(fg=self._muted)
        self._root.update_idletasks()

        def _do_verify():
            try:
                sdk = self._client
                if sdk is None:
                    raise RuntimeError('SDK client not available')

                # 1) Verify license for renewal
                verify_resp = sdk.verify_license_for_renewal(key)
                if not verify_resp.get('valid'):
                    msg = verify_resp.get('message', 'Invalid license')
                    self._root.after(0, lambda: self._verify_failed(msg))
                    return

                # 2) Get detailed license info
                details_resp = sdk.get_license_details(key)

                data = {**verify_resp, **details_resp}
                self._root.after(0, lambda: self._verify_success(data))

            except Exception as exc:
                self._root.after(0, lambda e=exc: self._verify_failed(str(e)))

        import threading
        threading.Thread(target=_do_verify, daemon=True).start()

    def _verify_success(self, data: Dict[str, Any]):
        self._verified = True
        self._license_data = data

        self._var_status.set('\u2713 Verified')
        self._status_label.config(fg=self._success)
        self._btn_verify.config(state=tk.NORMAL, text='Verify')

        # Fill customer info (user may edit — changes never overwrite DB)
        self._var_cust_name.set(data.get('customer_name', ''))
        self._var_email.set(data.get('email', data.get('customer_email', '')))
        self._var_mobile.set(data.get('mobile', data.get('customer_mobile', '')))

        # Fill license info
        self._var_plan.set(data.get('plan', '--'))
        status_text = data.get('status', '--')
        if isinstance(status_text, str):
            status_text = status_text.upper()
        self._var_lic_status.set(status_text)
        expiry = data.get('expiry_date', '--')
        if expiry and expiry != '--':
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                expiry = dt.strftime('%d %b %Y')
            except Exception:
                pass
        self._var_expiry.set(expiry)

        # Store product_id and fetch available plans
        self._product_id = data.get('product_id', '')
        if self._product_id:
            import threading
            threading.Thread(target=self._fetch_plans, args=(self._product_id,), daemon=True).start()

        # Enable fields
        self._set_fields_disabled(False)

        # Focus first editable field
        if hasattr(self, '_entry_cust_name') and self._entry_cust_name:
            self._entry_cust_name.focus_set()

    def _verify_failed(self, msg: str):
        self._verified = False
        self._license_data = {}
        self._var_status.set(f'\u2717 {msg}')
        self._status_label.config(fg=self._error)
        self._btn_verify.config(state=tk.NORMAL, text='Verify')
        self._set_fields_disabled(True)

    def _on_reset(self):
        self._var_license_key.set('')
        self._var_cust_name.set('')
        self._var_email.set('')
        self._var_mobile.set('')
        self._var_plan.set('--')
        self._var_lic_status.set('--')
        self._var_expiry.set('--')
        self._var_requested_plan.set('')
        self._plan_dropdown['values'] = []
        self._plans_list = []
        self._product_id = ''
        self._var_subject.set('License Renewal Request')
        self._var_req_type.set('renew')
        self._msg_text.delete('1.0', tk.END)
        self._msg_text.insert(tk.END, 'Additional details...')
        self._verified = False
        self._license_data = {}
        self._var_status.set('Not Verified')
        self._status_label.config(fg=self._muted)
        self._set_fields_disabled(True)

    def _on_send(self):
        if not self._verified:
            messagebox.showwarning('Not Verified',
                                    'Verify your license first.',
                                    parent=self._root)
            return

        key = self._var_license_key.get().strip()
        cust_name = self._var_cust_name.get().strip()
        email = self._var_email.get().strip()
        mobile = self._var_mobile.get().strip()
        subject = self._var_subject.get().strip()
        msg = self._msg_text.get('1.0', tk.END).strip()
        req_type = self._var_req_type.get()
        current_plan = self._var_plan.get()
        selected_plan = self._var_requested_plan.get()
        product_id = self._product_id

        if not msg or msg == 'Additional details...':
            msg = ''

        if not key:
            messagebox.showwarning('Input Required', 'License key is missing.',
                                    parent=self._root)
            return

        self._btn_send.config(state=tk.DISABLED, text='Sending...')
        self._root.update_idletasks()

        def _do_send():
            try:
                sdk = self._client
                if sdk is None:
                    raise RuntimeError('SDK client not available')

                cplan = current_plan if current_plan and current_plan != '--' else selected_plan
                payload = {
                    'license_key': key,
                    'customer_name': cust_name,
                    'email': email,
                    'mobile': mobile,
                    'subject': subject,
                    'message': msg,
                    'request_type': req_type,
                    'current_plan': cplan,
                    'selected_plan': selected_plan,
                    'product_id': product_id,
                }
                resp = sdk._request('license/send-renewal-request', payload)
                self._root.after(0, lambda: self._send_done(resp))

            except Exception as exc:
                self._root.after(0, lambda e=exc: self._send_error(str(e)))

        import threading
        threading.Thread(target=_do_send, daemon=True).start()

    def _send_done(self, resp: Dict[str, Any]):
        self._btn_send.config(state=tk.NORMAL, text='Send Request')
        if resp.get('success'):
            messagebox.showinfo('Sent',
                                'Your renewal request has been sent to Websmith Digital.\n'
                                'You will receive a response shortly.',
                                parent=self._root)
            self._on_close()
        else:
            msg = resp.get('message', resp.get('error', 'Failed to send request.'))
            messagebox.showerror('Error', msg, parent=self._root)

    def _send_error(self, msg: str):
        self._btn_send.config(state=tk.NORMAL, text='Send Request')
        messagebox.showerror('Error', f'Failed to send request:\n{msg}',
                             parent=self._root)
