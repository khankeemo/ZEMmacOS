"""Renew License Dialog — premium renewal window with email compose"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List
import webbrowser
import urllib.parse


class RenewLicenseDialog:
    def __init__(self, engine, license_key: str = '', parent=None):
        self.engine = engine
        self.client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self._parent = parent
        self.license_key = license_key
        if license_key:
            self.engine._license_key = license_key
        self.result = None
        self.root = None
        self._verified = False
        self._license_data: Dict[str, Any] = {}
        self._plans: list = []
        self._selected_plan: Optional[Dict[str, Any]] = None
        self._current_plan: Optional[Dict[str, Any]] = None

        branding = self.config.get('branding', {})
        self._colors = branding.get('colors', {})
        self._labels = branding.get('labels', {})
        self._primary = self._colors.get('primary', '#1e40af')
        self._bg = self._colors.get('bg_page', '#f5f7fb')
        self._card_bg = self._colors.get('bg_card', '#ffffff')
        self._text = self._colors.get('text_primary', '#111827')
        self._text_sec = self._colors.get('text_secondary', '#6b7280')
        self._muted = self._colors.get('text_muted', '#9ca3af')
        self._border = self._colors.get('border', '#dbe3ef')
        self._success = self._colors.get('success', '#16a34a')
        self._error = self._colors.get('error', '#dc2626')
        self._support_email = 'support@websmithdigital.com'

        self._product_name = ''
        self._license_key_val = ''

    def show(self) -> Optional[Dict[str, Any]]:
        if not self._parent:
            raise RuntimeError("SDK dialogs require the application root window as parent")
        self._build_ui()
        self._center()
        self.root.wait_window()
        return self.result

    def _build_ui(self):
        self.root = tk.Toplevel(self._parent)
        self.root.title(self._labels.get('renew_title', 'Renew License'))
        self.root.geometry('900x700')
        self.root.minsize(760, 600)
        self.root.resizable(True, True)
        self.root.configure(bg=self._bg)
        self.root.transient(self._parent)
        self.root.grab_set()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

        canvas = tk.Canvas(self.root, bg=self._bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=canvas.yview)
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
        self._build_plan_selector(content)
        self._build_message(content)
        self._build_footer(content)

        if self.license_key:
            self._var_license_key.set(self.license_key)

    def _card(self, parent) -> tk.Frame:
        frame = tk.Frame(parent, bg=self._card_bg,
                         highlightbackground=self._border,
                         highlightthickness=1, bd=0)
        return frame

    def _make_label(self, parent, text, size=11, bold=False, color=None, **kw):
        font = ('Segoe UI', size, 'bold' if bold else 'normal')
        return tk.Label(parent, text=text, font=font,
                        bg=self._card_bg, fg=color or self._text, **kw)

    def _make_entry(self, parent, textvariable=None, readonly=False, **kw):
        state = 'readonly' if readonly else 'normal'
        entry = tk.Entry(parent, textvariable=textvariable,
                         font=('Segoe UI', 11),
                         bg=self._card_bg, fg=self._text,
                         insertbackground=self._primary,
                         highlightbackground=self._border,
                         highlightthickness=1,
                         relief=tk.FLAT, bd=2,
                         state=state, **kw)
        return entry

    def _build_header(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=18)
        inner.pack(fill=tk.BOTH)
        self._make_label(inner, 'Renew License', size=20, bold=True,
                         color=self._primary).pack(anchor=tk.W)
        self._make_label(inner,
                         'Select a new plan and send your renewal request to Websmith Digital support.',
                         size=10, color=self._text_sec).pack(anchor=tk.W, pady=(4, 0))

    def _build_verification(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        self._make_label(inner, 'License Verification', size=13, bold=True,
                         color=self._text).pack(anchor=tk.W, pady=(0, 10))

        key_row = tk.Frame(inner, bg=self._card_bg)
        key_row.pack(fill=tk.X, pady=(0, 6))
        self._make_label(key_row, 'License Key', size=10, bold=True,
                         color=self._text_sec).pack(anchor=tk.W, pady=(0, 4))

        input_row = tk.Frame(key_row, bg=self._card_bg)
        input_row.pack(fill=tk.X)
        self._var_license_key = tk.StringVar()
        self._entry_key = tk.Entry(
            input_row, textvariable=self._var_license_key,
            font=('Courier', 11),
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

        self._var_status = tk.StringVar(value='Not Verified')
        self._status_label = tk.Label(
            inner, textvariable=self._var_status,
            font=('Segoe UI', 10),
            bg=self._card_bg, fg=self._muted)
        self._status_label.pack(anchor=tk.W, pady=(4, 0))

    def _build_customer_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        self._make_label(inner, 'Customer Information', size=13, bold=True,
                         color=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_cust_name = tk.StringVar()
        self._var_email = tk.StringVar()
        self._var_mobile = tk.StringVar()

        for lbl, var in [('Customer Name', self._var_cust_name),
                         ('Email', self._var_email),
                         ('Mobile Number', self._var_mobile)]:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 8))
            self._make_label(row, lbl, size=10, bold=True,
                             color=self._text_sec).pack(anchor=tk.W, pady=(0, 3))
            entry = self._make_entry(row, textvariable=var)
            entry.pack(fill=tk.X, ipady=6)

    def _build_license_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        self._make_label(inner, 'License Information', size=13, bold=True,
                         color=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_plan = tk.StringVar(value='--')
        self._var_lic_status = tk.StringVar(value='--')
        self._var_expiry = tk.StringVar(value='--')
        self._var_product = tk.StringVar(value='--')

        labels = [('Product', self._var_product),
                  ('Current Plan', self._var_plan),
                  ('Status', self._var_lic_status),
                  ('Expiry Date', self._var_expiry)]
        for lbl, var in labels:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 4))
            self._make_label(row, lbl + ':', size=10, bold=True,
                             color=self._text_sec,
                             width=16, anchor=tk.W).pack(side=tk.LEFT)
            self._make_label(row, '', size=11, bold=True,
                             color=self._text).pack(side=tk.LEFT, fill=tk.X, expand=True)
            var_label = self._make_label(row, '', size=11, bold=False,
                                         color=self._text)
            var_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            config_label_text = lambda v=var, lb=var_label: lb.config(textvariable=v)
            config_label_text()

    def _build_plan_selector(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        self._make_label(inner, 'Select Plan', size=13, bold=True,
                         color=self._text).pack(anchor=tk.W, pady=(0, 4))
        self._make_label(inner,
                         'Choose a plan to upgrade or renew your subscription.',
                         size=10, color=self._text_sec).pack(anchor=tk.W, pady=(0, 10))

        self._plans_container = tk.Frame(inner, bg=self._card_bg)
        self._plans_container.pack(fill=tk.X)

        self._no_plans_label = self._make_label(
            self._plans_container, 'Verify your license to see available plans.',
            size=10, color=self._muted)
        self._no_plans_label.pack(pady=6)

        self._plan_buttons: List[tk.Frame] = []
        self._selected_plan_idx = -1

    def _render_plan_cards(self):
        for child in self._plans_container.winfo_children():
            child.destroy()
        self._plan_buttons.clear()

        self._no_plans_label = None

        if not self._plans:
            self._no_plans_label = self._make_label(
                self._plans_container,
                'No alternative plans available for this license.',
                size=10, color=self._muted)
            self._no_plans_label.pack(pady=6)
            return

        for i, plan in enumerate(self._plans):
            plan_frame = tk.Frame(
                self._plans_container, bg=self._card_bg,
                highlightbackground=self._border,
                highlightthickness=1, bd=0, cursor='hand2')
            plan_frame.pack(fill=tk.X, pady=(0, 8))

            is_current = False
            if self._current_plan and isinstance(self._current_plan, dict):
                cid = self._current_plan.get('id')
                pid = plan.get('id')
                if cid is not None and pid is not None and str(cid) == str(pid):
                    is_current = True

            inner = tk.Frame(plan_frame, bg=self._card_bg, padx=16, pady=12)
            inner.pack(fill=tk.X)

            name = plan.get('name', f'Plan {i+1}')
            dur = plan.get('duration_days', plan.get('default_expiry_days', 365))
            devices = plan.get('max_devices', 1)
            price = plan.get('price', '')

            row1 = tk.Frame(inner, bg=self._card_bg)
            row1.pack(fill=tk.X)
            name_label = self._make_label(row1, name, size=12, bold=True,
                                          color=self._text)
            name_label.pack(side=tk.LEFT)

            if is_current:
                current_badge = tk.Label(row1, text='Current',
                                         font=('Segoe UI', 8, 'bold'),
                                         fg='white', bg=self._success,
                                         padx=8, pady=2)
                current_badge.pack(side=tk.LEFT, padx=(8, 0))

            price_label = self._make_label(row1, f'{price}' if price else '',
                                           size=11, bold=True,
                                           color=self._primary)
            price_label.pack(side=tk.RIGHT)

            row2 = tk.Frame(inner, bg=self._card_bg)
            row2.pack(fill=tk.X, pady=(4, 0))
            detail_text = f'{dur} days \u00b7 {devices} device(s)'
            self._make_label(row2, detail_text, size=9,
                             color=self._text_sec).pack(side=tk.LEFT)

            plan_frame.bind('<Button-1>', lambda e, idx=i: self._on_plan_click(idx))
            for child in inner.winfo_children():
                child.bind('<Button-1>', lambda e, idx=i: self._on_plan_click(idx))
            for child2 in row2.winfo_children():
                child2.bind('<Button-1>', lambda e, idx=i: self._on_plan_click(idx))

            self._plan_buttons.append(plan_frame)

        if self._selected_plan_idx >= 0 and self._selected_plan_idx < len(self._plan_buttons):
            self._highlight_plan(self._selected_plan_idx)

    def _on_plan_click(self, idx):
        self._selected_plan_idx = idx
        self._selected_plan = self._plans[idx]
        self._highlight_plan(idx)

    def _highlight_plan(self, idx):
        for i, frame in enumerate(self._plan_buttons):
            if i == idx:
                frame.config(highlightbackground=self._primary, highlightthickness=2)
            else:
                frame.config(highlightbackground=self._border, highlightthickness=1)

    def _build_message(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        self._make_label(inner, 'Message', size=13, bold=True,
                         color=self._text).pack(anchor=tk.W, pady=(0, 4))
        self._make_label(inner,
                         'Add any additional details for your renewal request.',
                         size=10, color=self._text_sec).pack(anchor=tk.W, pady=(0, 8))

        self._msg_text = tk.Text(inner, font=('Segoe UI', 10),
                                 bg=self._card_bg, fg=self._text,
                                 insertbackground=self._primary,
                                 highlightbackground=self._border,
                                 highlightthickness=1,
                                 relief=tk.FLAT, bd=2,
                                 height=4, wrap=tk.WORD)
        self._msg_text.pack(fill=tk.X)

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
            fg=self._text, bg='#e5e7eb',
            activebackground='#d1d5db',
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_cancel.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_reset = tk.Button(
            btn_frame, text='Reset', command=self._on_reset,
            font=('Segoe UI', 10),
            fg=self._text, bg='#e5e7eb',
            activebackground='#d1d5db',
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_reset.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_send = tk.Button(
            btn_frame, text='Send Request', command=self._on_send,
            font=('Segoe UI', 10, 'bold'),
            fg='white', bg=self._primary,
            activebackground=self._primary, activeforeground='white',
            bd=0, padx=20, pady=6, cursor='hand2')
        self._btn_send.pack(side=tk.RIGHT)

    def _center(self):
        if not self.root:
            return
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _on_close(self):
        if self.root:
            self.root.destroy()
            self.root = None

    def _on_verify(self):
        key = self._var_license_key.get().strip()
        if not key:
            messagebox.showwarning('Input Required', 'Enter a license key.',
                                   parent=self.root)
            return

        self._btn_verify.config(state=tk.DISABLED, text='Verifying...')
        self._var_status.set('Verifying...')
        self._status_label.config(fg=self._muted)
        self.root.update_idletasks()

        import threading

        def _do_verify():
            try:
                client = self.client
                if client is None:
                    raise RuntimeError('SDK client not available')

                verify_resp = client.verify_license_for_renewal(key)
                if not verify_resp.get('valid'):
                    msg = verify_resp.get('message', 'Invalid license')
                    self.root.after(0, lambda: self._verify_failed(msg))
                    return

                plans_resp = client.get_available_plans(key)
                data = {**verify_resp, 'plans_data': plans_resp}
                self.root.after(0, lambda: self._verify_success(data))

            except Exception as exc:
                self.root.after(0, lambda e=exc: self._verify_failed(str(e)))

        threading.Thread(target=_do_verify, daemon=True).start()

    def _load_plans(self):
        plans_data = self._license_data.get('plans_data', {})
        plans = plans_data.get('plans', [])
        curr_plan = plans_data.get('current_plan', {})
        curr_plan_id = curr_plan.get('id') if isinstance(curr_plan, dict) else None
        curr_plan_name = curr_plan.get('name') if isinstance(curr_plan, dict) else ''
        if isinstance(curr_plan_id, str) and curr_plan_id and curr_plan_id.isdigit():
            curr_plan_id = int(curr_plan_id)
        self._current_plan = curr_plan
        if plans:
            self._plans = plans
            auto_idx = -1
            for i, p in enumerate(plans):
                pid = p.get('id')
                if isinstance(pid, str) and pid.isdigit():
                    pid = int(pid)
                if pid is not None and curr_plan_id is not None and pid == curr_plan_id:
                    auto_idx = i
                    break
                if str(p.get('name', '')).lower() == str(curr_plan_name).lower():
                    auto_idx = i
            self._selected_plan_idx = auto_idx
            if auto_idx >= 0:
                self._selected_plan = plans[auto_idx]
            else:
                self._selected_plan_idx = 0
                self._selected_plan = plans[0] if plans else None
        else:
            self._plans = []
            self._selected_plan = None
            self._selected_plan_idx = -1
        self._render_plan_cards()

    def _on_plan_selected(self, event=None):
        sel = self._var_plan_name.get()
        for p in self._plans:
            dur = p.get('duration_days', p.get('default_expiry_days', 365))
            devices = p.get('max_devices', 1)
            label = f"{p.get('name', '')} ({dur} days, {devices} devices)"
            if label == sel:
                self._selected_plan = p
                return
        self._selected_plan = None

    def _verify_success(self, data: Dict[str, Any]):
        self._verified = True
        self._license_data = data

        self._var_status.set('\u2713 Verified')
        self._status_label.config(fg=self._success)
        self._btn_verify.config(state=tk.NORMAL, text='Verify')

        plans_data = data.get('plans_data', {})
        self._var_cust_name.set(data.get('customer_name', ''))
        self._var_email.set(data.get('email', data.get('customer_email', '')))
        self._var_mobile.set(data.get('mobile', data.get('customer_mobile', '')))

        self._var_product.set(data.get('product_name', ''))
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
        self._product_name = data.get('product_name', '')
        self._license_key_val = self._var_license_key.get().strip()

        self._load_plans()

    def _verify_failed(self, msg: str):
        self._verified = False
        self._license_data = {}
        self._plans = []
        self._selected_plan = None
        self._current_plan = None
        self._render_plan_cards()
        self._var_status.set(f'\u2717 {msg}')
        self._status_label.config(fg=self._error)
        self._btn_verify.config(state=tk.NORMAL, text='Verify')

    def _on_reset(self):
        self._var_license_key.set('')
        self._var_cust_name.set('')
        self._var_email.set('')
        self._var_mobile.set('')
        self._var_plan.set('--')
        self._var_lic_status.set('--')
        self._var_expiry.set('--')
        self._var_product.set('--')
        self._msg_text.delete('1.0', tk.END)
        self._verified = False
        self._license_data = {}
        self._plans = []
        self._selected_plan = None
        self._current_plan = None
        self._selected_plan_idx = -1
        self._render_plan_cards()
        self._var_status.set('Not Verified')
        self._status_label.config(fg=self._muted)

    def _on_send(self):
        if not self._verified:
            messagebox.showwarning('Not Verified',
                                   'Verify your license first.',
                                   parent=self.root)
            return

        cust_name = self._var_cust_name.get().strip()
        email = self._var_email.get().strip()
        mobile = self._var_mobile.get().strip()
        license_key = self._var_license_key.get().strip()
        product = self._var_product.get().strip()
        current_plan = self._var_plan.get().strip()
        msg = self._msg_text.get('1.0', tk.END).strip()

        requested_plan_name = ''
        if self._selected_plan:
            requested_plan_name = self._selected_plan.get('name', '')

        if not license_key:
            messagebox.showwarning('Input Required', 'License key is missing.',
                                   parent=self.root)
            return

        subject = f'License Renewal Request - {product} - {cust_name}'

        body_lines = [
            'License Renewal Request',
            '=' * 40,
            '',
            f'Customer Name: {cust_name}',
            f'Email: {email}',
            f'Mobile: {mobile}',
            '',
            f'License Key: {license_key}',
            f'Product: {product}',
            f'Current Plan: {current_plan}',
            f'Requested Plan: {requested_plan_name}',
        ]
        if msg:
            body_lines.extend(['', f'Customer Message:', msg])

        body = '\n'.join(body_lines)

        self._compose_email(self._support_email, subject, body)

        messagebox.showinfo(
            'Request Sent',
            'Your email client has been opened with a pre-composed renewal request.\n\n'
            'Please review and send the email to complete your request.',
            parent=self.root
        )
        self.result = {'success': True, 'message': 'Email compose opened'}
        self._on_close()

    def _compose_email(self, to: str, subject: str, body: str):
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        mailto_url = f'mailto:{to}?subject={encoded_subject}&body={encoded_body}'
        try:
            webbrowser.open(mailto_url)
        except Exception as e:
            messagebox.showerror('Error',
                                 f'Failed to open email client:\n{e}',
                                 parent=self.root)
