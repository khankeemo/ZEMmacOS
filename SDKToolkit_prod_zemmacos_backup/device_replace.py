"""Device Replacement Dialog for ZEM MAC OS"""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any


class DeviceReplaceDialog:
    def __init__(self, engine, license_key: str, parent=None):
        self.engine=engine; self.config=getattr(engine,'config',{})
        self._parent=parent
        self.license_key=license_key; self.engine._license_key=license_key
        self.result=None; self.root=None; self._loading=False

    def show(self)->Optional[Dict[str,Any]]:
        self._build_ui(); self.root.mainloop(); return self.result

    def _build_ui(self):
        branding=self.config.get('branding',{}); colors = branding.get('colors', {})
        primary=colors.get('primary', branding.get('primary_color','#6366f1')); bg=colors.get('bg_page','#f8f9fa')
        labels=branding.get('labels',{})
        unknown_lbl = labels.get('unknown_device', 'Unknown')
        s=self.engine.get_status()
        old_hw_str = s.hardware_id if s and s.hardware_id else unknown_lbl
        if s is None or not s.hardware_id:
            c=getattr(self.engine,'_cache',None)
            if c:
                cached = c.get_license_status()
                if cached: old_hw_str=cached.get('hardware_id', unknown_lbl)
        new_hw=self.engine.get_hardware_id()
        if not self._parent:
            raise RuntimeError("SDK dialogs require the application root window as parent")
        self.root = tk.Toplevel(self._parent)
        self.root.transient(self._parent)
        self.root.grab_set()
        self.root.title(labels.get('replace_title', "Replace Device")); self.root.geometry("450x430")
        self.root.resizable(False,False); self.root.configure(bg=bg)
        self.root.update_idletasks()
        sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight(); w=self.root.winfo_width(); h=self.root.winfo_height()
        self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        header=tk.Frame(self.root,bg=primary,height=60); header.pack(fill=tk.X); header.pack_propagate(False)
        tk.Label(header,text=labels.get('replace_title', "Replace Device"),fg="white",bg=primary,font=("Helvetica",16,"bold")).pack(expand=True)
        form=tk.Frame(self.root,bg=bg,padx=25,pady=15); form.pack(fill=tk.BOTH,expand=True)
        tk.Label(form,text=labels.get('device_replace_section', "Device Replacement"),font=("Helvetica",12,"bold"),bg=bg,fg=colors.get('text_primary','#333')).pack(anchor=tk.W,pady=(0,10))
        tk.Label(form,text=labels.get('device_replace_desc', "Move your license from old device to this one."),
                 font=("Helvetica",10),bg=bg,fg=colors.get('text_secondary','#555'),wraplength=380).pack(anchor=tk.W,pady=(0,12))
        hwf=tk.Frame(form,bg=bg); hwf.pack(fill=tk.X,pady=(0,10))
        tk.Label(hwf,text=labels.get('old_hardware_label', "Old Hardware")+":",font=("Helvetica",10,"bold"),bg=bg,fg=colors.get('text_secondary','#555')).pack(anchor=tk.W)
        tk.Label(hwf,text=old_hw_str[:48]+("..." if len(old_hw_str)>48 else ""),
                 font=("Courier",9),bg=bg,fg=colors.get('text_muted','#888'),wraplength=380,anchor=tk.W).pack(fill=tk.X,pady=(0,8))
        tk.Label(hwf,text=labels.get('new_hardware_label', "New Hardware")+":",font=("Helvetica",10,"bold"),bg=bg,fg=colors.get('text_secondary','#555')).pack(anchor=tk.W)
        tk.Label(hwf,text=new_hw[:48]+("..." if len(new_hw)>48 else ""),
                 font=("Courier",9),bg=bg,fg=colors.get('text_primary','#333'),wraplength=380,anchor=tk.W).pack(fill=tk.X,pady=(0,10))
        tk.Label(hwf,text=labels.get('device_name_label', "Device Name")+":",font=("Helvetica",10,"bold"),bg=bg,fg=colors.get('text_secondary','#555')).pack(anchor=tk.W)
        self.dev_name=tk.Entry(hwf,font=("Helvetica",10),relief=tk.SOLID,bd=1)
        self.dev_name.pack(fill=tk.X,ipady=3)
        import platform; self.dev_name.insert(0,platform.node() or labels.get('new_device', 'New Device'))
        ttk.Separator(form,orient=tk.HORIZONTAL).pack(fill=tk.X,pady=8)
        self.repl_btn=tk.Button(form,text=labels.get('replace_btn', "Replace Device"),command=self._replace,
                                 font=("Helvetica",12,"bold"),bg=primary,fg="white",relief=tk.FLAT,padx=15,pady=8)
        self.repl_btn.pack(fill=tk.X,pady=(5,5))
        btn_bg = colors.get('bg_button', '#e5e7eb'); btn_fg = colors.get('text_primary', '#333')
        self.cancel_btn=tk.Button(form,text=labels.get('cancel_btn', "Cancel"),command=self.root.destroy,
                                   font=("Helvetica",10),bg=btn_bg,fg=btn_fg,relief=tk.FLAT,padx=10,pady=5)
        self.cancel_btn.pack()
        self.st=tk.Label(form,text="",font=("Helvetica",9),bg=bg,fg=colors.get('text_primary','#333'),wraplength=380); self.st.pack(pady=(5,0))
        self.root.bind('<Escape>',lambda e:self.root.destroy())

    def _set_loading(self,v): self._loading=v; self.repl_btn.config(state='disabled' if v else 'normal')

    def _replace(self):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(True); self.st.config(text="Replacing device...",fg=colors.get('text_primary','#333'))
        def do():
            try:
                r=self.engine.replace_hardware(device_name=self.dev_name.get().strip() or None)
                self.root.after(0,lambda: self._on_result(r))
            except Exception as e: self.root.after(0,lambda: self.st.config(text=f"Error: {str(e)}",fg=colors.get('error','#dc2626')))
        threading.Thread(target=do,daemon=True).start()

    def _on_result(self,r):
        colors = self.config.get('branding', {}).get('colors', {})
        self._set_loading(False)
        if r.get('success'):
            self.st.config(text="Device replaced!",fg=colors.get('success','#16a34a')); self.result={'action':'device_replaced'}
            self.root.after(500,self.root.destroy)
        else: self.st.config(text=r.get('message','Failed'),fg=colors.get('error','#dc2626'))
