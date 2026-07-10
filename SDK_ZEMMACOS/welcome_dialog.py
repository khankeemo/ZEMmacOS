#!/usr/bin/env python3
"""Universal Welcome Dialog for ZEM MAC OS

Shows on first application launch. Collects customer information,
sends OTP verification, and starts a trial via the Websmith API.

DEPENDENCIES:
- tkinter (built-in Python)
- threading (built-in)
- .client (ApiClient)
- .license_engine (LicenseEngine)

USAGE:
    from .welcome_dialog import show_welcome_dialog
    success = show_welcome_dialog(engine)
"""

import json
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

from .client import ApiClient, ApiError

# Embedded country codes (from Websmith data source)
COUNTRY_CODES = [
    {"code": "IN", "name": "India", "dial": "+91", "flag": "🇮🇳"},
    {"code": "US", "name": "United States", "dial": "+1", "flag": "🇺🇸"},
    {"code": "GB", "name": "United Kingdom", "dial": "+44", "flag": "🇬🇧"},
    {"code": "CA", "name": "Canada", "dial": "+1", "flag": "🇨🇦"},
    {"code": "AU", "name": "Australia", "dial": "+61", "flag": "🇦🇺"},
    {"code": "AE", "name": "United Arab Emirates", "dial": "+971", "flag": "🇦🇪"},
    {"code": "DE", "name": "Germany", "dial": "+49", "flag": "🇩🇪"},
    {"code": "FR", "name": "France", "dial": "+33", "flag": "🇫🇷"},
    {"code": "IT", "name": "Italy", "dial": "+39", "flag": "🇮🇹"},
    {"code": "ES", "name": "Spain", "dial": "+34", "flag": "🇪🇸"},
    {"code": "JP", "name": "Japan", "dial": "+81", "flag": "🇯🇵"},
    {"code": "CN", "name": "China", "dial": "+86", "flag": "🇨🇳"},
    {"code": "BR", "name": "Brazil", "dial": "+55", "flag": "🇧🇷"},
    {"code": "RU", "name": "Russia", "dial": "+7", "flag": "🇷🇺"},
    {"code": "KR", "name": "South Korea", "dial": "+82", "flag": "🇰🇷"},
    {"code": "SG", "name": "Singapore", "dial": "+65", "flag": "🇸🇬"},
    {"code": "ZA", "name": "South Africa", "dial": "+27", "flag": "🇿🇦"},
    {"code": "NG", "name": "Nigeria", "dial": "+234", "flag": "🇳🇬"},
    {"code": "EG", "name": "Egypt", "dial": "+20", "flag": "🇪🇬"},
    {"code": "KE", "name": "Kenya", "dial": "+254", "flag": "🇰🇪"},
    {"code": "MA", "name": "Morocco", "dial": "+212", "flag": "🇲🇦"},
    {"code": "AR", "name": "Argentina", "dial": "+54", "flag": "🇦🇷"},
    {"code": "CO", "name": "Colombia", "dial": "+57", "flag": "🇨🇴"},
    {"code": "MX", "name": "Mexico", "dial": "+52", "flag": "🇲🇽"},
    {"code": "SE", "name": "Sweden", "dial": "+46", "flag": "🇸🇪"},
    {"code": "NO", "name": "Norway", "dial": "+47", "flag": "🇳🇴"},
    {"code": "DK", "name": "Denmark", "dial": "+45", "flag": "🇩🇰"},
    {"code": "FI", "name": "Finland", "dial": "+358", "flag": "🇫🇮"},
    {"code": "NL", "name": "Netherlands", "dial": "+31", "flag": "🇳🇱"},
    {"code": "CH", "name": "Switzerland", "dial": "+41", "flag": "🇨🇭"},
    {"code": "AT", "name": "Austria", "dial": "+43", "flag": "🇦🇹"},
    {"code": "BE", "name": "Belgium", "dial": "+32", "flag": "🇧🇪"},
    {"code": "IE", "name": "Ireland", "dial": "+353", "flag": "🇮🇪"},
    {"code": "PT", "name": "Portugal", "dial": "+351", "flag": "🇵🇹"},
    {"code": "GR", "name": "Greece", "dial": "+30", "flag": "🇬🇷"},
    {"code": "PL", "name": "Poland", "dial": "+48", "flag": "🇵🇱"},
    {"code": "CZ", "name": "Czech Republic", "dial": "+420", "flag": "🇨🇿"},
    {"code": "HU", "name": "Hungary", "dial": "+36", "flag": "🇭🇺"},
    {"code": "RO", "name": "Romania", "dial": "+40", "flag": "🇷🇴"},
    {"code": "BG", "name": "Bulgaria", "dial": "+359", "flag": "🇧🇬"},
    {"code": "HR", "name": "Croatia", "dial": "+385", "flag": "🇭🇷"},
    {"code": "SK", "name": "Slovakia", "dial": "+421", "flag": "🇸🇰"},
    {"code": "SI", "name": "Slovenia", "dial": "+386", "flag": "🇸🇮"},
    {"code": "LT", "name": "Lithuania", "dial": "+370", "flag": "🇱🇹"},
    {"code": "LV", "name": "Latvia", "dial": "+371", "flag": "🇱🇻"},
    {"code": "EE", "name": "Estonia", "dial": "+372", "flag": "🇪🇪"},
    {"code": "IS", "name": "Iceland", "dial": "+354", "flag": "🇮🇸"},
    {"code": "MT", "name": "Malta", "dial": "+356", "flag": "🇲🇹"},
    {"code": "LU", "name": "Luxembourg", "dial": "+352", "flag": "🇱🇺"},
    {"code": "CY", "name": "Cyprus", "dial": "+357", "flag": "🇨🇾"},
    {"code": "IL", "name": "Israel", "dial": "+972", "flag": "🇮🇱"},
    {"code": "SA", "name": "Saudi Arabia", "dial": "+966", "flag": "🇸🇦"},
    {"code": "QA", "name": "Qatar", "dial": "+974", "flag": "🇶🇦"},
    {"code": "OM", "name": "Oman", "dial": "+968", "flag": "🇴🇲"},
    {"code": "KW", "name": "Kuwait", "dial": "+965", "flag": "🇰🇼"},
    {"code": "JO", "name": "Jordan", "dial": "+962", "flag": "🇯🇴"},
    {"code": "IR", "name": "Iran", "dial": "+98", "flag": "🇮🇷"},
    {"code": "IQ", "name": "Iraq", "dial": "+964", "flag": "🇮🇶"},
    {"code": "PK", "name": "Pakistan", "dial": "+92", "flag": "🇵🇰"},
    {"code": "BD", "name": "Bangladesh", "dial": "+880", "flag": "🇧🇩"},
    {"code": "LK", "name": "Sri Lanka", "dial": "+94", "flag": "🇱🇰"},
    {"code": "NP", "name": "Nepal", "dial": "+977", "flag": "🇳🇵"},
    {"code": "MV", "name": "Maldives", "dial": "+960", "flag": "🇲🇻"},
    {"code": "TH", "name": "Thailand", "dial": "+66", "flag": "🇹🇭"},
    {"code": "VN", "name": "Vietnam", "dial": "+84", "flag": "🇻🇳"},
    {"code": "ID", "name": "Indonesia", "dial": "+62", "flag": "🇮🇩"},
    {"code": "PH", "name": "Philippines", "dial": "+63", "flag": "🇵🇭"},
    {"code": "MY", "name": "Malaysia", "dial": "+60", "flag": "🇲🇾"},
    {"code": "TW", "name": "Taiwan", "dial": "+886", "flag": "🇹🇼"},
    {"code": "HK", "name": "Hong Kong", "dial": "+852", "flag": "🇭🇰"},
    {"code": "UA", "name": "Ukraine", "dial": "+380", "flag": "🇺🇦"},
    {"code": "TR", "name": "Turkey", "dial": "+90", "flag": "🇹🇷"},
    {"code": "UG", "name": "Uganda", "dial": "+256", "flag": "🇺🇬"},
    {"code": "YE", "name": "Yemen", "dial": "+967", "flag": "🇾🇪"},
    {"code": "ZW", "name": "Zimbabwe", "dial": "+263", "flag": "🇿🇼"},
]


