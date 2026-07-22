"""Status Widget for ZEM MAC OS"""
import tkinter as tk
from tkinter import ttk


class StatusWidget:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine; self.frame=ttk.Frame(parent)
    def build(self)->ttk.Frame:
        self.frame.pack(fill=tk.X,padx=5,pady=2)
        branding=self.engine.config.get('branding',{}); colors=branding.get('colors',{}); labels=branding.get('labels',{})
        bg=colors.get('bg_page','#f8f9fa'); tx_m=colors.get('text_muted','#888'); tx_s=colors.get('text_secondary','#555')
        inner=tk.Frame(self.frame,bg=bg,padx=8,pady=4); inner.pack(fill=tk.X)
        self.icon=tk.Label(inner,text="\u25cf",font=("Helvetica",14),bg=bg,fg=tx_m)
        self.icon.pack(side=tk.LEFT,padx=(0,5))
        self.label=tk.Label(inner,text=labels.get('checking_status',"Checking..."),font=("Helvetica",10),bg=bg,fg=tx_s)
        self.label.pack(side=tk.LEFT)
        self.refresh(); return self.frame
    def refresh(self):
        branding=self.engine.config.get('branding',{}); colors=branding.get('colors',{}); labels=branding.get('labels',{})
        s=self.engine.get_status() or self.engine.initialize()
        if s and s.valid:
            t=f"{labels.get('trial_active_text','Trial')}: {s.days_left}d" if s.trial_active else f"{labels.get('licensed_text','Licensed')}: {s.days_left}d"
            c=colors.get('warning','#f59e0b') if s.trial_active else colors.get('success','#16a34a')
            self.label.config(text=t,fg=c); self.icon.config(fg=c)
        else:
            self.label.config(text=s.message if s else labels.get('no_license_text',"No license"),fg=colors.get('error','#dc2626'))
            self.icon.config(fg=colors.get('error','#dc2626'))
