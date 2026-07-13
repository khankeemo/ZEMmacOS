"""Universal Welcome Dialog for ZEM MAC OS"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

COUNTRY_FALLBACK = [
    {"code": "IN", "name": "India", "dial": "+91", "flag": "\U0001F1EE\U0001F1F3"},
    {"code": "US", "name": "United States", "dial": "+1", "flag": "\U0001F1FA\U0001F1F8"},
    {"code": "GB", "name": "United Kingdom", "dial": "+44", "flag": "\U0001F1EC\U0001F1E7"},
]


class WelcomeDialog:
    def __init__(self, engine, parent=None, support_email: str = ""):
        self.engine = engine
        self._parent = parent
        self.support_email = support_email
        self.client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self.result = False
        self._otp_sent = False
        self._otp_verified = False
        self._customer_data = {}
        self._countries = []
        self.selected_country = None
        self.root = None

    def show(self) -> bool:
        self._load_countries()
        self._build_ui()
        self.root.wait_window()
        return self.result

    def _load_countries(self):
        try:
            result = self.engine.get_countries()
            if result.get('success'):
                self._countries = result.get('data', result.get('countries', []))
        except Exception:
            pass
        if not self._countries:
            self._countries = COUNTRY_FALLBACK
        self.selected_country = self._countries[0]

    def _build_ui(self):
        branding = self.config.get('branding', {})
        product_name = self.config.get('product', {}).get('name', '')
        colors = branding.get('colors', {})
        primary_color = colors.get('primary', branding.get('primary_color', '#6366f1'))
        bg_color = colors.get('bg_page', '#f8f9fa')
        labels = branding.get('labels', {})

        if not self._parent:
            raise RuntimeError("SDK dialogs require the application root window as parent")
        self.root = tk.Toplevel(self._parent)
        self.root.transient(self._parent)
        self.root.grab_set()
        self.root.title(labels.get('welcome_title', f"Welcome to {product_name}"))
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg=bg_color)

        self.root.update_idletasks()
        w = self.root.winfo_width(); h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth(); sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        header = tk.Frame(self.root, bg=primary_color, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=labels.get('welcome_title', f"Welcome to {product_name}"),
                 fg="white", bg=primary_color,
                 font=("Helvetica", 18, "bold")).pack(expand=True)

        form = tk.Frame(self.root, bg=bg_color, padx=30, pady=20)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text=labels.get('customer_info_section', "Customer Information"),
                 font=("Helvetica", 12, "bold"), bg=bg_color, fg="#333").pack(anchor=tk.W, pady=(0, 10))

        tk.Label(form, text="Full Name *", font=("Helvetica", 10), bg=bg_color, fg=colors.get('text_secondary', '#555')).pack(anchor=tk.W)
        self.name_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Email Address *", font=("Helvetica", 10), bg=bg_color, fg=colors.get('text_secondary', '#555')).pack(anchor=tk.W)
        self.email_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.email_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Company", font=("Helvetica", 10), bg=bg_color, fg=colors.get('text_secondary', '#555')).pack(anchor=tk.W)
        self.company_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.company_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        country_frame = tk.Frame(form, bg=bg_color)
        country_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(country_frame, text=labels.get('mobile_label', "Mobile Number"), font=("Helvetica", 10), bg=bg_color, fg=colors.get('text_secondary', '#555')).pack(anchor=tk.W)

        mobile_row = tk.Frame(country_frame, bg=bg_color)
        mobile_row.pack(fill=tk.X, pady=(2, 0))
        self.country_btn = tk.Button(mobile_row, text=f"{self.selected_country['flag']} {self.selected_country['dial']}",
                                      font=("Helvetica", 11), relief=tk.SOLID, bd=1, bg="white", fg=colors.get('text_primary', '#333'),
                                      command=self._open_country_selector)
        self.country_btn.pack(side=tk.LEFT, ipady=4)
        self.mobile_entry = tk.Entry(mobile_row, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.mobile_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=4)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        otp_frame = tk.Frame(form, bg=bg_color)
        otp_frame.pack(fill=tk.X)
        self.otp_btn = tk.Button(otp_frame, text=labels.get('send_otp_btn', "Send OTP"), command=self._send_otp,
                                  font=("Helvetica", 10, "bold"), bg=primary_color, fg="white", relief=tk.FLAT, padx=10, pady=5)
        self.otp_btn.pack(side=tk.LEFT)
        self.otp_status = tk.Label(otp_frame, text="", font=("Helvetica", 9), bg=bg_color, fg=colors.get('text_muted', '#888'))
        self.otp_status.pack(side=tk.LEFT, padx=(10, 0))

        self.otp_entry_frame = tk.Frame(form, bg=bg_color)
        self.otp_entry_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Label(self.otp_entry_frame, text=labels.get('enter_otp_label', "Enter OTP"), font=("Helvetica", 10), bg=bg_color, fg=colors.get('text_secondary', '#555')).pack(anchor=tk.W)
        otp_row = tk.Frame(self.otp_entry_frame, bg=bg_color)
        otp_row.pack(fill=tk.X, pady=(2, 0))
        self.otp_entry = tk.Entry(otp_row, font=("Helvetica", 14, "bold"), relief=tk.SOLID, bd=1, width=8)
        self.otp_entry.pack(side=tk.LEFT, ipady=4)
        self.verify_btn = tk.Button(otp_row, text=labels.get('verify_otp_btn', "Verify OTP"), command=self._verify_otp,
                                     font=("Helvetica", 10, "bold"), bg=colors.get('info', '#10b981'), fg="white", relief=tk.FLAT, padx=10, pady=5, state=tk.DISABLED)
        self.verify_btn.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        self.start_btn = tk.Button(form, text=labels.get('start_trial_btn', "Start Trial"), command=self._start_trial,
                                    font=("Helvetica", 13, "bold"), bg=colors.get('info', '#10b981'), fg="white", relief=tk.FLAT, padx=20, pady=8)
        self.start_btn.pack(pady=(0, 8))
        self.start_btn.config(state=tk.DISABLED)

        self.status_label = tk.Label(form, text="", font=("Helvetica", 9), bg=bg_color, fg=colors.get('text_primary', '#333'), wraplength=400)
        self.status_label.pack()

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        support_frame = tk.Frame(form, bg=bg_color)
        support_frame.pack(fill=tk.X)
        tk.Label(support_frame, text=labels.get('need_license_label', "Need a license?"), font=("Helvetica", 9), bg=bg_color, fg=colors.get('text_muted', '#888')).pack()
        email_text = branding.get('support_email') or self.support_email or "support@websmithdigital.com"
        tk.Label(support_frame, text=email_text,
                 font=("Helvetica", 9, "italic"), bg=bg_color, fg=primary_color).pack()

        self.root.bind('<Escape>', lambda e: self.root.destroy())

    def _open_country_selector(self):
        top = tk.Toplevel(self.root)
        top.title("Select Country"); top.geometry("320x400"); top.resizable(False, False)
        top.transient(self.root); top.grab_set()
        search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=search_var, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        search_entry.pack(fill=tk.X, padx=10, pady=(10, 5), ipady=3); search_entry.focus_set()
        list_frame = tk.Frame(top); list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar = tk.Scrollbar(list_frame); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(list_frame, font=("Helvetica", 10), yscrollcommand=scrollbar.set, relief=tk.SOLID, bd=1)
        scrollbar.config(command=listbox.yview)

        def populate_list(ft=""):
            listbox.delete(0, tk.END); ft = ft.lower()
            for c in self._countries:
                if ft in c['name'].lower() or ft in c['dial'] or ft in c['code'].lower():
                    listbox.insert(tk.END, f"{c['flag']} {c['name']} ({c['dial']})")
        populate_list()
        search_var.trace("w", lambda *a: populate_list(search_var.get()))

        def on_select(ev):
            sel = listbox.curselection()
            if not sel: return
            for c in self._countries:
                if f"{c['flag']} {c['name']} ({c['dial']})" == listbox.get(sel[0]):
                    self.selected_country = c; self.country_btn.config(text=f"{c['flag']} {c['dial']}")
                    top.destroy(); break
        listbox.bind("<<ListboxSelect>>", on_select); listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _set_loading(self, loading: bool):
        state = 'disabled' if loading else 'normal'
        for w in [self.otp_btn, self.verify_btn, self.start_btn]:
            if w: w.config(state=state)

    def _send_otp(self):
        colors = self.config.get('branding', {}).get('colors', {})
        email = self.email_entry.get().strip()
        if not email: self.otp_status.config(text="Please enter email first", fg=colors.get('error', '#dc2626')); return
        self._set_loading(True); self.otp_status.config(text="Sending OTP...", fg=colors.get('text_muted', '#888'))
        def do():
            try:
                r = self.engine.send_otp(email, purpose='registration')
                self.root.after(0, lambda: self._on_otp_sent(r))
            except Exception as e:
                self.root.after(0, lambda: self.otp_status.config(text=f"Error: {str(e)}", fg=colors.get('error', '#dc2626')))
        threading.Thread(target=do, daemon=True).start()

    def _on_otp_sent(self, result):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if result.get('success'):
            self._otp_sent = True; self.otp_status.config(text="OTP sent! Check email", fg=colors.get('success', '#16a34a'))
            self.verify_btn.config(state=tk.NORMAL)
        else:
            self.otp_status.config(text=result.get('message', 'Failed to send'), fg=colors.get('error', '#dc2626'))

    def _verify_otp(self):
        colors = self.config.get('branding', {}).get('colors', {})
        if not self._otp_sent: return
        otp = self.otp_entry.get().strip(); email = self.email_entry.get().strip()
        if not otp: self.otp_status.config(text="Enter OTP", fg=colors.get('error', '#dc2626')); return
        self._set_loading(True); self.otp_status.config(text="Verifying...", fg=colors.get('text_muted', '#888'))
        def do():
            try:
                r = self.engine.verify_otp(email, otp)
                self.root.after(0, lambda: self._on_otp_verified(r))
            except Exception as e:
                self.root.after(0, lambda: self.otp_status.config(text=f"Error: {str(e)}", fg=colors.get('error', '#dc2626')))
        threading.Thread(target=do, daemon=True).start()

    def _on_otp_verified(self, result):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if result.get('success'):
            self._otp_verified = True; self.otp_status.config(text="OTP verified!", fg=colors.get('success', '#16a34a'))
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.otp_status.config(text=result.get('message', 'Invalid OTP'), fg=colors.get('error', '#dc2626'))

    def _start_trial(self):
        colors = self.config.get('branding', {}).get('colors', {})
        name = self.name_entry.get().strip(); email = self.email_entry.get().strip()
        if not name or not email: self.status_label.config(text="Name and email required", fg=colors.get('error', '#dc2626')); return
        if not self._otp_verified: self.status_label.config(text="Verify OTP first", fg=colors.get('error', '#dc2626')); return
        self._set_loading(True); self.status_label.config(text="Starting trial...", fg=colors.get('text_primary', '#333'))
        def do():
            try:
                if self.client:
                    self.engine.store_customer({
                        "name": name, "email": email, "mobile": f"{self.selected_country['dial']}{self.mobile_entry.get().strip()}",
                        "company_name": self.company_entry.get().strip(), "country_code": self.selected_country['code'],
                        "hardware_id": self.engine.get_hardware_id(),
                    })
                r = self.engine.start_trial(email=email, name=name, company=self.company_entry.get().strip())
                self.root.after(0, lambda: self._on_trial_result(r))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}", fg=colors.get('error', '#dc2626')))
        threading.Thread(target=do, daemon=True).start()

    def _on_trial_result(self, result):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if result.get('success'):
            self.status_label.config(text="Trial started!", fg=colors.get('success', '#16a34a')); self.result = True
            self.root.after(500, self.root.destroy)
        else:
            self.status_label.config(text=result.get('message', 'Failed'), fg=colors.get('error', '#dc2626'))