class WelcomeDialog:
    """Universal welcome dialog for SDK-powered applications.

    Collects customer information, performs OTP verification,
    and starts a trial via the Websmith API.
    """

    def __init__(self, engine, support_email: str = ""):
        self.engine = engine
        self.support_email = support_email
        self.client: Optional[ApiClient] = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})

        self.result = False
        self._otp_sent = False
        self._otp_verified = False
        self._customer_data = {{}}

        # Selected country
        self.selected_country = COUNTRY_CODES[0]  # default India

        self._build_ui()

    def _build_ui(self):
        """Build the welcome dialog UI using tkinter."""
        self.root = tk.Tk()
        self.root.title("Welcome to ZEM MAC OS")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8f9fa")

        # Center on screen
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{{x}}+{{y}}")

        # Header
        header = tk.Frame(self.root, bg="#6366f1", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Welcome to ZEM MAC OS",
                 fg="white", bg="#6366f1",
                 font=("Helvetica", 18, "bold")).pack(expand=True)

        # Form container
        form = tk.Frame(self.root, bg="#f8f9fa", padx=30, pady=20)
        form.pack(fill=tk.BOTH, expand=True)

        # Customer Information label
        tk.Label(form, text="Customer Information",
                 font=("Helvetica", 12, "bold"),
                 bg="#f8f9fa", fg="#333").pack(anchor=tk.W, pady=(0, 10))

        # Full Name
        tk.Label(form, text="Full Name *", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.name_entry = tk.Entry(form, font=("Helvetica", 11),
                                    relief=tk.SOLID, bd=1)
        self.name_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        # Email
        tk.Label(form, text="Email Address *", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.email_entry = tk.Entry(form, font=("Helvetica", 11),
                                     relief=tk.SOLID, bd=1)
        self.email_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        # Company
        tk.Label(form, text="Company", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)
        self.company_entry = tk.Entry(form, font=("Helvetica", 11),
                                       relief=tk.SOLID, bd=1)
        self.company_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)

        # Country Code + Mobile
        country_frame = tk.Frame(form, bg="#f8f9fa")
        country_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(country_frame, text="Mobile Number", font=("Helvetica", 10),
                 bg="#f8f9fa", fg="#555").pack(anchor=tk.W)

        mobile_row = tk.Frame(country_frame, bg="#f8f9fa")
        mobile_row.pack(fill=tk.X, pady=(2, 0))

        # Country code button
        self.country_btn = tk.Button(
            mobile_row,
            text=f"{{self.selected_country['flag']}} {{self.selected_country['dial']}}",
            font=("Helvetica", 11),
            relief=tk.SOLID, bd=1,
            bg="white", fg="#333",
            command=self._open_country_selector
        )
        self.country_btn.pack(side=tk.LEFT, ipady=4)

        # Mobile entry
        self.mobile_entry = tk.Entry(mobile_row, font=("Helvetica", 11),
                                      relief=tk.SOLID, bd=1)
        self.mobile_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                                padx=(5, 0), ipady=4)

        # Separator
        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        # OTP Section
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

        # OTP Entry (hidden initially)
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

        # Start Trial button
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

        # Status message
        self.status_label = tk.Label(
            form, text="",
            font=("Helvetica", 9),
            bg="#f8f9fa", fg="#333",
            wraplength=400
        )
        self.status_label.pack()

        # Support link
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
        """Open a searchable country selector popup."""
        top = tk.Toplevel(self.root)
        top.title("Select Country")
        top.geometry("320x400")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        # Search entry
        search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=search_var,
                                 font=("Helvetica", 11),
                                 relief=tk.SOLID, bd=1)
        search_entry.pack(fill=tk.X, padx=10, pady=(10, 5), ipady=3)
        search_entry.focus_set()

        # Listbox with scrollbar
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
                                   f"{{c['flag']}} {{c['name']}} ({{c['dial']}})")

        populate_list()

        def on_search(*args):
            populate_list(search_var.get())

        search_var.trace("w", on_search)

        def on_select(event):
            selection = listbox.curselection()
            if not selection:
                return
            raw = listbox.get(selection[0])
            # Extract the dial code from the listbox entry
            for c in COUNTRY_CODES:
                if f"{{c['flag']}} {{c['name']}} ({{c['dial']}})" == raw:
                    self.selected_country = c
                    self.country_btn.config(
                        text=f"{{c['flag']}} {{c['dial']}}"
                    )
                    top.destroy()
                    break

        listbox.bind("<<ListboxSelect>>", on_select)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _send_otp(self):
        """Send OTP to the entered email via the internal API."""
        email = self.email_entry.get().strip()
        if not email:
            self.otp_status.config(text="Please enter an email first", fg="#ef4444")
            return

        self.otp_btn.config(state=tk.DISABLED, text="Sending...")
        self.otp_status.config(text="", fg="#888")

        def do_send():
            try:
                config = self.config
                api_config = config.get('api', {{}})
                base_url = api_config.get('url', '').rstrip('/')

                import requests
                resp = requests.post(
                    f"{{base_url}}/internal/backend/api/auth/forgot-password",
                    json={{"email": email}},
                    timeout=15
                )
                data = resp.json() if resp.ok else {{}}

                self.root.after(0, lambda: self._on_otp_sent(
                    data.get('success', False),
                    data.get('message', '')
                ))
            except Exception as e:
                self.root.after(0, lambda: self._on_otp_sent(
                    False, f"Connection error: {{str(e)}}"
                ))

        threading.Thread(target=do_send, daemon=True).start()

    def _on_otp_sent(self, success: bool, message: str):
        """Handle OTP send response."""
        if success:
            self._otp_sent = True
            self.otp_status.config(text="OTP sent! Check your email.", fg="#10b981")
            self.otp_btn.config(text="Resend OTP", state=tk.NORMAL)
            # Show OTP entry
            self.otp_entry_frame.pack(fill=tk.X, pady=(8, 0))
        else:
            self.otp_status.config(
                text=message or "Failed to send OTP. Try again.",
                fg="#ef4444"
            )
            self.otp_btn.config(text="Send OTP", state=tk.NORMAL)

    def _verify_otp(self):
        """Verify the entered OTP."""
        otp = self.otp_entry.get().strip()
        if not otp:
            self.otp_status.config(text="Please enter the OTP", fg="#ef4444")
            return

        email = self.email_entry.get().strip()
        self.verify_btn.config(state=tk.DISABLED, text="Verifying...")

        def do_verify():
            try:
                config = self.config
                api_config = config.get('api', {{}})
                base_url = api_config.get('url', '').rstrip('/')

                import requests
                resp = requests.post(
                    f"{{base_url}}/internal/backend/api/auth/verify-otp",
                    json={{"email": email, "otp": otp}},
                    timeout=15
                )
                data = resp.json() if resp.ok else {{}}
                success = data.get('success', False) if resp.ok else False

                self.root.after(0, lambda: self._on_otp_verified(success, data.get('message', '')))
            except Exception as e:
                self.root.after(0, lambda: self._on_otp_verified(
                    False, f"Verification error: {{str(e)}}"
                ))

        threading.Thread(target=do_verify, daemon=True).start()

    def _on_otp_verified(self, success: bool, message: str):
        """Handle OTP verification response."""
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
        """Start trial via the API with collected customer data."""
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
                    self._customer_data = {{
                        "name": name,
                        "email": email,
                        "company": self.company_entry.get().strip(),
                        "country_code": self.selected_country['dial'],
                        "mobile": self.mobile_entry.get().strip(),
                        "hardware_id": hardware_id,
                    }}
                    self.result = True
                    self.root.after(0, self.root.destroy)
                else:
                    err = result.get('error', {{}})
                    msg = err.get('message', 'Failed to start trial') if isinstance(err, dict) else str(err)
                    self.root.after(0, lambda: self._on_trial_failed(msg))
            except Exception as e:
                self.root.after(0, lambda: self._on_trial_failed(str(e)))

        threading.Thread(target=do_trial, daemon=True).start()

    def _on_trial_failed(self, message: str):
        """Handle trial start failure."""
        self.status_label.config(text=f"Trial failed: {{message}}", fg="#ef4444")
        self.start_btn.config(text="Start Trial", state=tk.NORMAL)

    def run(self):
        """Run the dialog and return True if trial was started."""
        self.root.mainloop()
        return self.result


def show_welcome_dialog(engine) -> bool:
    """Show the welcome dialog and return True if onboarding completed."""
    dialog = WelcomeDialog(engine)
    return dialog.run()
