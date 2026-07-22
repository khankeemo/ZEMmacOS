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
        branding=self.engine.config.get('branding',{}); labels=branding.get('labels',{}); colors=branding.get('colors',{})
        bg=colors.get('bg_page','#f8f9fa'); tx_p=colors.get('text_primary','#333'); tx_s=colors.get('text_secondary','#555'); tx_m=colors.get('text_muted','#888')
        cv=tk.Frame(parent,bg=bg,padx=20,pady=15); cv.pack(fill=tk.BOTH,expand=True)
        tk.Label(cv,text=labels.get('license_info_section',"License Information"),font=("Helvetica",13,"bold"),bg=bg,fg=tx_p).pack(anchor=tk.W,pady=(0,12))
        status_lbl=labels.get('status_label','Status'); prod_lbl=labels.get('product_label','Product')
        expiry_lbl=labels.get('expiry_label','Expiry'); plan_lbl=labels.get('plan_label','Plan')
        hw_lbl=labels.get('hardware_id_label','Hardware ID'); runtime_lbl=labels.get('runtime_label','Runtime')
        sdk_lbl=labels.get('sdk_version_label','SDK Version'); ph=labels.get('hardware_placeholder','--')
        self._w['s']=tk.Label(cv,text=f"{status_lbl}: {ph}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['s'].pack(anchor=tk.W,pady=2)
        self._w['p']=tk.Label(cv,text=f"{prod_lbl}: {ph}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['p'].pack(anchor=tk.W,pady=2)
        self._w['e']=tk.Label(cv,text=f"{expiry_lbl}: {ph}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['e'].pack(anchor=tk.W,pady=2)
        self._w['pl']=tk.Label(cv,text=f"{plan_lbl}: {ph}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['pl'].pack(anchor=tk.W,pady=2)
        self._w['h']=tk.Label(cv,text=f"{hw_lbl}: {ph}",font=("Courier",9),bg=bg,fg=tx_m); self._w['h'].pack(anchor=tk.W,pady=2)
        runtime_val=labels.get('runtime_value','Python')
        self._w['r']=tk.Label(cv,text=f"{runtime_lbl}: {runtime_val}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['r'].pack(anchor=tk.W,pady=2)
        ver=self.engine.config.get('product',{}).get('version','')
        self._w['sdk']=tk.Label(cv,text=f"{sdk_lbl}: {ver}",font=("Helvetica",10),bg=bg,fg=tx_s); self._w['sdk'].pack(anchor=tk.W,pady=2)
        ttk.Separator(cv,orient=tk.HORIZONTAL).pack(fill=tk.X,pady=12)
        bf=tk.Frame(cv,bg=bg); bf.pack(fill=tk.X)
        for cmd,clr,txt in [(self._open_activation,colors.get('primary','#6366f1'),labels.get('activate_btn',"Activate")),
                            (self._open_renewal,colors.get('info','#10b981'),labels.get('renew_btn',"Renew")),
                            (self._open_replace,colors.get('warning','#f59e0b'),labels.get('replace_btn',"Replace Device")),
                            (self.refresh,colors.get('gray','#6b7280'),labels.get('refresh_btn',"Refresh")),
                            (self._open_welcome,colors.get('accent','#8b5cf6'),labels.get('open_welcome_btn',"Open Welcome"))]:
            tk.Button(bf,text=txt,command=cmd,font=("Helvetica",10),bg=clr,fg="white",relief=tk.FLAT,padx=12,pady=5).pack(fill=tk.X,pady=3)
        self.refresh()
    def refresh(self):
        branding=self.engine.config.get('branding',{}); labels=branding.get('labels',{}); colors=branding.get('colors',{})
        s=self.engine.get_status() or self.engine.initialize()
        status_lbl=labels.get('status_label','Status'); prod_lbl=labels.get('product_label','Product')
        expiry_lbl=labels.get('expiry_label','Expiry'); plan_lbl=labels.get('plan_label','Plan')
        hw_lbl=labels.get('hardware_id_label','Hardware ID')
        if s:
            self._w['s'].config(text=f"{status_lbl}: {s.status.upper()}",fg=colors.get('success','#16a34a') if s.valid else colors.get('error','#dc2626'))
            n=self.engine.config.get('product',{}).get('name','')
            self._w['p'].config(text=f"{prod_lbl}: {n}"); self._w['e'].config(text=f"{expiry_lbl}: {s.expiry_date or labels.get('expiry_na', 'N/A')}")
            self._w['pl'].config(text=f"{plan_lbl}: {s.plan or labels.get('plan_na', 'N/A')}"); self._w['h'].config(text=f"{hw_lbl}: {s.hardware_id or labels.get('hardware_placeholder', '--')}")
    def _open_activation(self):
        from ..activation import ActivationDialog
        ActivationDialog(
            getattr(self.engine, '_client', None),
            product_name=self.engine.config.get('product', {}).get('name', ''),
            cache=getattr(self.engine, '_cache', None)
        ).show(); self.refresh()
    def _open_renewal(self):
        from ..renewal import RenewalDialog
        k=self.engine.get_license_key()
        if k: RenewalDialog(self.engine,k, parent=self.parent).show(); self.refresh()
    def _open_replace(self):
        from ..device_replace import DeviceReplaceDialog
        k=self.engine.get_license_key()
        if k: DeviceReplaceDialog(self.engine,k, parent=self.parent).show(); self.refresh()
    def _open_welcome(self):
        from ..welcome import WelcomeDialog
        WelcomeDialog(
            getattr(self.engine, '_client', None),
            product_name=self.engine.config.get('product', {}).get('name', ''),
            cache=getattr(self.engine, '_cache', None)
        ).show(); self.refresh()
