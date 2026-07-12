"""Status Widget for ZEM MAC OS"""
import tkinter as tk
from tkinter import ttk


class StatusWidget:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine; self.frame=ttk.Frame(parent)
    def build(self)->ttk.Frame:
        self.frame.pack(fill=tk.X,padx=5,pady=2)
        inner=tk.Frame(self.frame,bg="#f8f9fa",padx=8,pady=4); inner.pack(fill=tk.X)
        self.icon=tk.Label(inner,text="\u25CF",font=("Helvetica",14),bg="#f8f9fa",fg="#888")
        self.icon.pack(side=tk.LEFT,padx=(0,5))
        self.label=tk.Label(inner,text="Checking...",font=("Helvetica",10),bg="#f8f9fa",fg="#555")
        self.label.pack(side=tk.LEFT)
        self.refresh(); return self.frame
    def refresh(self):
        s=self.engine.get_status() or self.engine.initialize()
        if s and s.valid:
            t=f"Trial: {{s.days_remaining}}d" if s.trial_active else f"Licensed: {{s.days_remaining}}d"
            c="#f59e0b" if s.trial_active else "#16a34a"
            self.label.config(text=t,fg=c); self.icon.config(fg=c)
        else:
            self.label.config(text=s.message if s else "No license",fg="#dc2626")
            self.icon.config(fg="#dc2626")
