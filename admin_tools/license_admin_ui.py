# admin_tools/license_admin_ui.py — API-only ZEM License Admin Panel

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from admin_api_client import AdminAPIClient, resolve_admin_key, set_api_log_callback, load_api_config
from backend_manager import BackendManager
from license_generator import LicenseGenerator

ADMIN_LOG_FILE = "license_admin.log"
REFRESH_MS = 15000


class LicenseAdminUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ZEMmacOS License Admin — API Dashboard")
        self.root.geometry("1100x900")
        self.root.minsize(950, 750)

        self.admin_log_path = os.path.join(SCRIPT_DIR, ADMIN_LOG_FILE)
        self.api: AdminAPIClient = None
        self.generator: LicenseGenerator = None
        self.api_online = False
        self.db_status = "unknown"
        self._refresh_job = None
        self._last_license_result = None

        cfg = load_api_config()
        self.api_url = cfg.get("license_api_url", "http://localhost:8000")
        self.backend_manager = BackendManager(self.api_url, log_callback=self._live_log)

        self._build_ui()
        set_api_log_callback(self._live_log)
        self._live_log("Admin panel initialized", "info")
        self._ensure_backend_running()
        self._startup_sequence()
        self.backend_manager.start_monitor()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Connecting to API...")
        ttk.Label(top, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="↻ Auto Reconnect", command=self._startup_sequence).pack(side=tk.RIGHT, padx=4)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.tab_dashboard = ttk.Frame(self.notebook, padding=8)
        self.tab_generate = ttk.Frame(self.notebook, padding=8)
        self.tab_validate = ttk.Frame(self.notebook, padding=8)
        self.tab_search = ttk.Frame(self.notebook, padding=8)
        self.tab_hardware = ttk.Frame(self.notebook, padding=8)
        self.tab_trials = ttk.Frame(self.notebook, padding=8)
        self.tab_activations = ttk.Frame(self.notebook, padding=8)
        self.tab_monitor = ttk.Frame(self.notebook, padding=8)
        self.tab_api = ttk.Frame(self.notebook, padding=8)

        tabs = [
            (self.tab_dashboard, "📊 Dashboard"),
            (self.tab_generate, "🔑 Generate License"),
            (self.tab_validate, "✓ Validate License"),
            (self.tab_search, "🔍 Search Customer"),
            (self.tab_hardware, "💻 Hardware Manager"),
            (self.tab_trials, "🧪 Trial Manager"),
            (self.tab_activations, "📋 Activation Logs"),
            (self.tab_monitor, "📡 Live Monitoring"),
            (self.tab_api, "🌐 API Status"),
        ]
        for frame, title in tabs:
            self.notebook.add(frame, text=title)

        self._build_dashboard_tab()
        self._build_generate_tab()
        self._build_validate_tab()
        self._build_search_tab()
        self._build_hardware_tab()
        self._build_trials_tab()
        self._build_activations_tab()
        self._build_monitor_tab()
        self._build_api_tab()

    def _card_row(self, parent, labels):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=6)
        widgets = {}
        for i, (key, title) in enumerate(labels):
            box = ttk.LabelFrame(frame, text=title, padding=8)
            box.grid(row=0, column=i, padx=6, sticky="nsew")
            frame.columnconfigure(i, weight=1)
            val = ttk.Label(box, text="—", font=("Segoe UI", 14, "bold"))
            val.pack()
            widgets[key] = val
        return widgets

    def _build_dashboard_tab(self):
        self.dash_cards = self._card_row(
            self.tab_dashboard,
            [
                ("total", "Total Licenses"),
                ("active", "Active"),
                ("revoked", "Revoked"),
                ("expired", "Expired"),
            ],
        )
        self.dash_cards2 = self._card_row(
            self.tab_dashboard,
            [
                ("trials", "Active Trials"),
                ("devices", "Online Devices (24h)"),
                ("latency", "API Latency"),
                ("db", "Database"),
            ],
        )
        btn_row = ttk.Frame(self.tab_dashboard)
        btn_row.pack(fill=tk.X, pady=8)
        ttk.Button(btn_row, text="↻ Refresh Now", command=self._refresh_dashboard).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Generate Test License", command=self._generate_test_license).pack(side=tk.LEFT, padx=4)
        self.dash_log = scrolledtext.ScrolledText(self.tab_dashboard, height=12, font=("Consolas", 9))
        self.dash_log.pack(fill=tk.BOTH, expand=True, pady=6)

    def _build_generate_tab(self):
        f = ttk.LabelFrame(self.tab_generate, text="Customer", padding=10)
        f.pack(fill=tk.X)
        self.gen_name = self._labeled_entry(f, "Full Name:", 0)
        self.gen_email = self._labeled_entry(f, "Email:", 1)
        self.gen_plan = self._labeled_combo(f, "Plan:", 2, ["Standard", "Professional", "Enterprise"])
        self.gen_days = self._labeled_entry(f, "Expiry Days:", 3, "365")
        self.gen_devices = self._labeled_entry(f, "Max Devices:", 4, "1")
        self.gen_notes = self._labeled_entry(f, "Notes:", 5)
        self.gen_key = self._labeled_entry(f, "License Key (optional):", 6, "")

        btns = ttk.Frame(self.tab_generate)
        btns.pack(fill=tk.X, pady=8)
        self.btn_gen = ttk.Button(btns, text="Create via API", command=self._generate_license)
        self.btn_gen.pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Generate Test License", command=self._generate_test_license).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Save Receipt", command=self._save_last_receipt).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Copy License Key", command=self._copy_license_key).pack(side=tk.LEFT, padx=4)

        self.gen_output = scrolledtext.ScrolledText(self.tab_generate, height=18, font=("Consolas", 9))
        self.gen_output.pack(fill=tk.BOTH, expand=True)
        self.api_sync_label = ttk.Label(self.tab_generate, text="API: checking...", foreground="gray")
        self.api_sync_label.pack(anchor=tk.W)

    def _build_validate_tab(self):
        row = ttk.Frame(self.tab_validate)
        row.pack(fill=tk.X, pady=6)
        ttk.Label(row, text="License Key:").pack(side=tk.LEFT)
        self.val_key = ttk.Entry(row, width=50)
        self.val_key.pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="Validate via API", command=self._validate_license).pack(side=tk.LEFT)
        self.val_output = scrolledtext.ScrolledText(self.tab_validate, height=24, font=("Consolas", 9))
        self.val_output.pack(fill=tk.BOTH, expand=True)

    def _build_search_tab(self):
        row = ttk.Frame(self.tab_search)
        row.pack(fill=tk.X, pady=6)
        ttk.Label(row, text="Email:").pack(side=tk.LEFT)
        self.search_email = ttk.Entry(row, width=40)
        self.search_email.pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="Search", command=self._search_customer).pack(side=tk.LEFT)
        self.search_output = scrolledtext.ScrolledText(self.tab_search, height=24, font=("Consolas", 9))
        self.search_output.pack(fill=tk.BOTH, expand=True)

    def _build_hardware_tab(self):
        row = ttk.Frame(self.tab_hardware)
        row.pack(fill=tk.X, pady=6)
        ttk.Label(row, text="License Key:").pack(side=tk.LEFT)
        self.hw_key = ttk.Entry(row, width=36)
        self.hw_key.pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Load Activations", command=self._load_hardware).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Reset All Devices", command=self._reset_all_hardware).pack(side=tk.LEFT, padx=4)
        self.hw_output = scrolledtext.ScrolledText(self.tab_hardware, height=22, font=("Consolas", 9))
        self.hw_output.pack(fill=tk.BOTH, expand=True)

    def _build_trials_tab(self):
        ttk.Button(self.tab_trials, text="↻ Refresh Trials", command=self._load_trials).pack(anchor=tk.W, pady=4)
        self.trials_output = scrolledtext.ScrolledText(self.tab_trials, height=26, font=("Consolas", 9))
        self.trials_output.pack(fill=tk.BOTH, expand=True)

    def _build_activations_tab(self):
        ttk.Button(self.tab_activations, text="↻ Refresh Logs", command=self._load_activations).pack(anchor=tk.W, pady=4)
        self.act_output = scrolledtext.ScrolledText(self.tab_activations, height=26, font=("Consolas", 9))
        self.act_output.pack(fill=tk.BOTH, expand=True)

    def _build_monitor_tab(self):
        self.live_console = scrolledtext.ScrolledText(self.tab_monitor, height=30, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.live_console.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.tab_monitor, text="Clear", command=lambda: self.live_console.delete(1.0, tk.END)).pack(anchor=tk.E, pady=4)

    def _build_api_tab(self):
        self.api_output = scrolledtext.ScrolledText(self.tab_api, height=28, font=("Consolas", 9))
        self.api_output.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.tab_api, text="Run Full Diagnostics", command=self._run_api_diagnostics).pack(anchor=tk.W, pady=4)

    def _labeled_entry(self, parent, label, row, default=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        e = ttk.Entry(parent, width=45)
        e.grid(row=row, column=1, sticky=tk.W, pady=3)
        if default:
            e.insert(0, default)
        return e

    def _labeled_combo(self, parent, label, row, values):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
        c = ttk.Combobox(parent, values=values, width=42)
        c.grid(row=row, column=1, sticky=tk.W, pady=3)
        c.set(values[0])
        return c

    # ------------------------------------------------------------------ Logging
    def _live_log(self, msg: str, level: str = "info"):
        ts = __import__("datetime").datetime.now().strftime("%H:%M:%S")
        colors = {"info": "#51cf66", "error": "#ff6b6b", "warning": "#ffd43b", "debug": "#888", "success": "#00ff88"}
        line = f"[{ts}] [{level.upper()}] {msg}\n"
        for widget in (getattr(self, "live_console", None), getattr(self, "dash_log", None)):
            if widget:
                try:
                    widget.insert(tk.END, line)
                    widget.see(tk.END)
                except tk.TclError:
                    pass
        try:
            with open(self.admin_log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def _set_api_ui_state(self, online: bool):
        state = tk.NORMAL if online else tk.DISABLED
        for btn in (getattr(self, "btn_gen", None),):
            if btn:
                btn.config(state=state)
        color = "green" if online else "orange"
        text = "API: ONLINE" if online else "API: OFFLINE — auto reconnecting..."
        if hasattr(self, "api_sync_label"):
            self.api_sync_label.config(text=text, foreground=color)

    def _ensure_backend_running(self):
        self._live_log("Ensuring local backend is running...", "info")
        if self.backend_manager.ensure_backend_running():
            self._live_log("Local backend is ready.", "success")
        else:
            self._live_log(
                "Local backend could not be started automatically. "
                "The admin UI will continue retrying in the background.",
                "warning",
            )

    # ------------------------------------------------------------------ Startup
    def _startup_sequence(self):
        def work():
            self._live_log("Checking API availability...", "info")
            if self.backend_manager.ensure_backend_running():
                self._live_log("Backend availability confirmed.", "success")
            else:
                self._live_log("Backend auto-start did not complete. Will continue retrying.", "warning")

            key = resolve_admin_key()
            if not key:
                self._live_log("No admin API key — create admin_tools/admin_api.key or set ZEM_ADMIN_API_KEY", "warning")
            self.api = AdminAPIClient(admin_key=key)
            health = self.api.health_check()
            self.root.after(0, lambda: self._apply_health(health))

        threading.Thread(target=work, daemon=True).start()

    def _apply_health(self, health: dict):
        self.api_online = health.get("status") == "ok" or health.get("success")
        self.db_status = health.get("database", "unknown")
        latency = health.get("latency_ms", self.api.last_latency_ms if self.api else 0)

        if self.api_online:
            self.status_var.set(f"API Online • DB: {self.db_status} • {latency}ms")
            self._live_log(f"Backend online — PostgreSQL/SQLite: {self.db_status}", "success")
            self._live_log(f"Tables OK: {health.get('tables_ok')}", "info")
            self.generator = LicenseGenerator(self.api)
            self._set_api_ui_state(True)
            self._refresh_dashboard()
            self._schedule_refresh()
        else:
            err = health.get("error", "Connection refused")
            self.status_var.set("API Offline — auto reconnecting...")
            self._live_log(f"Backend unavailable: {err}", "error")
            self._set_api_ui_state(False)
            self._live_log(
                "License API offline. The system will continue retrying automatically.",
                "warning",
            )

    def _schedule_refresh(self):
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        if self.api_online:
            self._refresh_job = self.root.after(REFRESH_MS, self._auto_refresh)

    def _auto_refresh(self):
        self._refresh_dashboard(quiet=True)
        self._schedule_refresh()

    def _refresh_dashboard(self, quiet=False):
        if not self.api or not self.api_online:
            return

        def work():
            health = self.api.health_check()
            stats = self.api.get_dashboard_stats()
            self.root.after(0, lambda: self._update_dashboard(health, stats, quiet))

        threading.Thread(target=work, daemon=True).start()

    def _update_dashboard(self, health, stats, quiet):
        if not quiet:
            self._live_log("Dashboard refreshed", "debug")
        lat = health.get("latency_ms") or stats.get("latency_ms") or "—"
        self.dash_cards["total"].config(text=str(stats.get("total_licenses", "—")))
        self.dash_cards["active"].config(text=str(stats.get("active_licenses", "—")))
        self.dash_cards["revoked"].config(text=str(stats.get("revoked_licenses", "—")))
        self.dash_cards["expired"].config(text=str(stats.get("expired_licenses", "—")))
        self.dash_cards2["trials"].config(text=str(stats.get("active_trials", "—")))
        self.dash_cards2["devices"].config(text=str(stats.get("online_devices_24h", "—")))
        self.dash_cards2["latency"].config(text=f"{lat} ms")
        self.dash_cards2["db"].config(text=self.db_status)

    # ------------------------------------------------------------------ Actions
    def _generate_license(self):
        if not self.generator or not self.api_online:
            messagebox.showwarning("API Offline", "License API unavailable. Auto reconnect is active.")
            return
        try:
            days = int(self.gen_days.get() or "365")
            devices = int(self.gen_devices.get() or "1")
        except ValueError:
            messagebox.showerror("Error", "Expiry days and devices must be numbers")
            return
        key_opt = self.gen_key.get().strip() or None
        self._live_log("Creating license via API...", "info")

        def work():
            result = self.generator.generate_license(
                self.gen_name.get().strip(),
                self.gen_email.get().strip(),
                expiry_days=days,
                license_key=key_opt,
                plan=self.gen_plan.get(),
                devices=devices,
                notes=self.gen_notes.get().strip(),
            )
            self.root.after(0, lambda: self._show_gen_result(result))

        threading.Thread(target=work, daemon=True).start()

    def _generate_test_license(self):
        if not self.api_online:
            messagebox.showwarning("API Offline", "License API unavailable. Auto reconnect is active.")
            return
        self._live_log("Generating test license via API...", "info")

        def work():
            gen = self.generator or LicenseGenerator(self.api)
            result = gen.generate_test_license()
            self.root.after(0, lambda: self._show_gen_result(result))

        threading.Thread(target=work, daemon=True).start()

    def _show_gen_result(self, result: dict):
        self.gen_output.delete(1.0, tk.END)
        if result.get("error"):
            self.gen_output.insert(tk.END, f"ERROR: {result['error']}\n")
            self._live_log(f"License create failed: {result['error']}", "error")
            return
        self._last_license_result = result
        self._live_log(f"License created: {result.get('license_key')}", "success")
        text = (
            f"SUCCESS — License created on server (PostgreSQL)\n\n"
            f"License Key: {result.get('license_key')}\n"
            f"Customer:    {result['data'].get('customer_name')}\n"
            f"Email:       {result['data'].get('customer_email')}\n"
            f"Expiry:      {result.get('expiry_date')}\n"
            f"Plan:        {result['data'].get('plan')}\n\n"
            f"Customer activates in ZEMmacOS → Settings → Manage License\n"
        )
        self.gen_output.insert(tk.END, text)
        self.gen_output.insert(tk.END, "\n--- JSON Receipt ---\n")
        self.gen_output.insert(tk.END, result.get("content", ""))

    def _save_last_receipt(self):
        if not self._last_license_result:
            messagebox.showinfo("Nothing to save", "Generate a license first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON receipt", "*.json")],
            initialfile=self._last_license_result.get("filename", "license.json"),
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._last_license_result.get("content", ""))
            self._live_log(f"Receipt saved: {path}", "success")

    def _copy_license_key(self):
        if not self._last_license_result:
            messagebox.showinfo("Nothing to copy", "Generate a license first.")
            return
        key = self._last_license_result.get("license_key", "")
        self.root.clipboard_clear()
        self.root.clipboard_append(key)
        messagebox.showinfo("Copied", f"License key copied:\n{key}")

    def _validate_license(self):
        key = self.val_key.get().strip()
        if not key:
            return
        self._live_log(f"Validating license {key[:12]}...", "info")

        def work():
            r = self.api.validate_license(key)
            self.root.after(0, lambda: self._show_validate(r))

        threading.Thread(target=work, daemon=True).start()

    def _show_validate(self, r: dict):
        self.val_output.delete(1.0, tk.END)
        if r.get("valid") or r.get("success"):
            info = r.get("license_info", r)
            lines = [
                "VALID (server)",
                f"Status:     {info.get('status', r.get('status'))}",
                f"Days left:  {info.get('days_left', r.get('days_left'))}",
                f"Plan:       {info.get('plan', r.get('plan'))}",
                f"Max devices:{info.get('max_devices', r.get('max_devices'))}",
                f"Hardware:   {', '.join(info.get('hardware_ids', r.get('hardware_ids', []))) or 'none'}",
            ]
            for act in info.get("activations", info.get("activations_detail", [])):
                lines.append(f"  • {act.get('hardware_id')} last_seen={act.get('last_seen')}")
            self.val_output.insert(tk.END, "\n".join(lines))
            self._live_log("Validation: valid", "success")
        else:
            self.val_output.insert(tk.END, f"INVALID\n{r.get('error', r.get('message'))}")
            self._live_log("Validation: invalid", "warning")

    def _search_customer(self):
        email = self.search_email.get().strip()
        if not email:
            return

        def work():
            r = self.api.search_by_email(email)
            self.root.after(0, lambda: self._fill_text(self.search_output, r))

        threading.Thread(target=work, daemon=True).start()

    def _load_hardware(self):
        key = self.hw_key.get().strip()
        if not key:
            return

        def work():
            r = self.api.search_by_license(key)
            self.root.after(0, lambda: self._show_hardware(r))

        threading.Thread(target=work, daemon=True).start()

    def _show_hardware(self, r: dict):
        self.hw_output.delete(1.0, tk.END)
        if not r.get("success"):
            self.hw_output.insert(tk.END, r.get("error", "Not found"))
            return
        lines = [
            f"License: {r.get('license_key')}",
            f"Customer: {r.get('customer_name')} <{r.get('customer_email')}>",
            f"Status: {r.get('status')}  Plan: {r.get('plan')}  Max: {r.get('max_devices')}",
            "",
            "Activations:",
        ]
        for a in r.get("activations_detail", []):
            lines.append(
                f"  HW: {a.get('hardware_id')}\n"
                f"      Device: {a.get('device_name')}  IP: {a.get('ip_address')}\n"
                f"      Activated: {a.get('activated_at')}  Last seen: {a.get('last_seen')}"
            )
        self.hw_output.insert(tk.END, "\n".join(lines))

    def _reset_all_hardware(self):
        key = self.hw_key.get().strip()
        if not key:
            return
        if not messagebox.askyesno("Confirm", f"Reset ALL devices for {key}?"):
            return

        def work():
            r = self.api.reset_hardware(key)
            self.root.after(0, lambda: self._on_reset_done(r))

        threading.Thread(target=work, daemon=True).start()

    def _on_reset_done(self, r: dict):
        if r.get("success"):
            self._live_log(f"Hardware reset: {r.get('message')}", "success")
            self._load_hardware()
        else:
            messagebox.showerror("Reset failed", r.get("error", "Unknown"))

    def _load_trials(self):
        def work():
            r = self.api.get_trials()
            self.root.after(0, lambda: self._fill_trials(r))

        threading.Thread(target=work, daemon=True).start()

    def _fill_trials(self, r: dict):
        self.trials_output.delete(1.0, tk.END)
        for t in r.get("trials", []):
            self.trials_output.insert(
                tk.END,
                f"{t.get('hardware_id')[:20]}…  {t.get('status')}  {t.get('days_left')}d  exp {t.get('expiry_date')}\n",
            )

    def _load_activations(self):
        def work():
            acts = self.api.get_activation_history()
            logs = self.api.get_logs()
            self.root.after(0, lambda: self._fill_activations(acts, logs))

        threading.Thread(target=work, daemon=True).start()

    def _fill_activations(self, acts, logs):
        self.act_output.delete(1.0, tk.END)
        self.act_output.insert(tk.END, "=== ACTIVATIONS ===\n")
        for a in acts.get("activations", []):
            self.act_output.insert(
                tk.END,
                f"{a.get('license_key')} | {a.get('hardware_id')[:16]} | {a.get('last_seen')}\n",
            )
        self.act_output.insert(tk.END, "\n=== AUDIT LOG ===\n")
        for log in logs.get("logs", [])[:50]:
            self.act_output.insert(
                tk.END,
                f"[{log.get('timestamp')}] {log.get('event_type')}: {log.get('message')}\n",
            )

    def _run_api_diagnostics(self):
        self.api_output.delete(1.0, tk.END)

        def work():
            lines = []
            h = self.api.health_check()
            lines.append("GET /health")
            lines.append(json_dumps(h))
            if self.api.admin_key:
                d = self.api.get_dashboard_stats()
                lines.append("\nGET /admin/dashboard")
                lines.append(json_dumps(d))
            self.root.after(0, lambda: self.api_output.insert(tk.END, "\n".join(lines)))

        threading.Thread(target=work, daemon=True).start()

    def _fill_text(self, widget, data: dict):
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, json_dumps(data))

    def run(self):
        self.root.mainloop()


def json_dumps(obj):
    return json.dumps(obj, indent=2, default=str)


if __name__ == "__main__":
    app = LicenseAdminUI()
    app.run()
