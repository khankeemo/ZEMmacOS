"""Settings Widget for ZEM MAC OS"""
import tkinter as tk
from tkinter import ttk


class SettingsWidget:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine; self.frame=ttk.Frame(parent); self._w={}
    def build(self)->ttk.Frame:
        self.frame.pack(fill=tk.BOTH,expand=True)
        nb=ttk.Notebook(self.frame); nb.pack(fill=tk.BOTH,expand=True,padx=10,pady=10)
        tab=ttk.Frame(nb); nb.add(tab,text="License"); self._build_tab(tab); return self.frame
    def _build_tab(self,parent):
        cv=tk.Frame(parent,bg="#f8f9fa",padx=20,pady=15); cv.pack(fill=tk.BOTH,expand=True)
        tk.Label(cv,text="License Information",font=("Helvetica",13,"bold"),bg="#f8f9fa",fg="#333").pack(anchor=tk.W,pady=(0,12))
        self._w['s']=tk.Label(cv,text="Status: --",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['s'].pack(anchor=tk.W,pady=2)
        self._w['p']=tk.Label(cv,text="Product: --",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['p'].pack(anchor=tk.W,pady=2)
        self._w['e']=tk.Label(cv,text="Expiry: --",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['e'].pack(anchor=tk.W,pady=2)
        self._w['pl']=tk.Label(cv,text="Plan: --",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['pl'].pack(anchor=tk.W,pady=2)
        self._w['h']=tk.Label(cv,text="Hardware ID: --",font=("Courier",9),bg="#f8f9fa",fg="#888"); self._w['h'].pack(anchor=tk.W,pady=2)
        self._w['r']=tk.Label(cv,text="Runtime: Python",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['r'].pack(anchor=tk.W,pady=2)
        ver=self.engine.config.get('product',{}).get('version','1.0.0')
        self._w['sdk']=tk.Label(cv,text=f"SDK Version: {{ver}}",font=("Helvetica",10),bg="#f8f9fa",fg="#555"); self._w['sdk'].pack(anchor=tk.W,pady=2)
        ttk.Separator(cv,orient=tk.HORIZONTAL).pack(fill=tk.X,pady=12)
        bf=tk.Frame(cv,bg="#f8f9fa"); bf.pack(fill=tk.X)
        for txt,cmd,clr in [("Activate",self._open_activation,"#6366f1"),("Renew",self._open_renewal,"#10b981"),
                            ("Replace Device",self._open_replace,"#f59e0b"),("Refresh",self.refresh,"#6b7280"),
                            ("Open Welcome",self._open_welcome,"#8b5cf6")]:
            tk.Button(bf,text=txt,command=cmd,font=("Helvetica",10),bg=clr,fg="white",relief=tk.FLAT,padx=12,pady=5).pack(fill=tk.X,pady=3)
        self.refresh()
    def refresh(self):
        s=self.engine.get_status() or self.engine.initialize()
        if s:
            self._w['s'].config(text=f"Status: {{s.status.upper()}}",fg="#16a34a" if s.valid else "#dc2626")
            n=self.engine.config.get('product',{}).get('name','--')
            self._w['p'].config(text=f"Product: {{n}}"); self._w['e'].config(text=f"Expiry: {{s.expires_at or 'N/A'}}")
            self._w['pl'].config(text=f"Plan: {{s.plan or 'N/A'}}"); self._w['h'].config(text=f"Hardware ID: {{s.hardware_id or '--'}}")
    def _open_activation(self):
        from ..activation import ActivationDialog
        ActivationDialog(self.engine).show(); self.refresh()
    def _open_renewal(self):
        from ..renewal import RenewalDialog
        k=self.engine.get_license_key()
        if k: RenewalDialog(self.engine,k).show(); self.refresh()
    def _open_replace(self):
        from ..device_replace import DeviceReplaceDialog
        k=self.engine.get_license_key()
        if k: DeviceReplaceDialog(self.engine,k).show(); self.refresh()
    def _open_welcome(self):
        from ..welcome import WelcomeDialog
        WelcomeDialog(self.engine).show(); self.refresh()
