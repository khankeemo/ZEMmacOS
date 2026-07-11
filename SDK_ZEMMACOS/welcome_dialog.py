#!/usr/bin/env python3
"""Universal Welcome Dialog for ZEM MAC OS

Shows on first application launch. Collects customer information,
sends OTP verification, and starts a trial via the Websmith API.
"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

from .client import ApiClient, ApiError

COUNTRY_CODES = [
    {"code": "IN", "name": "India", "dial": "+91", "flag": "IND"},
    {"code": "US", "name": "United States", "dial": "+1", "flag": "USA"},
    {"code": "GB", "name": "United Kingdom", "dial": "+44", "flag": "GBR"},
    {"code": "CA", "name": "Canada", "dial": "+1", "flag": "CAN"},
    {"code": "AU", "name": "Australia", "dial": "+61", "flag": "AUS"},
    {"code": "AE", "name": "United Arab Emirates", "dial": "+971", "flag": "ARE"},
    {"code": "DE", "name": "Germany", "dial": "+49", "flag": "DEU"},
    {"code": "FR", "name": "France", "dial": "+33", "flag": "FRA"},
    {"code": "IT", "name": "Italy", "dial": "+39", "flag": "ITA"},
    {"code": "ES", "name": "Spain", "dial": "+34", "flag": "ESP"},
    {"code": "JP", "name": "Japan", "dial": "+81", "flag": "JPN"},
    {"code": "CN", "name": "China", "dial": "+86", "flag": "CHN"},
    {"code": "BR", "name": "Brazil", "dial": "+55", "flag": "BRA"},
    {"code": "RU", "name": "Russia", "dial": "+7", "flag": "RUS"},
    {"code": "KR", "name": "South Korea", "dial": "+82", "flag": "KOR"},
    {"code": "SG", "name": "Singapore", "dial": "+65", "flag": "SGP"},
    {"code": "ZA", "name": "South Africa", "dial": "+27", "flag": "ZAF"},
    {"code": "NG", "name": "Nigeria", "dial": "+234", "flag": "NGA"},
    {"code": "EG", "name": "Egypt", "dial": "+20", "flag": "EGY"},
    {"code": "KE", "name": "Kenya", "dial": "+254", "flag": "KEN"},
    {"code": "MA", "name": "Morocco", "dial": "+212", "flag": "MAR"},
    {"code": "AR", "name": "Argentina", "dial": "+54", "flag": "ARG"},
    {"code": "CO", "name": "Colombia", "dial": "+57", "flag": "COL"},
    {"code": "MX", "name": "Mexico", "dial": "+52", "flag": "MEX"},
    {"code": "SE", "name": "Sweden", "dial": "+46", "flag": "SWE"},
    {"code": "NO", "name": "Norway", "dial": "+47", "flag": "NOR"},
    {"code": "DK", "name": "Denmark", "dial": "+45", "flag": "DNK"},
    {"code": "FI", "name": "Finland", "dial": "+358", "flag": "FIN"},
    {"code": "NL", "name": "Netherlands", "dial": "+31", "flag": "NLD"},
    {"code": "CH", "name": "Switzerland", "dial": "+41", "flag": "CHE"},
    {"code": "AT", "name": "Austria", "dial": "+43", "flag": "AUT"},
    {"code": "BE", "name": "Belgium", "dial": "+32", "flag": "BEL"},
    {"code": "IE", "name": "Ireland", "dial": "+353", "flag": "IRL"},
    {"code": "PT", "name": "Portugal", "dial": "+351", "flag": "PRT"},
    {"code": "GR", "name": "Greece", "dial": "+30", "flag": "GRC"},
    {"code": "PL", "name": "Poland", "dial": "+48", "flag": "POL"},
    {"code": "CZ", "name": "Czech Republic", "dial": "+420", "flag": "CZE"},
    {"code": "HU", "name": "Hungary", "dial": "+36", "flag": "HUN"},
    {"code": "RO", "name": "Romania", "dial": "+40", "flag": "ROU"},
    {"code": "TR", "name": "Turkey", "dial": "+90", "flag": "TUR"},
    {"code": "IL", "name": "Israel", "dial": "+972", "flag": "ISR"},
    {"code": "SA", "name": "Saudi Arabia", "dial": "+966", "flag": "SAU"},
    {"code": "PK", "name": "Pakistan", "dial": "+92", "flag": "PAK"},
    {"code": "BD", "name": "Bangladesh", "dial": "+880", "flag": "BGD"},
    {"code": "UA", "name": "Ukraine", "dial": "+380", "flag": "UKR"},
    {"code": "TH", "name": "Thailand", "dial": "+66", "flag": "THA"},
    {"code": "VN", "name": "Vietnam", "dial": "+84", "flag": "VNM"},
    {"code": "ID", "name": "Indonesia", "dial": "+62", "flag": "IDN"},
    {"code": "PH", "name": "Philippines", "dial": "+63", "flag": "PHL"},
    {"code": "MY", "name": "Malaysia", "dial": "+60", "flag": "MYS"},
    {"code": "TW", "name": "Taiwan", "dial": "+886", "flag": "TWN"},
    {"code": "HK", "name": "Hong Kong", "dial": "+852", "flag": "HKG"},
]


class WelcomeDialog:
    """Universal welcome dialog for SDK-powered applications."""

    def __init__(self, engine, support_email: str = ""):
        self.engine = engine
        self.support_email = support_email
        self.client: Optional[ApiClient] = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})

        self.result = False
        self._otp_sent = False
        self._otp_verified = False
        self._customer_data = {}

        self.selected_country = COUNTRY_CODES[0]

        self._build_ui()

    def _build_ui(self):
        """Build the welcome dialog UI using tkinter."""
        self.root = tk.Tk()
        self.root.title("Welcome to ZEM MAC OS")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8f9fa")

        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

        header = tk.Frame(self.root, bg="#6366f1", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Welcome to ZEM MAC OS",
                 fg="white", bg="#6366f1",
                 font=("Helvetica", 18, "bold")).pack(expand=True)

        form = tk.Frame(self.root, bg="#f8f9fa", padx=30, pady=20)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="Customer Information",
                 font=("Helvetica", 12, "bold"),
                 bg="#f8f9fa", fg="#333").pack(anchor=tk.W, pady=(0, 10))

        tk.Label(form, text="Full Name *", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.name_entry = tk.Entry(form, font=("Helvetica", 11),
                                    relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Email Address *", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.email_entry = tk.Entry(form, font=("Helvetica", 11),
                                     relief=tk.SOLID, bd=1)
        self.email_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        tk.Label(form, text="Company", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.company_entry = tk.Entry(form, font=("Helvetica", 11),
                                       relief=tk.SOLID, bd=1)
        self.company_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        country_frame = tk.Frame(form, bg="#f8f9fa")
        country_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(country_frame, text="Mobile Number", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)

        mobile_row = tk.Frame(country_frame, bg="#f8f9fa")
        mobile_row.pack(fill=tk.X, pady=(2, 0))

        self.country_btn = tk.Button(
            mobile_row,
            text=f"{self.selected_country['flag']} {self.selected_country['dial']}",
            font=("Helvetica", 11),
            relief=tk.SOLID, bd=1,
            bg="white", fg="#333",
            command=self._open_country_selector
        )
        self.country_btn.pack(side=tk.LEFT, ipady=4)

        self.mobile_entry = tk.Entry(mobile_row, font=("Helvetica", 11),
                                      relief=tk.SOLID, bd=1)
        self.mobile_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                                padx=(5, 0), ipady=4)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        otp_frame = tk.Frame(form, bg="#f8f9fa")
        otp_frame.pack(fill=tk.X)

        self.otp_btn = tk.Button(
            otp_frame, text="Send OTP",
            command=self._send_otp,
            font=("Helvetica", 10, "bold"),
            bg="#6366f1", fg="white",
            relief=tk.FLAT, padx=10, pady=5
        )
        self.otp_btn.pack(side=tk.LEFT)

        self.otp_status = tk.Label(
            otp_frame, text="",
            font=("Helvetica", 9),
            bg="#f8f9fa", fg="#888"
        )
        self.otp_status.pack(side=tk.LEFT, padx=(10, 0))

        self.otp_entry_frame = tk.Frame(form, bg="#f8f9fa")

        tk.Label(self.otp_entry_frame, text="Enter OTP",
                 font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)

        otp_row = tk.Frame(self.otp_entry_frame, bg="#f8f9fa")
        otp_row.pack(fill=tk.X, pady=(2, 0))

        self.otp_entry = tk.Entry(otp_row, font=("Helvetica", 14, "bold"),
                                   relief=tk.SOLID, bd=1, width=8)
        self.otp_entry.pack(side=tk.LEFT, ipady=4)

        self.verify_btn = tk.Button(
            otp_row, text="Verify OTP",
            command=self._verify_otp,
            font=("Helvetica", 10, "bold"),
            bg="#10b981", fg="white",
            relief=tk.FLAT, padx=10, pady=5
        )
        self.verify_btn.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        self.start_btn = tk.Button(
            form, text="Start Trial",
            command=self._start_trial,
            font=("Helvetica", 13, "bold"),
            bg="#10b981", fg="white",
            relief=tk.FLAT, padx=20, pady=8
        )
        self.start_btn.pack(pady=(0, 8))
        self.start_btn.config(state=tk.DISABLED)

        self.status_label = tk.Label(
            form, text="",
            font=("Helvetica", 9),
            bg="#f8f9fa", fg="#333",
            wraplength=400
        )
        self.status_label.pack()

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        support_frame = tk.Frame(form, bg="#f8f9fa")
        support_frame.pack(fill=tk.X)
        tk.Label(support_frame, text="Need a license?",
                 font=("Helvetica", 9),
                 bg="#f8f9fa", fg="#888").pack()
        tk.Label(support_frame, text=self.support_email or "support@websmithdigital.com",
                 font=("Helvetica", 9, "italic"),
                 bg="#f8f9fa", fg="#6366f1").pack()

    def _open_country_selector(self):
        top = tk.Toplevel(self.root)
        top.title("Select Country")
        top.geometry("320x400")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=search_var,
                                 font=("Helvetica", 11),
                                 relief=tk.SOLID, bd=1)
        search_entry.pack(fill=tk.X, padx=10, pady=(10, 5), ipady=3)
        search_entry.focus_set()

        list_frame = tk.Frame(top)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, font=("Helvetica", 10),
                              yscrollcommand=scrollbar.set,
                              relief=tk.SOLID, bd=1)
        scrollbar.config(command=listbox.yview)

        def populate_list(filter_text=""):
            listbox.delete(0, tk.END)
            ft = filter_text.lower()
            for c in COUNTRY_CODES:
                if (ft in c['name'].lower() or
                    ft in c['dial'] or
                    ft in c['code'].lower()):
                    listbox.insert(tk.END,
                                   f"{c['flag']} {c['name']} ({c['dial']})")

        populate_list()

        def on_search(*args):
            populate_list(search_var.get())

        search_var.trace("w", on_search)

        def on_select(event):
            selection = listbox.curselection()
            if not selection:
                return
            raw = listbox.get(selection[0])
            for c in COUNTRY_CODES:
                if f"{c['flag']} {c['name']} ({c['dial']})" == raw:
                    self.selected_country = c
                    self.country_btn.config(
                        text=f"{c['flag']} {c['dial']}"
                    )
                    top.destroy()
                    break

        listbox.bind("<<ListboxSelect>>", on_select)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _send_otp(self):
        email = self.email_entry.get().strip()
        if not email:
            self.otp_status.config(text="Please enter an email first", fg="#ef4444")
            return

        self.otp_btn.config(state=tk.DISABLED, text="Sending...")
        self.otp_status.config(text="", fg="#888")

        def do_send():
            try:
                config = self.config
                api_config = config.get('api', {})
                base_url = api_config.get('url', '').rstrip('/')

                import requests
                resp = requests.post(
                    f"{base_url}/internal/backend/api/auth/forgot-password",
                    json={"email": email},
                    timeout=15
                )
                data = resp.json() if resp.ok else {}

                self.root.after(0, lambda: self._on_otp_sent(
                    data.get('success', False),
                    data.get('message', '')
                ))
            except Exception as e:
                self.root.after(0, lambda: self._on_otp_sent(
                    False, f"Connection error: {str(e)}"
                ))

        threading.Thread(target=do_send, daemon=True).start()

    def _on_otp_sent(self, success: bool, message: str):
        if success:
            self._otp_sent = True
            self.otp_status.config(text="OTP sent! Check your email.", fg="#10b981")
            self.otp_btn.config(text="Resend OTP", state=tk.NORMAL)
            self.otp_entry_frame.pack(fill=tk.X, pady=(8, 0))
        else:
            self.otp_status.config(
                text=message or "Failed to send OTP. Try again.",
                fg="#ef4444"
            )
            self.otp_btn.config(text="Send OTP", state=tk.NORMAL)

    def _verify_otp(self):
        otp = self.otp_entry.get().strip()
        if not otp:
            self.otp_status.config(text="Please enter the OTP", fg="#ef4444")
            return

        email = self.email_entry.get().strip()
        self.verify_btn.config(state=tk.DISABLED, text="Verifying...")

        def do_verify():
            try:
                config = self.config
                api_config = config.get('api', {})
                base_url = api_config.get('url', '').rstrip('/')

                import requests
                resp = requests.post(
                    f"{base_url}/internal/backend/api/auth/verify-otp",
                    json={"email": email, "otp": otp},
                    timeout=15
                )
                data = resp.json() if resp.ok else {}
                success = data.get('success', False) if resp.ok else False

                self.root.after(0, lambda: self._on_otp_verified(success, data.get('message', '')))
            except Exception as e:
                self.root.after(0, lambda: self._on_otp_verified(
                    False, f"Verification error: {str(e)}"
                ))

        threading.Thread(target=do_verify, daemon=True).start()

    def _on_otp_verified(self, success: bool, message: str):
        if success:
            self._otp_verified = True
            self.otp_status.config(text="OTP verified!", fg="#10b981")
            self.verify_btn.config(text="Verified", state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.otp_status.config(
                text=message or "Invalid OTP. Try again.",
                fg="#ef4444"
            )
            self.verify_btn.config(text="Verify OTP", state=tk.NORMAL)

    def _start_trial(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()

        if not name or not email:
            self.status_label.config(text="Please fill in Name and Email", fg="#ef4444")
            return

        self.start_btn.config(state=tk.DISABLED, text="Starting Trial...")
        self.status_label.config(text="", fg="#333")

        def do_trial():
            try:
                hardware_id = self.engine._hardware.get_fingerprint()
                result = self.engine.start_trial(
                    email=email,
                    company=self.company_entry.get().strip() or None
                )

                if result.get('success'):
                    self._customer_data = {
                        "name": name,
                        "email": email,
                        "company": self.company_entry.get().strip(),
                        "country_code": self.selected_country['dial'],
                        "mobile": self.mobile_entry.get().strip(),
                        "hardware_id": hardware_id,
                    }
                    self.result = True
                    self.root.after(0, self.root.destroy)
                else:
                    err = result.get('error', {})
                    msg = err.get('message', 'Failed to start trial') if isinstance(err, dict) else str(err)
                    self.root.after(0, lambda: self._on_trial_failed(msg))
            except Exception as e:
                self.root.after(0, lambda: self._on_trial_failed(str(e)))

        threading.Thread(target=do_trial, daemon=True).start()

    def _on_trial_failed(self, message: str):
        self.status_label.config(text=f"Trial failed: {message}", fg="#ef4444")
        self.start_btn.config(text="Start Trial", state=tk.NORMAL)

    def run(self):
        """Run the dialog and return True if trial was started."""
        self.root.mainloop()
        return self.result


def show_welcome_dialog(engine) -> bool:
    """Show the welcome dialog and return True if onboarding completed."""
    dialog = WelcomeDialog(engine)
    return dialog.run()
