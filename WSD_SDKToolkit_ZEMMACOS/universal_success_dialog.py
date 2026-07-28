"""Universal Success Dialog — success info with single Restart Now button"""
import subprocess
import sys
import tkinter as tk
from typing import Any, Optional

from .license_engine import LicenseEngine, LicenseStatus
from .live_log import LiveLog


class SuccessDialog:
    def __init__(self, parent: tk.Toplevel, status: LicenseStatus,
                 product_name: str, operation: str = "activation",
                 engine: Optional[LicenseEngine] = None):
        self._parent = parent
        self._status = status
        self._product_name = product_name
        self._operation = operation
        self._engine = engine
        self._root: Optional[tk.Toplevel] = None

        # Branding / color constants
        self._success_color = "#16a34a"
        self._bg = "#f0f2f5"
        self._card_bg = "#ffffff"
        self._text_primary = "#1a1a2e"
        self._text_secondary = "#6b7280"
        self._border = "#d1d5db"

    def show(self) -> None:
        self._root = tk.Toplevel(self._parent)
        self._root.title("Operation Successful")
        self._root.geometry("520x520")
        self._root.resizable(False, False)
        self._root.configure(bg=self._bg)
        self._root.transient(self._parent)
        self._root.grab_set()
        self._root.protocol("WM_DELETE_WINDOW", self._on_restart)
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

        header = tk.Frame(root, bg=self._success_color, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="\u2714 Operation Successful",
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._success_color).pack(expand=True)

        main = tk.Frame(root, bg=self._card_bg, padx=28, pady=20)
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

        for label, value in fields:
            row = tk.Frame(main, bg=self._card_bg)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label + ":", font=("Segoe UI", 10),
                     fg=self._text_secondary, bg=self._card_bg,
                     width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                     fg=self._text_primary, bg=self._card_bg,
                     anchor="w").pack(side="left", fill="x", expand=True)

        sep = tk.Frame(main, bg=self._border, height=1)
        sep.pack(fill="x", pady=16)

        msg = tk.Label(main,
                       text="Your licence has been updated successfully.\n"
                            "Please restart the application to apply the latest licence information.",
                       font=("Segoe UI", 11), fg=self._text_secondary, bg=self._card_bg,
                       justify="center", wraplength=460)
        msg.pack(pady=(0, 20))

        btn = tk.Button(main, text="Restart Now",
                        font=("Segoe UI", 13, "bold"),
                        bg="#6366f1", fg="white", relief="flat",
                        command=self._on_restart, cursor="hand2",
                        padx=28, pady=10)
        btn.pack()

    def _save_runtime_state(self) -> None:
        if not self._engine:
            return
        try:
            status = self._engine.get_status()
            if status:
                self._engine._cache.set_license_status(status.to_dict())
                key = self._engine.get_license_key()
                if key:
                    self._engine._cache.save_license_key(key)
                self._engine._cache.set_onboarding_complete()
                LiveLog.log("Runtime state saved", f"Status: {status.status}")
        except Exception as e:
            LiveLog.log("Runtime state save failed", str(e))

    def _flush_cache(self) -> None:
        if not self._engine:
            return
        try:
            self._engine._cache._save_cache()
            LiveLog.log("Cache flushed to disk", "Pre-restart cache write complete")
        except Exception as e:
            LiveLog.log("Cache flush failed", str(e))

    def _close_all_windows(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        if self._parent and self._parent != self._root:
            try:
                self._parent.destroy()
            except Exception:
                pass
        try:
            if tk._default_root:
                for w in tk._default_root.winfo_children():
                    try:
                        w.destroy()
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if tk._default_root:
                tk._default_root.destroy()
        except Exception:
            pass

    def _on_restart(self):
        LiveLog.log("Restart requested", "User clicked Restart Now")
        self._save_runtime_state()
        self._flush_cache()
        self._close_all_windows()
        cmd = [sys.executable] + sys.argv
        LiveLog.log("Restart command", f"Executing: {' '.join(cmd[:3])}...")
        try:
            subprocess.Popen(cmd)
            LiveLog.log("Restart command launched", "New process started")
        except Exception as e:
            LiveLog.log("Restart launch failed", str(e))
        LiveLog.log("Current process closing", "Exiting")
        sys.exit(0)
