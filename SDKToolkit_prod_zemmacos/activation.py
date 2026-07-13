"""Activation Dialog for ZEM MAC OS"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any


class ActivationDialog:
    def __init__(self, engine, license_key: Optional[str] = None):
        self.engine = engine; self.client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self._license_key = license_key
        self.result = None; self.root = None
        self._loading = False; self.hardware_id = ""

    def show(self) -> Optional[Dict[str, Any]]:
        self._build_ui(); self.root.mainloop(); return self.result

    def _build_ui(self):
        branding = self.config.get('branding', {})
        product_name = self.config.get('product', {}).get('name', 'Software')
        primary_color = branding.get('primary_color', '#6366f1'); bg = "#f8f9fa"

        self.root = tk.Tk(); self.root.title(f"Activate {{product_name}}")
        self.root.geometry("500x580"); self.root.resizable(False, False); self.root.configure(bg=bg)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth(); sh = self.root.winfo_screenheight()
        w = self.root.winfo_width(); h = self.root.winfo_height()
        self.root.geometry(f"+{{(sw - w) // 2}}+{{(sh - h) // 2}}")

        header = tk.Frame(self.root, bg=primary_color, height=70)
        header.pack(fill=tk.X); header.pack_propagate(False)
        tk.Label(header, text="Activate License", fg="white", bg=primary_color,
                 font=("Helvetica", 16, "bold")).pack(expand=True)

        form = tk.Frame(self.root, bg=bg, padx=25, pady=15); form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="Product Details", font=("Helvetica", 11, "bold"), bg=bg, fg="#333").pack(anchor=tk.W, pady=(0,5))
        df = tk.Frame(form, bg=bg); df.pack(fill=tk.X, pady=(0,10))
        for label, value in [("Product", product_name), ("Version", self.config.get('product',{}).get('version','1.0.0'))]:
            r = tk.Frame(df, bg=bg); r.pack(fill=tk.X, pady=1)
            tk.Label(r, text=label+":", font=("Helvetica",10,"bold"), bg=bg, fg="#555", width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(r, text=value, font=("Helvetica",10), bg=bg, fg="#333").pack(side=tk.LEFT)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        tk.Label(form, text="Hardware", font=("Helvetica",11,"bold"), bg=bg, fg="#333").pack(anchor=tk.W, pady=(0,5))
        hw = tk.Frame(form, bg=bg); hw.pack(fill=tk.X, pady=(0,10))
        self.hardware_id = self.engine.get_hardware_id()
        tk.Label(hw, text="Hardware ID:", font=("Helvetica",10,"bold"), bg=bg, fg="#555").pack(anchor=tk.W)
        tk.Label(hw, text=self.hardware_id[:48]+"...", font=("Courier",9), bg=bg, fg="#666", wraplength=400, anchor=tk.W).pack(fill=tk.X, pady=(0,5))
        tk.Label(hw, text="Device Name:", font=("Helvetica",10,"bold"), bg=bg, fg="#555").pack(anchor=tk.W)
        self.device_name = tk.Entry(hw, font=("Helvetica",10), relief=tk.SOLID, bd=1)
        self.device_name.pack(fill=tk.X, ipady=3)
        import platform; self.device_name.insert(0, platform.node() or "Unknown")

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        tk.Label(form, text="License Key", font=("Helvetica",11,"bold"), bg=bg, fg="#333").pack(anchor=tk.W, pady=(0,5))
        kf = tk.Frame(form, bg=bg); kf.pack(fill=tk.X, pady=(0,10))
        self.key_entry = tk.Entry(kf, font=("Courier",12), relief=tk.SOLID, bd=1)
        self.key_entry.pack(fill=tk.X, ipady=5)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        tk.Label(form, text="License Info", font=("Helvetica",11,"bold"), bg=bg, fg="#333").pack(anchor=tk.W, pady=(0,5))
        inf = tk.Frame(form, bg=bg); inf.pack(fill=tk.X, pady=(0,10))
        self.plan_label = tk.Label(inf, text="Plan: --", font=("Helvetica",10), bg=bg, fg="#555"); self.plan_label.pack(anchor=tk.W)
        self.expiry_label = tk.Label(inf, text="Expiry: --", font=("Helvetica",10), bg=bg, fg="#555"); self.expiry_label.pack(anchor=tk.W)
        self.days_label = tk.Label(inf, text="Remaining days: --", font=("Helvetica",10), bg=bg, fg="#555"); self.days_label.pack(anchor=tk.W)
        self.dev_label = tk.Label(inf, text="Device usage: --", font=("Helvetica",10), bg=bg, fg="#555"); self.dev_label.pack(anchor=tk.W)

        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        bf = tk.Frame(form, bg=bg); bf.pack(fill=tk.X, pady=(5,0))
        self.act_btn = tk.Button(bf, text="Activate", command=self._activate,
                                  font=("Helvetica",12,"bold"), bg=primary_color, fg="white", relief=tk.FLAT, padx=15, pady=8)
        self.act_btn.pack(fill=tk.X, pady=(0,5))
        br = tk.Frame(bf, bg=bg); br.pack(fill=tk.X)
        self.renew_btn = tk.Button(br, text="Renew", command=self._open_renewal,
                                    font=("Helvetica",10), bg="#e5e7eb", fg="#333", relief=tk.FLAT, padx=10, pady=5)
        self.renew_btn.pack(side=tk.LEFT, padx=(0,5))
        self.repl_btn = tk.Button(br, text="Replace Device", command=self._open_replace,
                                   font=("Helvetica",10), bg="#e5e7eb", fg="#333", relief=tk.FLAT, padx=10, pady=5)
        self.repl_btn.pack(side=tk.LEFT)
        self.status_label = tk.Label(form, text="", font=("Helvetica",9), bg=bg, fg="#333", wraplength=400)
        self.status_label.pack(pady=(5,0))
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        self.key_entry.bind('<KeyRelease>', self._on_key_change)

    def _set_loading(self, v: bool):
        self._loading = v; s = 'disabled' if v else 'normal'
        for w in [self.act_btn, self.renew_btn, self.repl_btn]: w.config(state=s)

    def _on_key_change(self, ev=None):
        key = self.key_entry.get().strip()
        if len(key) >= 10:
            threading.Thread(target=lambda: self.root.after(0, lambda: self._update_details(
                self.engine.get_license_details(key))), daemon=True).start()

    def _update_details(self, d):
        if d.get('success'):
            data = d.get('data',{})
            self.plan_label.config(text=f"Plan: {{data.get('plan','--')}}")
            self.expiry_label.config(text=f"Expiry: {{data.get('expiry_date','--')}}")
            self.days_label.config(text=f"Remaining days: {{data.get('days_left','--')}}")
            self.dev_label.config(text=f"Device usage: {{data.get('device_count',0)}}/{{data.get('max_devices','--')}}")

    def _activate(self):
        key = self.key_entry.get().strip()
        if not key: self.status_label.config(text="Enter license key", fg="#dc2626"); return
        self._set_loading(True); self.status_label.config(text="Activating...", fg="#333")
        def do():
            try:
                r = self.engine.activate(key, device_name=self.device_name.get().strip() or None)
                self.root.after(0, lambda: self._on_result(r))
            except Exception as e: self.root.after(0, lambda: self.status_label.config(text=f"Error: {{str(e)}}", fg="#dc2626"))
        threading.Thread(target=do, daemon=True).start()

    def _on_result(self, r):
        self._set_loading(False)
        if r.get('success'):
            self.status_label.config(text="Activated!", fg="#16a34a")
            self.result = {'action': 'activated', 'license_key': self.key_entry.get().strip()}
            self.root.after(500, self.root.destroy)
        else: self.status_label.config(text=r.get('message','Failed'), fg="#dc2626")

    def _open_renewal(self):
        from .renewal import RenewalDialog
        d = RenewalDialog(self.engine, self.key_entry.get().strip())
        self.root.withdraw()
        if d.show(): self.root.destroy()
        else: self.root.deiconify()

    def _open_replace(self):
        from .device_replace import DeviceReplaceDialog
        d = DeviceReplaceDialog(self.engine, self.key_entry.get().strip())
        self.root.withdraw()
        if d.show(): self.root.destroy()
        else: self.root.deiconify()
