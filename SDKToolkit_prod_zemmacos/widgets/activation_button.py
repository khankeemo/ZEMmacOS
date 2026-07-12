"""Activation Button for ZEM MAC OS"""
import tkinter as tk


class ActivationButton:
    def __init__(self, parent, engine):
        self.parent=parent; self.engine=engine; self.btn=None
    def build(self)->tk.Button:
        self.btn=tk.Button(self.parent,text="Activate License",command=self._click,
                            font=("Helvetica",10,"bold"),bg="#6366f1",fg="white",relief=tk.FLAT,padx=15,pady=6,cursor="hand2")
        self.btn.pack(); return self.btn
    def _click(self):
        from ..activation import ActivationDialog
        r=ActivationDialog(self.engine).show()
        if r and r.get('action')=='activated' and self.btn:
            self.btn.config(text="Licensed",bg="#16a34a")
