"""Activation Button for ZEM MAC OS"""
import tkinter as tk


class ActivationButton:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine; self.btn=None
    def build(self)->tk.Button:
        branding=self.engine.config.get('branding',{}); labels=branding.get('labels',{}); colors=branding.get('colors',{})
        primary=colors.get('primary','#6366f1')
        self.btn=tk.Button(self.parent,text=labels.get('activate_license_btn',"Activate License"),command=self._click,
                            font=("Helvetica",10,"bold"),bg=primary,fg="white",relief=tk.FLAT,padx=15,pady=6,cursor="hand2")
        self.btn.pack(); return self.btn
    def _click(self):
        colors=self.engine.config.get('branding',{}).get('colors',{})
        labels=self.engine.config.get('branding',{}).get('labels',{})
        from ..activation import ActivationDialog
        r=ActivationDialog(
            getattr(self.engine, '_client', None),
            product_name=self.engine.config.get('product', {}).get('name', ''),
            cache=getattr(self.engine, '_cache', None)
        ).show()
        if r and r.get('activated') and self.btn:
            self.btn.config(text=labels.get('licensed_text',"Licensed"),bg=colors.get('success','#16a34a'))
