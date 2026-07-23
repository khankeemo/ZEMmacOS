f'''"""Universal Email Dialog - reusable email form for all request types"""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional

from .client import ApiClient
from .hardware import HardwareDetector
from .cache import CacheManager

SDK_VERSION = "{context.kitVersion}"
RUNTIME_TYPE = "{context.runtime}"
SUPPORT_EMAIL = "support@websmithdigital.com"

REQUEST_TYPES = [
    "BUY",
    "RENEW",
    "SUPPORT",
    "ACTIVATION",
    "DEVICE_REPLACEMENT",
    "HARDWARE",
    "GENERAL",
]


class UniversalEmailDialog:
    def __init__(
        self,
        config: Dict[str, Any],
        client: ApiClient,
        hardware: HardwareDetector,
        cache: CacheManager,
    ):
        self.config = config
        self.client = client
        self.hardware = hardware
        self.cache = cache
        self._result: Optional[Dict[str, Any]] = None
        self._root: Optional[tk.Toplevel] = None

        branding = config.get("branding", {{}})
        self._primary = branding.get("primary_color", "#6366f1")
        self._bg = "#f0f2f5"
        self._card_bg = "#ffffff"
        self._text_primary = "#1a1a2e"
        self._text_secondary = "#6b7280"
        self._border = "#d1d5db"

    def show(
        self,
        request_type: str,
        subject: str = "",
        customer_name: str = "",
        customer_email: str = "",
        license_key: str = "",
        plan_name: str = "",
        hardware_id: str = "",
        message_text: str = "",
    ) -> Dict[str, Any]:
        product_name = self.config.get("product", {{}}).get("name", "")

        cached = self.cache.get_license_status()
        if not customer_name:
            customer_name = cached.get("customer_name", "") if cached else ""
        if not customer_email:
            customer_email = cached.get("customer_email", "") if cached else ""
        if not hardware_id:
            hardware_id = self.hardware.get_fingerprint()

        self._result = None
        self._root = tk.Toplevel()
        self._root.title(f"{{request_type.replace('_', ' ')}} Request")
        self._root.geometry("520x580")
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient()
        self._root.grab_set()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui(request_type, product_name, customer_name, customer_email,
                       license_key, plan_name, hardware_id, message_text)
        self._center_window()
        self._root.wait_window()
        return self._result or {{"sent": False, "error": "Dialog closed"}}

    def _center_window(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{{w}}x{{h}}+{{x}}+{{y}}")

    def _build_ui(self, request_type, product_name, customer_name, customer_email,
                  license_key, plan_name, hardware_id, message_text):
        root = self._root
        padding = {{"padx": 20, "pady": 4}}

        header = tk.Label(root, text=f"Universal Email Form",
                          font=("Segoe UI", 18, "bold"),
                          bg=self._bg, fg=self._text_primary)
        header.pack(pady=(24, 2))
        sub = tk.Label(root, text=f"Request: {{request_type.replace('_', ' ')}}",
                       font=("Segoe UI", 10), bg=self._bg, fg=self._text_secondary)
        sub.pack(pady=(0, 16))
        if product_name:
            prod_lbl = tk.Label(root, text=f"Product: {{product_name}}",
                                font=("Segoe UI", 9), bg=self._bg, fg=self._text_secondary)
            prod_lbl.pack(pady=(0, 8))

        frame = tk.Frame(root, bg=self._card_bg, bd=1, relief="solid",
                         highlightbackground=self._border)
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        tk.Label(frame, text="Your Name *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
        self._name_var = tk.StringVar(value=customer_name)
        self._name_entry = tk.Entry(frame, textvariable=self._name_var,
                                     font=("Segoe UI", 11), relief="solid", bd=1)
        self._name_entry.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(frame, text="Your Email *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
        self._email_var = tk.StringVar(value=customer_email)
        self._email_entry = tk.Entry(frame, textvariable=self._email_var,
                                      font=("Segoe UI", 11), relief="solid", bd=1)
        self._email_entry.pack(fill="x", padx=20, pady=(0, 8))

        if license_key:
            tk.Label(frame, text="License Key", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
            lk_lbl = tk.Label(frame, text=license_key, font=("Courier", 10),
                              bg=self._card_bg, fg=self._text_secondary)
            lk_lbl.pack(anchor="w", padx=20, pady=(0, 8))

        if plan_name:
            tk.Label(frame, text="Plan", font=("Segoe UI", 10, "bold"),
                     bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
            plan_lbl = tk.Label(frame, text=plan_name, font=("Segoe UI", 10),
                                bg=self._card_bg, fg=self._text_secondary)
            plan_lbl.pack(anchor="w", padx=20, pady=(0, 8))

        tk.Label(frame, text="Subject", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
        self._subject_var = tk.StringVar(
            value=f"{{request_type.replace('_', ' ')}} Request")
        self._subject_entry = tk.Entry(frame, textvariable=self._subject_var,
                                        font=("Segoe UI", 11), relief="solid", bd=1)
        self._subject_entry.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(frame, text="Message *", font=("Segoe UI", 10, "bold"),
                 bg=self._card_bg, fg=self._text_primary).pack(anchor="w", **padding)
        self._msg_text = tk.Text(frame, font=("Segoe UI", 10), height=5,
                                  wrap="word", relief="solid", bd=1)
        self._msg_text.pack(fill="x", padx=20, pady=(0, 12))
        if message_text:
            self._msg_text.insert("1.0", message_text)

        self._status_label = tk.Label(frame, text="", font=("Segoe UI", 9),
                                       bg=self._card_bg, fg="#16a34a")
        self._status_label.pack(padx=20, pady=(0, 4))

        self._send_btn = tk.Button(frame, text="Send Request",
                                    font=("Segoe UI", 11, "bold"),
                                    bg=self._primary, fg="white", relief="flat",
                                    command=self._on_send, cursor="hand2")
        self._send_btn.pack(fill="x", padx=20, pady=(0, 12))
        self._send_btn.bind("<Enter>", lambda e: self._send_btn.config(bg="#4f46e5"))
        self._send_btn.bind("<Leave>", lambda e: self._send_btn.config(bg=self._primary))

        self._request_type = request_type
        self._product_name = product_name
        self._license_key = license_key
        self._plan_name = plan_name
        self._hardware_id = hardware_id

    def _on_close(self):
        self._result = {{"sent": False, "error": "Dialog closed"}}
        try:
            self._root.destroy()
        except Exception:
            pass

    def _on_send(self):
        name = self._name_var.get().strip()
        email = self._email_var.get().strip()
        subject = self._subject_var.get().strip()
        msg = self._msg_text.get("1.0", "end").strip()

        if not name or not email:
            messagebox.showwarning("Validation Error",
                                    "Name and email are required.", parent=self._root)
            return
        if not msg:
            messagebox.showwarning("Validation Error",
                                    "Message is required.", parent=self._root)
            return

        self._send_btn.config(state="disabled", text="Sending...")
        self._status_label.config(text="Submitting your request...", fg=self._text_secondary)
        self._root.update()

        try:
            result = self.client.send_request(
                request_type=self._request_type,
                customer_name=name,
                customer_email=email,
                subject=subject,
                message=msg,
                license_key=self._license_key,
                hardware_id=self._hardware_id,
                plan_name=self._plan_name,
                product_name=self._product_name,
            )
            if result.get("success"):
                ref = result.get("data", {{}}).get("request_id", "")
                messagebox.showinfo(
                    "Request Submitted",
                    f"Your request has been submitted successfully!\n\n"
                    f"Reference: {{ref}}\n"
                    f"We will contact you at {{email}} shortly.",
                    parent=self._root,
                )
                self._result = {{"sent": True, "request_id": ref}}
                self._root.destroy()
            else:
                err = result.get("error", {{}}).get("message", "Unknown error")
                self._status_label.config(text=f"Failed: {{err}}", fg="#dc2626")
                self._send_btn.config(state="normal", text="Send Request")
        except Exception as e:
            self._status_label.config(
                text=f"Error: {{str(e)}}. Email {{SUPPORT_EMAIL}} directly.",
                fg="#dc2626",
            )
            self._send_btn.config(state="normal", text="Send Request")
