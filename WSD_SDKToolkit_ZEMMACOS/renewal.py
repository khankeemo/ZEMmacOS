"""Renewal Dialog for ZEM MAC OS"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any


class RenewalDialog:
    def __init__(self, engine, license_key: str, parent=None):
        self.engine = engine; self.client = getattr(engine, '_client', None)
        self.config = getattr(engine, 'config', {})
        self._parent = parent
        self.license_key = license_key; self.engine._license_key = license_key
        self.result = None; self.root = None; self.plans = []; self._loading = False

    def show(self) -> Optional[Dict[str, Any]]:
        self._build_ui(); self.root.mainloop(); return self.result

    def _build_ui(self):
        branding = self.config.get('branding',{}); colors = branding.get('colors', {})
        primary = colors.get('primary', branding.get('primary_color','#6366f1')); bg=colors.get('bg_page','#f8f9fa')
        labels = branding.get('labels', {})
        if not self._parent:
            raise RuntimeError("SDK dialogs require the application root window as parent")
        self.root = tk.Toplevel(self._parent)
        self.root.transient(self._parent)
        self.root.grab_set()
        self.root.title(labels.get('renew_title', "Renew License")); self.root.geometry("450x500")
        self.root.resizable(False,False); self.root.configure(bg=bg)
        self.root.update_idletasks()
        sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight(); w=self.root.winfo_width(); h=self.root.winfo_height()
        self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        header=tk.Frame(self.root,bg=primary,height=60); header.pack(fill=tk.X); header.pack_propagate(False)
        tk.Label(header,text=labels.get('renew_title', "Renew License"),fg="white",bg=primary,font=("Helvetica",16,"bold")).pack(expand=True)
        form=tk.Frame(self.root,bg=bg,padx=25,pady=15); form.pack(fill=tk.BOTH,expand=True)

        tk.Label(form,text=labels.get('current_license_section', "Current License"),font=("Helvetica",11,"bold"),bg=bg,fg=colors.get('text_primary','#333')).pack(anchor=tk.W,pady=(0,5))
        cf=tk.Frame(form,bg=bg); cf.pack(fill=tk.X,pady=(0,10))
        s=self.engine.get_status()
        plan_lbl = labels.get('plan_label', 'Plan'); expiry_lbl = labels.get('expiry_label', 'Expiry')
        self.plan_lbl=tk.Label(cf,text=f"{plan_lbl}: {s.plan if s else labels.get('hardware_placeholder', '--')}",font=("Helvetica",10),bg=bg,fg=colors.get('text_secondary','#555')); self.plan_lbl.pack(anchor=tk.W)
        self.exp_lbl=tk.Label(cf,text=f"{expiry_lbl}: {s.expiry_date if s else labels.get('expiry_na', 'N/A')}",font=("Helvetica",10),bg=bg,fg=colors.get('text_secondary','#555')); self.exp_lbl.pack(anchor=tk.W)

        ttk.Separator(form,orient=tk.HORIZONTAL).pack(fill=tk.X,pady=8)
        tk.Label(form,text=labels.get('available_plans_section', "Available Plans"),font=("Helvetica",11,"bold"),bg=bg,fg=colors.get('text_primary','#333')).pack(anchor=tk.W,pady=(0,5))
        lf=tk.Frame(form,bg=bg); lf.pack(fill=tk.BOTH,expand=True,pady=(0,10))
        sb=tk.Scrollbar(lf); sb.pack(side=tk.RIGHT,fill=tk.Y)
        self.lb=tk.Listbox(lf,font=("Helvetica",10),yscrollcommand=sb.set,relief=tk.SOLID,bd=1)
        sb.config(command=self.lb.yview); self.lb.pack(fill=tk.BOTH,expand=True)

        ttk.Separator(form,orient=tk.HORIZONTAL).pack(fill=tk.X,pady=5)
        self.renew_btn=tk.Button(form,text=labels.get('renew_btn', "Renew License"),command=self._renew,
                                  font=("Helvetica",12,"bold"),bg=primary,fg="white",relief=tk.FLAT,padx=15,pady=8)
        self.renew_btn.pack(fill=tk.X,pady=(5,5))
        self.st=tk.Label(form,text="",font=("Helvetica",9),bg=bg,fg=colors.get('text_primary','#333'),wraplength=400); self.st.pack()
        self.root.bind('<Escape>',lambda e:self.root.destroy())
        self._load_plans()

    def _set_loading(self,v): self._loading=v; self.renew_btn.config(state='disabled' if v else 'normal')

    def _load_plans(self):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(True); self.st.config(text="Loading plans...",fg=colors.get('text_muted','#888'))
        def do():
            try: self.root.after(0,lambda: self._on_plans(self.engine.get_plans()))
            except Exception as e: self.root.after(0,lambda: self.st.config(text=f"Error: {str(e)}",fg=colors.get('error','#dc2626')))
        threading.Thread(target=do,daemon=True).start()

    def _on_plans(self,r):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if r.get('success'):
            self.plans=r.get('data',r.get('plans',[])); self.lb.delete(0,tk.END)
            for i,p in enumerate(self.plans):
                self.lb.insert(tk.END,f"{p.get('name',f'Plan {i+1}')} - {p.get('price','--')} ({p.get('duration_days',p.get('default_expiry_days','--'))} days)")
            if self.plans: self.lb.selection_set(0)
            self.lb.bind('<<ListboxSelect>>',self._on_select)
        else: self.st.config(text=r.get('message','Failed'),fg=colors.get('error','#dc2626'))

    def _on_select(self,ev):
        sel=self.lb.curselection()
        if sel and sel[0]<len(self.plans): self.selected_plan=self.plans[sel[0]]
        else: self.selected_plan=None

    def _renew(self):
        colors = self.config.get('branding', {}).get('colors', {})
        if not self.selected_plan: self.st.config(text="Select a plan",fg=colors.get('error','#dc2626')); return
        self._set_loading(True); self.st.config(text="Processing...",fg=colors.get('text_primary','#333'))
        extra = self.selected_plan.get('duration_days') if isinstance(self.selected_plan, dict) else None
        def do():
            try:
                r=self.engine.renew(extra_days=extra)
                self.root.after(0,lambda: self._on_renew(r))
            except Exception as e: self.root.after(0,lambda: self.st.config(text=f"Error: {str(e)}",fg=colors.get('error','#dc2626')))
        threading.Thread(target=do,daemon=True).start()

    def _on_renew(self,r):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if r.get('success'):
            self.st.config(text="Renewed!",fg=colors.get('success','#16a34a')); self.result={'action':'renewed'}
            self.root.after(500,self.root.destroy)
        else: self.st.config(text=r.get('message','Failed'),fg=colors.get('error','#dc2626'))
