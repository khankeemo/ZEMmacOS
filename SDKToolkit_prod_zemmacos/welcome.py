"""Universal Welcome Dialog for ZEM MAC OS"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

COUNTRY_CODES = [
    {"code": "IN", "name": "India", "dial": "+91", "flag": "U0001F1EEU0001F1F3"},
    {"code": "US", "name": "United States", "dial": "+1", "flag": "U0001F1FAU0001F1F8"},
    {"code": "GB", "name": "United Kingdom", "dial": "+44", "flag": "U0001F1ECU0001F1E7"},
    {"code": "CA", "name": "Canada", "dial": "+1", "flag": "U0001F1E8U0001F1E6"},
    {"code": "AU", "name": "Australia", "dial": "+61", "flag": "U0001F1E6U0001F1FA"},
    {"code": "DE", "name": "Germany", "dial": "+49", "flag": "U0001F1E9U0001F1EA"},
    {"code": "FR", "name": "France", "dial": "+33", "flag": "U0001F1EBU0001F1F7"},
    {"code": "IT", "name": "Italy", "dial": "+39", "flag": "U0001F1EEU0001F1F9"},
    {"code": "ES", "name": "Spain", "dial": "+34", "flag": "U0001F1EAU0001F1F8"},
    {"code": "NL", "name": "Netherlands", "dial": "+31", "flag": "U0001F1F3U0001F1F1"},
    {"code": "BR", "name": "Brazil", "dial": "+55", "flag": "U0001F1E7U0001F1F7"},
    {"code": "JP", "name": "Japan", "dial": "+81", "flag": "U0001F1EFU0001F1F5"},
    {"code": "CN", "name": "China", "dial": "+86", "flag": "U0001F1E8U0001F1F3"},
    {"code": "KR", "name": "South Korea", "dial": "+82", "flag": "U0001F1F0U0001F1F7"},
    {"code": "SG", "name": "Singapore", "dial": "+65", "flag": "U0001F1F8U0001F1EC"},
    {"code": "AE", "name": "United Arab Emirates", "dial": "+971", "flag": "U0001F1E6U0001F1EA"},
    {"code": "ZA", "name": "South Africa", "dial": "+27", "flag": "U0001F1FFU0001F1E6"},
    {"code": "RU", "name": "Russia", "dial": "+7", "flag": "U0001F1F7U0001F1FA"},
    {"code": "MX", "name": "Mexico", "dial": "+52", "flag": "U0001F1F2U0001F1FD"},
    {"code": "AR", "name": "Argentina", "dial": "+54", "flag": "U0001F1E6U0001F1F7"},
    {"code": "SE", "name": "Sweden", "dial": "+46", "flag": "U0001F1F8U0001F1EA"},
    {"code": "NO", "name": "Norway", "dial": "+47", "flag": "U0001F1F3U0001F1F4"},
    {"code": "DK", "name": "Denmark", "dial": "+45", "flag": "U0001F1E9U0001F1F0"},
    {"code": "FI", "name": "Finland", "dial": "+358", "flag": "U0001F1EBU0001F1EE"},
    {"code": "CH", "name": "Switzerland", "dial": "+41", "flag": "U0001F1E8U0001F1ED"},
    {"code": "AT", "name": "Austria", "dial": "+43", "flag": "U0001F1E6U0001F1F9"},
    {"code": "BE", "name": "Belgium", "dial": "+32", "flag": "U0001F1E7U0001F1EA"},
    {"code": "IE", "name": "Ireland", "dial": "+353", "flag": "U0001F1EEU0001F1EA"},
    {"code": "PT", "name": "Portugal", "dial": "+351", "flag": "U0001F1F5U0001F1F9"},
    {"code": "GR", "name": "Greece", "dial": "+30", "flag": "U0001F1ECU0001F1F7"},
    {"code": "PL", "name": "Poland", "dial": "+48", "flag": "U0001F1F5U0001F1F1"},
    {"code": "CZ", "name": "Czech Republic", "dial": "+420", "flag": "U0001F1E8U0001F1FF"},
    {"code": "HU", "name": "Hungary", "dial": "+36", "flag": "U0001F1EDU0001F1FA"},
    {"code": "RO", "name": "Romania", "dial": "+40", "flag": "U0001F1F7U0001F1F4"},
    {"code": "IL", "name": "Israel", "dial": "+972", "flag": "U0001F1EEU0001F1F1"},
    {"code": "SA", "name": "Saudi Arabia", "dial": "+966", "flag": "U0001F1F8U0001F1E6"},
    {"code": "NG", "name": "Nigeria", "dial": "+234", "flag": "U0001F1F3U0001F1EC"},
    {"code": "EG", "name": "Egypt", "dial": "+20", "flag": "U0001F1EAU0001F1EC"},
    {"code": "KE", "name": "Kenya", "dial": "+254", "flag": "U0001F1F0U0001F1EA"},
    {"code": "PK", "name": "Pakistan", "dial": "+92", "flag": "U0001F1F5U0001F1F0"},
    {"code": "BD", "name": "Bangladesh", "dial": "+880", "flag": "U0001F1E7U0001F1E9"},
    {"code": "PH", "name": "Philippines", "dial": "+63", "flag": "U0001F1F5U0001F1ED"},
    {"code": "VN", "name": "Vietnam", "dial": "+84", "flag": "U0001F1FBU0001F1F3"},
    {"code": "TH", "name": "Thailand", "dial": "+66", "flag": "U0001F1F9U0001F1ED"},
    {"code": "MY", "name": "Malaysia", "dial": "+60", "flag": "U0001F1F2U0001F1FE"},
    {"code": "ID", "name": "Indonesia", "dial": "+62", "flag": "U0001F1EEU0001F1E9"},
    {"code": "TW", "name": "Taiwan", "dial": "+886", "flag": "U0001F1F9U0001F1FC"},
    {"code": "HK", "name": "Hong Kong", "dial": "+852", "flag": "U0001F1EDU0001F1F0"},
    {"code": "TR", "name": "Turkey", "dial": "+90", "flag": "U0001F1F9U0001F1F7"},
    {"code": "UA", "name": "Ukraine", "dial": "+380", "flag": "U0001F1FAU0001F1E6"},
]


class WelcomeDialog:
    def __init__(self, engine, support_email: str = ""):
        self.engine = engine
        self.support_email = support_email
        self.client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self.result = False
        self._otp_sent = False
        self._otp_verified = False
        self._customer_data = {}
        self.selected_country = COUNTRY_CODES[0]
        self.root = None

    def show(self) -> bool:
        self._build_ui()
        self.root.mainloop()
        return self.result

    def _build_ui(self):
        branding = self.config.get('branding', {})
        product_name = self.config.get('product', {}).get('name', 'Software')
        primary_color = branding.get('primary_color', '#6366f1')
        bg_color = "#f8f9fa"

        self.root = tk.Tk()
        self.root.title(f"Welcome to {product_name}")
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
        tk.Label(header, text=f"Welcome to {product_name}",
                 fg="white", bg=primary_color,
                 font=("Helvetica", 18, "bold")).pack(expand=True)

        form = tk.Frame(self.root, bg=bg_color, padx=30, pady=20)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="Customer Information",
                 font=("Helvetica", 12, "bold"), bg=bg_color, fg="#333").pack(anchor=tk.W, pady=(0, 10))

        tk.Label(form, text="Full Name *", font=("Helvetica", 10), bg=bg_color, fg="#555").pack(anchor=tk.W)
        self.name_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Email Address *", font=("Helvetica", 10), bg=bg_color, fg="#555").pack(anchor=tk.W)
        self.email_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.email_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Company", font=("Helvetica", 10), bg=bg_color, fg="#555").pack(anchor=tk.W)
        self.company_entry = tk.Entry(form, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.company_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        country_frame = tk.Frame(form, bg=bg_color)
        country_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(country_frame, text="Mobile Number", font=("Helvetica", 10), bg=bg_color, fg="#555").pack(anchor=tk.W)

        mobile_row = tk.Frame(country_frame, bg=bg_color)
        mobile_row.pack(fill=tk.X, pady=(2, 0))
        self.country_btn = tk.Button(mobile_row, text=f"{self.selected_country['flag']} {self.selected_country['dial']}",
                                      font=("Helvetica", 11), relief=tk.SOLID, bd=1, bg="white", fg="#333",
                                      command=self._open_country_selector)
        self.country_btn.pack(side=tk.LEFT, ipady=4)
        self.mobile_entry = tk.Entry(mobile_row, font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.mobile_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=4)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        otp_frame = tk.Frame(form, bg=bg_color)
        otp_frame.pack(fill=tk.X)
        self.otp_btn = tk.Button(otp_frame, text="Send OTP", command=self._send_otp,
                                  font=("Helvetica", 10, "bold"), bg=primary_color, fg="white", relief=tk.FLAT, padx=10, pady=5)
        self.otp_btn.pack(side=tk.LEFT)
        self.otp_status = tk.Label(otp_frame, text="", font=("Helvetica", 9), bg=bg_color, fg="#888")
        self.otp_status.pack(side=tk.LEFT, padx=(10, 0))

        self.otp_entry_frame = tk.Frame(form, bg=bg_color)
        tk.Label(self.otp_entry_frame, text="Enter OTP", font=("Helvetica", 10), bg=bg_color, fg="#555").pack(anchor=tk.W)
        otp_row = tk.Frame(self.otp_entry_frame, bg=bg_color)
        otp_row.pack(fill=tk.X, pady=(2, 0))
        self.otp_entry = tk.Entry(otp_row, font=("Helvetica", 14, "bold"), relief=tk.SOLID, bd=1, width=8)
        self.otp_entry.pack(side=tk.LEFT, ipady=4)
        self.verify_btn = tk.Button(otp_row, text="Verify OTP", command=self._verify_otp,
                                     font=("Helvetica", 10, "bold"), bg="#10b981", fg="white", relief=tk.FLAT, padx=10, pady=5)
        self.verify_btn.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        self.start_btn = tk.Button(form, text="Start Trial", command=self._start_trial,
                                    font=("Helvetica", 13, "bold"), bg="#10b981", fg="white", relief=tk.FLAT, padx=20, pady=8)
        self.start_btn.pack(pady=(0, 8))
        self.start_btn.config(state=tk.DISABLED)

        self.status_label = tk.Label(form, text="", font=("Helvetica", 9), bg=bg_color, fg="#333", wraplength=400)
        self.status_label.pack()

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        support_frame = tk.Frame(form, bg=bg_color)
        support_frame.pack(fill=tk.X)
        tk.Label(support_frame, text="Need a license?", font=("Helvetica", 9), bg=bg_color, fg="#888").pack()
        tk.Label(support_frame, text=self.support_email or "support@websmithdigital.com",
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
            for c in COUNTRY_CODES:
                if ft in c['name'].lower() or ft in c['dial'] or ft in c['code'].lower():
                    listbox.insert(tk.END, f"{c['flag']} {c['name']} ({c['dial']})")
        populate_list()
        search_var.trace("w", lambda *a: populate_list(search_var.get()))

        def on_select(ev):
            sel = listbox.curselection()
            if not sel: return
            for c in COUNTRY_CODES:
                if f"{c['flag']} {c['name']} ({c['dial']})" == listbox.get(sel[0]):
                    self.selected_country = c; self.country_btn.config(text=f"{c['flag']} {c['dial']}")
                    top.destroy(); break
        listbox.bind("<<ListboxSelect>>", on_select); listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _set_loading(self, loading: bool):
        state = 'disabled' if loading else 'normal'
        for w in [self.otp_btn, self.verify_btn, self.start_btn]:
            if w: w.config(state=state)

    def _send_otp(self):
        email = self.email_entry.get().strip()
        if not email: self.otp_status.config(text="Please enter email first", fg="#dc2626"); return
        self._set_loading(True); self.otp_status.config(text="Sending OTP...", fg="#888")
        def do():
            try:
                r = self.engine.send_otp(email, purpose='registration')
                self.root.after(0, lambda: self._on_otp_sent(r))
            except Exception as e:
                self.root.after(0, lambda: self.otp_status.config(text=f"Error: {str(e)}", fg="#dc2626"))
        threading.Thread(target=do, daemon=True).start()

    def _on_otp_sent(self, result):
        self._set_loading(False)
        if result.get('success'):
            self._otp_sent = True; self.otp_status.config(text="OTP sent! Check email", fg="#16a34a")
            self.otp_entry_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.otp_status.config(text=result.get('message', 'Failed to send'), fg="#dc2626")

    def _verify_otp(self):
        if not self._otp_sent: return
        otp = self.otp_entry.get().strip(); email = self.email_entry.get().strip()
        if not otp: self.otp_status.config(text="Enter OTP", fg="#dc2626"); return
        self._set_loading(True); self.otp_status.config(text="Verifying...", fg="#888")
        def do():
            try:
                r = self.engine.verify_otp(email, otp)
                self.root.after(0, lambda: self._on_otp_verified(r))
            except Exception as e:
                self.root.after(0, lambda: self.otp_status.config(text=f"Error: {str(e)}", fg="#dc2626"))
        threading.Thread(target=do, daemon=True).start()

    def _on_otp_verified(self, result):
        self._set_loading(False)
        if result.get('success'):
            self._otp_verified = True; self.otp_status.config(text="OTP verified!", fg="#16a34a")
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.otp_status.config(text=result.get('message', 'Invalid OTP'), fg="#dc2626")

    def _start_trial(self):
        name = self.name_entry.get().strip(); email = self.email_entry.get().strip()
        if not name or not email: self.status_label.config(text="Name and email required", fg="#dc2626"); return
        if not self._otp_verified: self.status_label.config(text="Verify OTP first", fg="#dc2626"); return
        self._set_loading(True); self.status_label.config(text="Starting trial...", fg="#333")
        def do():
            try:
                if self.client:
                    self.engine.store_customer({
                        "name": name, "email": email, "phone": f"{self.selected_country['dial']}{self.mobile_entry.get().strip()}",
                        "company": self.company_entry.get().strip(), "country": self.selected_country['code'],
                    })
                r = self.engine.start_trial(email=email, name=name, company=self.company_entry.get().strip())
                self.root.after(0, lambda: self._on_trial_result(r))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}", fg="#dc2626"))
        threading.Thread(target=do, daemon=True).start()

    def _on_trial_result(self, result):
        self._set_loading(False)
        if result.get('success'):
            self.status_label.config(text="Trial started!", fg="#16a34a"); self.result = True
            self.root.after(500, self.root.destroy)
        else:
            self.status_label.config(text=result.get('message', 'Failed'), fg="#dc2626")
