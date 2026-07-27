"""Universal Restart Dialog — save state, close, exit, restart application"""
import os
import subprocess
import sys
import tkinter as tk
from typing import Optional

from .license_engine import LicenseEngine
from .live_log import LiveLog


class RestartDialog:
    def __init__(self, parent: tk.Toplevel, engine: LicenseEngine,
                 product_name: str = "",
                 allow_restart_later: bool = False):
        self._parent = parent
        self._engine = engine
        self._product_name = product_name
        self._allow_restart_later = allow_restart_later
        self._root: Optional[tk.Toplevel] = None

    def show(self) -> None:
        self._root = tk.Toplevel(self._parent)
        self._root.title("Restart Required")
        self._root.geometry("460x280")
        self._root.resizable(False, False)
        self._root.configure(bg="#f0f2f5")
        self._root.transient(self._parent)
        self._root.grab_set()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        LiveLog.log("Restart dialog shown", "Waiting for user action")
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

        header = tk.Frame(root, bg="#6366f1", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Restart Required",
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg="#6366f1").pack(expand=True)

        main = tk.Frame(root, bg="#ffffff", padx=30, pady=20)
        main.pack(fill="both", expand=True)

        msg = tk.Label(main,
                       text="Your product has been updated successfully.\n\nPlease restart the application to load the latest\nlicense information and apply all changes.",
                       font=("Segoe UI", 11), fg="#374151", bg="#ffffff",
                       justify="center")
        msg.pack(expand=True, pady=10)

        btn_frame = tk.Frame(main, bg="#ffffff")
        btn_frame.pack(fill="x", pady=(10, 0))

        restart_btn = tk.Button(btn_frame, text="Restart Now",
                                font=("Segoe UI", 12, "bold"),
                                bg="#6366f1", fg="white", relief="flat",
                                command=self._on_restart, cursor="hand2",
                                padx=24, pady=8)
        restart_btn.pack(side="left", expand=True, padx=(0, 6))

        if self._allow_restart_later:
            later_btn = tk.Button(btn_frame, text="Restart Later",
                                  font=("Segoe UI", 12),
                                  bg="#e5e7eb", fg="#374151", relief="flat",
                                  command=self._on_restart_later, cursor="hand2",
                                  padx=24, pady=8)
            later_btn.pack(side="right", expand=True, padx=(6, 0))

    def _save_runtime_state(self) -> bool:
        try:
            status = self._engine.get_status()
            if status:
                self._engine._cache.set_license_status(status.to_dict())
                LiveLog.log("Runtime state saved", f"Status: {status.status}")
                return True
            LiveLog.log("Runtime state save skipped", "No status available")
            return False
        except Exception as e:
            LiveLog.log("Runtime state save failed", str(e))
            return False

    def _shutdown(self) -> None:
        LiveLog.log("Shutdown sequence started", "Saving state and flushing cache")
        saved = self._save_runtime_state()
        try:
            self._engine._cache._save_cache()
            LiveLog.log("Cache flushed to disk", "Pre-restart cache write complete")
        except Exception as e:
            LiveLog.log("Cache flush failed", str(e))
        LiveLog.log("Shutdown complete", f"State saved: {saved}, exiting process")

    def _on_restart(self):
        LiveLog.log("Restart requested", "User clicked Restart Now")
        self._shutdown()
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        cmd = [sys.executable] + sys.argv
        LiveLog.log("Restart command", f"Executing: {' '.join(cmd[:3])}...")
        try:
            subprocess.Popen(cmd)
            LiveLog.log("Restart command launched", "New process started")
        except Exception as e:
            LiveLog.log("Restart launch failed", str(e))
        LiveLog.log("Current process closing", "Exiting")
        sys.exit(0)

    def _on_restart_later(self):
        LiveLog.log("Restart deferred", "User clicked Restart Later")
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass

    def _on_close(self):
        if self._allow_restart_later:
            self._on_restart_later()
        else:
            self._on_restart()
