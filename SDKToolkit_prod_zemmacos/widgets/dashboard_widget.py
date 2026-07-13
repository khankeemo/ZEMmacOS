"""Dashboard Widget for ZEM MAC OS"""
import tkinter as tk
from tkinter import ttk


class DashboardWidget:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine
        self.frame=ttk.Frame(parent)
        self._w={}
    def build(self)->ttk.Frame:
        self.frame.pack(fill=tk.BOTH,expand=True)
        tk.Label(self.frame,text="License Status",font=("Helvetica",14,"bold"),fg="#333").pack(pady=(10,5))
        inf=tk.Frame(self.frame,bg="#f8f9fa",padx=15,pady=10); inf.pack(fill=tk.X,padx=10)
        self._w['s']=tk.Label(inf,text="Status: Checking...",font=("Helvetica",11),bg="#f8f9fa",fg="#333")
        self._w['s'].pack(anchor=tk.W,pady=2)
        self._w['t']=tk.Label(inf,text="",font=("Helvetica",11),bg="#f8f9fa",fg="#555"); self._w['t'].pack(anchor=tk.W,pady=2)
        self._w['d']=tk.Label(inf,text="",font=("Helvetica",11),bg="#f8f9fa",fg="#555"); self._w['d'].pack(anchor=tk.W,pady=2)
        self._w['e']=tk.Label(inf,text="",font=("Helvetica",11),bg="#f8f9fa",fg="#555"); self._w['e'].pack(anchor=tk.W,pady=2)
        self._w['p']=tk.Label(inf,text="",font=("Helvetica",11),bg="#f8f9fa",fg="#555"); self._w['p'].pack(anchor=tk.W,pady=2)
        tk.Button(self.frame,text="Refresh",command=self.refresh,font=("Helvetica",9),bg="#e5e7eb",fg="#333",relief=tk.FLAT,padx=10,pady=3).pack(pady=(8,5))
        self.refresh(); return self.frame
    def refresh(self):
        s=self.engine.get_status() or self.engine.initialize()
        if s.valid:
            color="#16a34a"; label="Trial Active" if s.trial_active else "Licensed"
            self._w['s'].config(text=f"Status: {{label}}",fg=color)
            self._w['d'].config(text=f"Remaining days: {{s.days_remaining}}")
            self._w['e'].config(text=f"Expiry: {{s.expires_at or 'N/A'}}")
            self._w['p'].config(text=f"Plan: {{s.plan or 'N/A'}}")
        else:
            self._w['s'].config(text="Status: Unlicensed",fg="#dc2626"); self._w['t'].config(text="No active license or trial")
            for k in ['d','e','p']: self._w[k].config(text="")
