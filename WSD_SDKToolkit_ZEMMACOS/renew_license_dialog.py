"""Renew License Dialog - generic renewal window with license verification"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any


class RenewLicenseDialog:
    """Renewal dialog - scrollable, card-based layout.
    Verifies license via SDK, displays customer/license info, sends renewal request."""

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

        branding = self.config.get('branding', {})
        self._colors = branding.get('colors', {})
        self._labels = branding.get('labels', {})
        self._primary = self._colors.get('primary', '#1e40af')
        self._bg = self._colors.get('bg_page', '#f8f9fa')
        self._card_bg = self._colors.get('bg_card', '#ffffff')
        self._text = self._colors.get('text_primary', '#333333')
        self._text_sec = self._colors.get('text_secondary', '#555555')
        self._muted = self._colors.get('text_muted', '#888888')
        self._border = self._colors.get('border', '#dbe3ef')
        self._success = self._colors.get('success', '#16a34a')
        self._error = self._colors.get('error', '#dc2626')
        self._support_email = branding.get('support_email', 'support@websmithdigital.com')

    def show(self) -> Optional[Dict[str, Any]]:
        if not self._parent:
            raise RuntimeError("SDK dialogs require the application root window as parent")
        self._build_ui()
        self._center()
        self.root.mainloop()
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
        self._build_renewal_request(content)
        self._build_footer(content)

        if self.license_key:
            self._var_license_key.set(self.license_key)

    def _build_header(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=18)
        inner.pack(fill=tk.BOTH)
        tk.Label(inner, text='Renew License',
                 font=('Helvetica', 18, 'bold'),
                 bg=self._card_bg, fg=self._primary).pack(anchor=tk.W)
        tk.Label(inner,
                 text='Renew your subscription or request a new license from Websmith Digital.',
                 font=('Helvetica', 10),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(4, 0))

    def _build_verification(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='License Verification',
                 font=('Helvetica', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 8))

        key_row = tk.Frame(inner, bg=self._card_bg)
        key_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(key_row, text='License Number',
                 font=('Helvetica', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(0, 4))

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
            font=('Helvetica', 10, 'bold'),
            fg='white', bg=self._primary,
            activebackground=self._primary, activeforeground='white',
            bd=0, padx=20, pady=6, cursor='hand2')
        self._btn_verify.pack(side=tk.RIGHT)

        self._var_status = tk.StringVar(value='Not Verified')
        self._status_label = tk.Label(
            inner, textvariable=self._var_status,
            font=('Helvetica', 10),
            bg=self._card_bg, fg=self._muted)
        self._status_label.pack(anchor=tk.W, pady=(4, 0))

    def _build_customer_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='Customer Information',
                 font=('Helvetica', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_cust_name = tk.StringVar()
        self._var_email = tk.StringVar()
        self._var_mobile = tk.StringVar()

        for lbl, var in [('Customer Name', self._var_cust_name),
                         ('Email Address', self._var_email),
                         ('Mobile Number', self._var_mobile)]:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 8))
            tk.Label(row, text=lbl, font=('Helvetica', 10, 'bold'),
                     bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(0, 3))
            entry = tk.Entry(row, textvariable=var, font=('Helvetica', 11),
                             bg=self._card_bg, fg=self._text,
                             insertbackground=self._primary,
                             highlightbackground=self._border, highlightthickness=1,
                             relief=tk.FLAT, bd=2)
            entry.pack(fill=tk.X, ipady=6)

    def _build_license_info(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='License Information',
                 font=('Helvetica', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        self._var_plan = tk.StringVar(value='--')
        self._var_lic_status = tk.StringVar(value='--')
        self._var_expiry = tk.StringVar(value='--')

        for lbl, var in [('Current Plan', self._var_plan),
                         ('Status', self._var_lic_status),
                         ('Expiry Date', self._var_expiry)]:
            row = tk.Frame(inner, bg=self._card_bg)
            row.pack(fill=tk.X, pady=(0, 6))
            tk.Label(row, text=lbl + ':', font=('Helvetica', 10, 'bold'),
                     bg=self._card_bg, fg=self._text_sec,
                     width=18, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, textvariable=var, font=('Helvetica', 11, 'bold'),
                     bg=self._card_bg, fg=self._text).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_renewal_request(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(card, bg=self._card_bg, padx=24, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(inner, text='Renewal Request',
                 font=('Helvetica', 12, 'bold'),
                 bg=self._card_bg, fg=self._text).pack(anchor=tk.W, pady=(0, 10))

        row = tk.Frame(inner, bg=self._card_bg)
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text='To:', font=('Helvetica', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec, width=14, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(row, text=self._support_email,
                 font=('Helvetica', 11, 'bold'),
                 bg=self._card_bg, fg=self._primary).pack(side=tk.LEFT)

        row = tk.Frame(inner, bg=self._card_bg)
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text='Subject:', font=('Helvetica', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec, width=14, anchor=tk.W).pack(side=tk.LEFT)
        self._var_subject = tk.StringVar(value='License Renewal Request')
        tk.Label(row, textvariable=self._var_subject,
                 font=('Helvetica', 11),
                 bg=self._card_bg, fg=self._text).pack(side=tk.LEFT)

        tk.Label(inner, text='Request Type',
                 font=('Helvetica', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(6, 4))
        self._var_req_type = tk.StringVar(value='renew')
        radio_frame = tk.Frame(inner, bg=self._card_bg)
        radio_frame.pack(fill=tk.X, pady=(0, 6))
        for val, txt in [('renew', 'Renew Existing License'),
                         ('new', 'Request New License')]:
            tk.Radiobutton(radio_frame, text=txt, variable=self._var_req_type, value=val,
                           font=('Helvetica', 10),
                           bg=self._card_bg, fg=self._text,
                           selectcolor=self._card_bg,
                           activebackground=self._card_bg,
                           indicatoron=True).pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(inner, text='Message',
                 font=('Helvetica', 10, 'bold'),
                 bg=self._card_bg, fg=self._text_sec).pack(anchor=tk.W, pady=(6, 4))
        self._msg_text = tk.Text(inner, font=('Helvetica', 10),
                                 bg=self._card_bg, fg=self._text,
                                 insertbackground=self._primary,
                                 highlightbackground=self._border,
                                 highlightthickness=1,
                                 relief=tk.FLAT, bd=2,
                                 height=5, wrap=tk.WORD)
        self._msg_text.pack(fill=tk.X)
        self._msg_text.insert(tk.END, 'Additional details...')

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=self._bg)
        footer.pack(fill=tk.X, pady=(8, 0))

        sep = tk.Frame(footer, bg=self._border, height=1)
        sep.pack(fill=tk.X, pady=(0, 10))

        btn_frame = tk.Frame(footer, bg=self._bg)
        btn_frame.pack(fill=tk.X)

        self._btn_cancel = tk.Button(
            btn_frame, text='Cancel', command=self._on_close,
            font=('Helvetica', 10),
            fg=self._text, bg=self._colors.get('bg_button', '#e5e7eb'),
            activebackground=self._colors.get('bg_button', '#e5e7eb'),
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_cancel.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_reset = tk.Button(
            btn_frame, text='Reset', command=self._on_reset,
            font=('Helvetica', 10),
            fg=self._text, bg=self._colors.get('bg_button', '#e5e7eb'),
            activebackground=self._colors.get('bg_button', '#e5e7eb'),
            bd=0, padx=16, pady=6, cursor='hand2')
        self._btn_reset.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_send = tk.Button(
            btn_frame, text='Send Request', command=self._on_send,
            font=('Helvetica', 10, 'bold'),
            fg='white', bg=self._primary,
            activebackground=self._primary, activeforeground='white',
            bd=0, padx=20, pady=6, cursor='hand2')
        self._btn_send.pack(side=tk.RIGHT)

    def _card(self, parent) -> tk.Frame:
        return tk.Frame(parent, bg=self._card_bg,
                        highlightbackground=self._border,
                        highlightthickness=1, bd=0)

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

                details_resp = client.get_license_details(key)
                data = {**verify_resp, **details_resp}
                self.root.after(0, lambda: self._verify_success(data))

            except Exception as exc:
                self.root.after(0, lambda e=exc: self._verify_failed(str(e)))

        threading.Thread(target=_do_verify, daemon=True).start()

    def _verify_success(self, data: Dict[str, Any]):
        self._verified = True
        self._license_data = data

        self._var_status.set('\u2713 Verified')
        self._status_label.config(fg=self._success)
        self._btn_verify.config(state=tk.NORMAL, text='Verify')

        self._var_cust_name.set(data.get('customer_name', ''))
        self._var_email.set(data.get('email', data.get('customer_email', '')))
        self._var_mobile.set(data.get('mobile', data.get('customer_mobile', '')))

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

    def _verify_failed(self, msg: str):
        self._verified = False
        self._license_data = {}
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
        self._var_subject.set('License Renewal Request')
        self._var_req_type.set('renew')
        self._msg_text.delete('1.0', tk.END)
        self._msg_text.insert(tk.END, 'Additional details...')
        self._verified = False
        self._license_data = {}
        self._var_status.set('Not Verified')
        self._status_label.config(fg=self._muted)

    def _on_send(self):
        if not self._verified:
            messagebox.showwarning('Not Verified',
                                   'Verify your license first.',
                                   parent=self.root)
            return

        key = self._var_license_key.get().strip()
        cust_name = self._var_cust_name.get().strip()
        email = self._var_email.get().strip()
        mobile = self._var_mobile.get().strip()
        subject = self._var_subject.get().strip()
        msg = self._msg_text.get('1.0', tk.END).strip()
        req_type = self._var_req_type.get()

        if not msg or msg == 'Additional details...':
            msg = ''

        if not key:
            messagebox.showwarning('Input Required', 'License key is missing.',
                                   parent=self.root)
            return

        self._btn_send.config(state=tk.DISABLED, text='Sending...')
        self.root.update_idletasks()

        import threading

        def _do_send():
            try:
                client = self.client
                if client is None:
                    raise RuntimeError('SDK client not available')

                resp = client.send_renewal_request(
                    license_key=key,
                    customer_name=cust_name,
                    email=email,
                    mobile=mobile,
                    subject=subject,
                    message=msg,
                    request_type=req_type,
                )
                self.root.after(0, lambda: self._send_done(resp))

            except Exception as exc:
                self.root.after(0, lambda e=exc: self._send_error(str(e)))

        threading.Thread(target=_do_send, daemon=True).start()

    def _send_done(self, resp: Dict[str, Any]):
        self._btn_send.config(state=tk.NORMAL, text='Send Request')
        if resp.get('success'):
            messagebox.showinfo('Sent',
                                'Your renewal request has been sent to Websmith Digital.\n'
                                'You will receive a response shortly.',
                                parent=self.root)
            self.result = resp
            self._on_close()
        else:
            msg = resp.get('message', resp.get('error', 'Failed to send request.'))
            messagebox.showerror('Error', msg, parent=self.root)

    def _send_error(self, msg: str):
        self._btn_send.config(state=tk.NORMAL, text='Send Request')
        messagebox.showerror('Error', f'Failed to send request:\n{msg}',
                             parent=self.root)
