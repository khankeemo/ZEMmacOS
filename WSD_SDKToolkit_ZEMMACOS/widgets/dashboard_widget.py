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
        branding=self.engine.config.get('branding',{}); labels=branding.get('labels',{}); colors=branding.get('colors',{})
        bg=colors.get('bg_page','#f8f9fa'); tx_p=colors.get('text_primary','#333'); tx_s=colors.get('text_secondary','#555')
        btn_bg=colors.get('bg_button','#e5e7eb')
        tk.Label(self.frame,text=labels.get('license_status_section', "License Status"),font=("Helvetica",14,"bold"),fg=tx_p).pack(pady=(10,5))
        inf=tk.Frame(self.frame,bg=bg,padx=15,pady=10); inf.pack(fill=tk.X,padx=10)
        status_lbl = labels.get('status_label', 'Status')
        self._w['s']=tk.Label(inf,text=f"{status_lbl}: {labels.get('checking_status', 'Checking...')}",font=("Helvetica",11),bg=bg,fg=tx_p)
        self._w['s'].pack(anchor=tk.W,pady=2)
        self._w['t']=tk.Label(inf,text="",font=("Helvetica",11),bg=bg,fg=tx_s); self._w['t'].pack(anchor=tk.W,pady=2)
        self._w['d']=tk.Label(inf,text="",font=("Helvetica",11),bg=bg,fg=tx_s); self._w['d'].pack(anchor=tk.W,pady=2)
        self._w['e']=tk.Label(inf,text="",font=("Helvetica",11),bg=bg,fg=tx_s); self._w['e'].pack(anchor=tk.W,pady=2)
        self._w['p']=tk.Label(inf,text="",font=("Helvetica",11),bg=bg,fg=tx_s); self._w['p'].pack(anchor=tk.W,pady=2)
        tk.Button(self.frame,text=labels.get('refresh_btn',"Refresh"),command=self.refresh,font=("Helvetica",9),bg=btn_bg,fg=tx_p,relief=tk.FLAT,padx=10,pady=3).pack(pady=(8,5))
        self.refresh(); return self.frame
    def refresh(self):
        branding=self.engine.config.get('branding',{}); labels=branding.get('labels',{}); colors=branding.get('colors',{})
        s=self.engine.get_status() or self.engine.initialize()
        status_lbl = labels.get('status_label', 'Status')
        days_lbl = labels.get('remaining_days_label', 'Remaining days')
        expiry_lbl = labels.get('expiry_label', 'Expiry')
        plan_lbl = labels.get('plan_label', 'Plan')
        if s and s.valid:
            c=colors.get('success','#16a34a'); label=labels.get('trial_active_text','Trial Active') if s.trial_active else labels.get('licensed_text','Licensed')
            self._w['s'].config(text=f"{status_lbl}: {label}",fg=c)
            self._w['t'].config(text=label)
            self._w['d'].config(text=f"{days_lbl}: {s.days_left}")
            self._w['e'].config(text=f"{expiry_lbl}: {s.expiry_date or labels.get('expiry_na', 'N/A')}")
            self._w['p'].config(text=f"{plan_lbl}: {s.plan or labels.get('plan_na', 'N/A')}")
        else:
            self._w['s'].config(text=f"{status_lbl}: {labels.get('unlicensed_status', 'Unlicensed')}",fg=colors.get('error','#dc2626')); self._w['t'].config(text=labels.get('no_active_text', 'No active license or trial'))
            for k in ['d','e','p']: self._w[k].config(text="")
