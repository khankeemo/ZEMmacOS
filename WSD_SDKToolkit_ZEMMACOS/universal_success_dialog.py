"""Universal Success Dialog — shown after every successful licensing operation"""
import tkinter as tk
from typing import Any, Callable, Optional

from .license_engine import LicenseStatus


class SuccessDialog:
    def __init__(self, parent: tk.Toplevel, status: LicenseStatus,
                 product_name: str, operation: str = "activation",
                 on_restart: Optional[Callable[[], None]] = None,
                 on_restart_later: Optional[Callable[[], None]] = None):
        self._parent = parent
        self._status = status
        self._product_name = product_name
        self._operation = operation
        self._on_restart = on_restart
        self._on_restart_later = on_restart_later
        self._root: Optional[tk.Toplevel] = None

    def show(self) -> None:
        self._root = tk.Toplevel(self._parent)
        self._root.title("Operation Successful")
        self._root.geometry("520x480")
        self._root.resizable(False, False)
        self._root.configure(bg="#f0f2f5")
        self._root.transient(self._parent)
        self._root.grab_set()
        self._build_ui()
        self._center_window()
        self._root.wait_window()

    def _center_window(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        root = self._root
        status = self._status

        header = tk.Frame(root, bg="#16a34a", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="\u2714 Operation Successful",
                 font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#16a34a").pack(expand=True)

        main = tk.Frame(root, bg="#ffffff", padx=24, pady=16)
        main.pack(fill="both", expand=True)

        fields = [
            ("Customer Name", status.customer_name or "-"),
            ("Customer Email", status.customer_email or "-"),
            ("Product", self._product_name),
            ("Plan", status.plan or "-"),
            ("License Status", "Active" if status.valid else status.status.upper()),
        ]
        if status.expiry_date:
            fields.append(("Expiry Date", status.expiry_date))
        if status.days_left is not None:
            fields.append(("Days Remaining", str(status.days_left)))
        if status.hardware_id:
            hw_short = status.hardware_id[:16] + "..."
            fields.append(("Hardware ID", hw_short))

        for i, (label, value) in enumerate(fields):
            row = tk.Frame(main, bg="#ffffff")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", font=("Segoe UI", 10, "bold"),
                     fg="#374151", bg="#ffffff", width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10),
                     fg="#1a1a2e", bg="#ffffff", anchor="w").pack(side="left", fill="x", expand=True)

        sep = tk.Frame(main, bg="#d1d5db", height=1)
        sep.pack(fill="x", pady=12)

        msg = tk.Label(main,
                       text="Your product has been updated successfully.\nPlease restart the application to load the latest license information.",
                       font=("Segoe UI", 10), fg="#6b7280", bg="#ffffff",
                       justify="center", wraplength=460)
        msg.pack(pady=(0, 12))

        btn_frame = tk.Frame(main, bg="#ffffff")
        btn_frame.pack(fill="x")

        restart_btn = tk.Button(btn_frame, text="Restart Now",
                                font=("Segoe UI", 12, "bold"),
                                bg="#6366f1", fg="white", relief="flat",
                                command=self._on_restart_now, cursor="hand2",
                                padx=20, pady=8)
        restart_btn.pack(side="left", expand=True, padx=(0, 6))

        later_btn = tk.Button(btn_frame, text="Restart Later",
                              font=("Segoe UI", 12),
                              bg="#e5e7eb", fg="#374151", relief="flat",
                              command=self._on_restart_later_click, cursor="hand2",
                              padx=20, pady=8)
        later_btn.pack(side="right", expand=True, padx=(6, 0))

    def _on_restart_now(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        if self._on_restart:
            self._on_restart()

    def _on_restart_later_click(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        if self._on_restart_later:
            self._on_restart_later()
