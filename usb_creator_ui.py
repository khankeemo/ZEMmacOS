import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
from datetime import datetime
from usb_creator import USBCreator

class USBCreatorUI:
    def __init__(self, parent_window=None):
        if parent_window and isinstance(parent_window, tk.Tk):
            self.root = tk.Toplevel(parent_window)
            self.root.title("Prepare macOS Installer")
            self.root.transient(parent_window)
            self.root.grab_set()
            self._is_modal = True
        else:
            self.root = tk.Tk()
            self.root.title("Prepare macOS Installer")
            self._is_modal = False
        
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        self.root.configure(bg="#f5f5f7")
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1000x800+{x}+{y}")
        
        self.colors = {
            "bg": "#f5f5f7", "card": "#ffffff", "card_border": "#e0e0e0", "accent": "#0071e3", "accent_hover": "#005bbf",
            "text_dark": "#1d1d1f", "text_light": "#86868b", "success": "#34c759", "warning": "#ff9f0a", "error": "#ff3b30",
            "console_bg": "#1e1e1e", "console_text": "#d4d4d4"
        }
        
        self.validator = USBCreator(callback=self.log, progress_callback=self.update_progress)
        self.path_var = tk.StringVar(value=self.validator.load_last_path())
        self.validation_status = tk.StringVar(value="Ready - Select a folder to begin")
        self.progress_value = tk.IntVar(value=0)
        self.progress_message = tk.StringVar(value="Waiting for input...")
        self.is_validating = False
        self.current_result = None
        
        self.setup_ui()
        if self.path_var.get() and os.path.exists(self.path_var.get()):
            self.root.after(500, self.validate_path)

    def setup_ui(self):
        canvas = tk.Canvas(self.root, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=canvas.winfo_width())
        def resize_frame(event): canvas.itemconfig(1, width=event.width)
        canvas.bind("<Configure>", resize_frame)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        container = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True)
        main_frame = tk.Frame(container, bg=self.colors["bg"], width=880)
        main_frame.pack(pady=20)
        
        self.create_header(main_frame)
        self.create_info_card(main_frame)
        self.create_path_card(main_frame)
        self.create_detection_card(main_frame)
        self.create_progress_card(main_frame)
        self.create_validation_card(main_frame)
        self.create_next_steps_card(main_frame)
        self.create_console_card(main_frame)
        self.create_footer(main_frame)

    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        tk.Label(header_frame, text="💿 Prepare macOS Installer", font=("SF Pro Display", 24, "bold"), fg=self.colors["text_dark"], bg=self.colors["bg"]).pack(anchor=tk.W)
        tk.Label(header_frame, text="Validate macOS installer files downloaded on Windows", font=("SF Pro Text", 12), fg=self.colors["text_light"], bg=self.colors["bg"]).pack(anchor=tk.W, pady=(5, 0))

    def create_info_card(self, parent):
        card, content = self.create_card(parent, "📋 How It Works", 15)
        for step in ["1. Download macOS using the Library tab in ZEMmacOS", "2. Select a macOS folder, .app installer, or InstallAssistant.pkg below", "3. The tool will scan and validate the file structure", "4. Verified resources are ready for your workflow"]:
            tk.Label(content, text=step, font=("SF Pro Text", 11), fg=self.colors["text_dark"], bg=self.colors["card"], anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=2)

    def create_card(self, parent, title, padding=15):
        card = tk.Frame(parent, bg=self.colors["card"], relief=tk.RIDGE, bd=0, highlightbackground=self.colors["card_border"], highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 15))
        title_bar = tk.Frame(card, bg=self.colors["card"], height=40)
        title_bar.pack(fill=tk.X, padx=padding, pady=(padding, 0))
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text=title, font=("SF Pro Text", 13, "bold"), fg=self.colors["text_dark"], bg=self.colors["card"]).pack(side=tk.LEFT)
        content_frame = tk.Frame(card, bg=self.colors["card"])
        content_frame.pack(fill=tk.X, padx=padding, pady=(0, padding))
        return card, content_frame

    def create_path_card(self, parent):
        card, content = self.create_card(parent, "📂 Select macOS Folder, Installer (.app), or InstallAssistant.pkg", 15)
        entry_frame = tk.Frame(content, bg=self.colors["card"])
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Entry(entry_frame, textvariable=self.path_var, font=("SF Pro Text", 11), bg=self.colors["bg"], fg=self.colors["text_dark"], insertbackground=self.colors["accent"], bd=1, relief=tk.FLAT, highlightthickness=1, highlightcolor=self.colors["accent"], highlightbackground=self.colors["card_border"]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Button(entry_frame, text="📂 Browse", command=self.browse_path, font=("SF Pro Text", 11), fg="white", bg=self.colors["accent"], activebackground=self.colors["accent_hover"], bd=0, padx=20, pady=8, cursor="hand2").pack(side=tk.RIGHT)
        
        button_frame = tk.Frame(content, bg=self.colors["card"])
        button_frame.pack(fill=tk.X, pady=(10, 0))
        self.validate_btn = tk.Button(button_frame, text="🔍 Scan & Validate", command=self.validate_path, font=("SF Pro Text", 11, "bold"), fg="white", bg=self.colors["success"], activebackground="#2e8b57", bd=0, padx=20, pady=10, cursor="hand2")
        self.validate_btn.pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(button_frame, text="🔄 Reset", command=self.reset_path, font=("SF Pro Text", 11), fg="white", bg=self.colors["warning"], activebackground="#e08e00", bd=0, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(button_frame, text="📂 Open Location", command=self.open_path, font=("SF Pro Text", 11), fg=self.colors["text_dark"], bg=self.colors["bg"], activebackground="#e0e0e0", bd=1, relief=tk.FLAT, padx=20, pady=10, cursor="hand2").pack(side=tk.LEFT, padx=(0, 10))

    def create_detection_card(self, parent):
        card, content = self.create_card(parent, "🏷️ Detected Type", 15)
        self.badge_label = tk.Label(content, text="Not detected yet", font=("SF Pro Text", 11), fg=self.colors["text_light"], bg=self.colors["card"], anchor=tk.W)
        self.badge_label.pack(anchor=tk.W, pady=5)

    def create_progress_card(self, parent):
        card, content = self.create_card(parent, "📊 Progress", 15)
        self.progress_bar = ttk.Progressbar(content, mode='determinate', variable=self.progress_value, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_label = tk.Label(content, textvariable=self.progress_message, font=("SF Pro Text", 10), fg=self.colors["text_light"], bg=self.colors["card"], anchor=tk.W)
        self.progress_label.pack(anchor=tk.W, pady=(5, 0))

    def create_validation_card(self, parent):
        card, content = self.create_card(parent, "✅ Validation Status", 15)
        self.status_label = tk.Label(content, textvariable=self.validation_status, font=("SF Pro Text", 12), fg=self.colors["text_light"], bg=self.colors["card"], anchor=tk.W)
        self.status_label.pack(anchor=tk.W, pady=(0, 10))
        self.type_label = tk.Label(content, text="", font=("SF Pro Text", 10), fg=self.colors["text_light"], bg=self.colors["card"], anchor=tk.W)
        self.type_label.pack(anchor=tk.W, pady=(0, 5))
        self.files_frame = tk.Frame(content, bg=self.colors["card"])
        self.files_frame.pack(fill=tk.X)
        self.size_label = tk.Label(content, text="", font=("SF Pro Text", 10), fg=self.colors["text_light"], bg=self.colors["card"], anchor=tk.W)
        self.size_label.pack(anchor=tk.W, pady=(5, 0))

    def create_next_steps_card(self, parent):
        card, content = self.create_card(parent, "🚀 Next Steps", 15)
        tk.Label(content, text="✓ Validated resources are ready for your workflow", font=("SF Pro Text", 11), fg=self.colors["success"], bg=self.colors["card"], anchor=tk.W).pack(anchor=tk.W, pady=(0, 10))
        self.steps_text = tk.Text(content, font=("SF Mono", 10), bg=self.colors["console_bg"], fg=self.colors["console_text"], wrap=tk.WORD, height=6, bd=0, relief=tk.FLAT)
        self.steps_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.steps_text.tag_config("title", font=("SF Mono", 11, "bold"), foreground="#00ff88")
        self.steps_text.tag_config("step", foreground="#51cf66")
        self.steps_text.tag_config("info", foreground="#86868b")
        self.steps_text.insert(tk.END, "VALIDATION COMPLETE\n\n", "title")
        self.steps_text.insert(tk.END, "• Files verified and ready\n", "step")
        self.steps_text.insert(tk.END, "• Structure validated\n", "step")
        self.steps_text.insert(tk.END, "• No corruption detected\n", "step")
        self.steps_text.insert(tk.END, "\nResources can now be used in your workflow.\n", "info")
        self.steps_text.config(state=tk.DISABLED)
        
        button_frame = tk.Frame(content, bg=self.colors["card"])
        button_frame.pack(fill=tk.X)
        tk.Button(button_frame, text="📋 Copy Report", command=self.copy_validation_report, font=("SF Pro Text", 10), fg="white", bg=self.colors["accent"], activebackground=self.colors["accent_hover"], bd=0, padx=15, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(button_frame, text="💾 Export Report", command=self.export_report, font=("SF Pro Text", 10), fg="white", bg=self.colors["success"], activebackground="#2e8b57", bd=0, padx=15, pady=6, cursor="hand2").pack(side=tk.LEFT)

    def create_console_card(self, parent):
        card, content = self.create_card(parent, "📟 Console Output", 10)
        console_frame = tk.Frame(content, bg=self.colors["console_bg"])
        console_frame.pack(fill=tk.BOTH, expand=True)
        self.console_text = tk.Text(console_frame, font=("SF Mono", 9), bg=self.colors["console_bg"], fg=self.colors["console_text"], wrap=tk.WORD, height=8, bd=0, relief=tk.FLAT)
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        console_scrollbar = tk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=console_scrollbar.set)
        self.console_text.tag_config("info", foreground="#51cf66")
        self.console_text.tag_config("error", foreground="#ff6b6b")
        self.console_text.tag_config("warning", foreground="#ffd43b")
        self.console_text.tag_config("output", foreground="#d4d4d4")
        self.console_text.tag_config("success", foreground="#00ff88")
        self.console_text.tag_config("timestamp", foreground="#888888")
        
        button_frame = tk.Frame(content, bg=self.colors["card"])
        button_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Button(button_frame, text="Clear", command=self.clear_console, font=("SF Pro Text", 9), fg=self.colors["text_dark"], bg=self.colors["bg"], bd=1, relief=tk.FLAT, padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(button_frame, text="Copy", command=self.copy_console, font=("SF Pro Text", 9), fg=self.colors["text_dark"], bg=self.colors["bg"], bd=1, relief=tk.FLAT, padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT)
        
        self.log("=" * 60, "output")
        self.log("MACOS INSTALLER VALIDATION CENTER READY", "success")
        self.log("=" * 60, "output")
        self.log("Select a macOS folder, .app installer, or InstallAssistant.pkg to begin", "output")

    def create_footer(self, parent):
        footer_frame = tk.Frame(parent, bg=self.colors["bg"])
        footer_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Button(footer_frame, text="Close", command=self.on_closing, font=("SF Pro Text", 11), fg=self.colors["text_dark"], bg=self.colors["bg"], activebackground="#e0e0e0", bd=1, relief=tk.FLAT, padx=30, pady=8, cursor="hand2").pack(side=tk.RIGHT)

    def reset_path(self):
        self.path_var.set("")
        self.validation_status.set("Ready - Select a folder to begin")
        self.status_label.config(fg=self.colors["text_light"])
        self.type_label.config(text="")
        self.badge_label.config(text="Not detected yet", fg=self.colors["text_light"])
        self.progress_value.set(0)
        self.progress_message.set("Path reset")
        for widget in self.files_frame.winfo_children(): widget.destroy()
        self.size_label.config(text="")
        self.current_result = None
        self.log("Path reset. Select a new folder to begin.", "info")

    def update_progress(self, current, total, message=""):
        def update():
            if total > 0: self.progress_value.set(int((current / total) * 100))
            if message: self.progress_message.set(message)
            self.root.update_idletasks()
        self.root.after(0, update)

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def insert():
            self.console_text.insert(tk.END, f"[{timestamp}]  ", "timestamp")
            self.console_text.insert(tk.END, f"{message}\n", level)
            self.console_text.see(tk.END)
            self.root.update_idletasks()
        self.root.after(0, insert)
        print(f"[{timestamp}] [{level.upper()}] {message}")

    def browse_path(self):
        initial_dir = self.path_var.get() if os.path.exists(self.path_var.get()) else os.path.expanduser("~")
        path = filedialog.askdirectory(title="Select macOS Folder", initialdir=initial_dir)
        if not path:
            path = filedialog.askopenfilename(title="Select macOS Installer (.app) or InstallAssistant.pkg", initialdir=initial_dir, filetypes=[("macOS Installer", "*.app"), ("Package", "*.pkg"), ("All Files", "*.*")])
        if path:
            self.path_var.set(path)
            self.log(f"Selected: {path}", "info")
            self.validate_path()

    def validate_path(self):
        if self.is_validating: self.log("Validation already in progress...", "warning"); return
        path = self.path_var.get().strip()
        if not path: self.validation_status.set("No path selected"); self.log("Please select a path first", "warning"); return
        if not os.path.exists(path): self.validation_status.set("Path does not exist"); self.log(f"Path does not exist: {path}", "error"); return
        
        self.is_validating = True
        self.validate_btn.config(state=tk.DISABLED, text="⏳ Scanning...")
        self.progress_value.set(0)
        self.progress_message.set("Starting scan...")
        self.validation_status.set("Scanning folder structure...")
        
        def validate():
            try:
                self.validator.select_path(path)
                result = self.validator.validate_folder(path)
                self.current_result = result
                def update_ui():
                    input_type = result.get("input_type", "unknown")
                    badge_text, badge_color = ("🟢 macOS Installer (.app)", self.colors["success"]) if input_type == "app" else (("🔵 InstallAssistant.pkg", self.colors["accent"]) if input_type == "pkg" else (("🟡 RAW macOS Folder (gibMacOS)", self.colors["warning"]) if input_type == "raw" else ("❓ Unknown Format", self.colors["error"])))
                    self.badge_label.config(text=badge_text, fg=badge_color)
                    self.type_label.config(text=f"Type: {dict(app='📦 macOS Installer (.app)', pkg='📦 InstallAssistant.pkg', raw='📁 RAW macOS Folder (gibMacOS)').get(input_type, '📁 Unknown')}", fg=self.colors["text_light"])
                    if result["valid"]:
                        self.validation_status.set("✅ Installer Validated & Ready")
                        self.status_label.config(fg=self.colors["success"])
                        files_text = "Found: " + ", ".join(result["found"]) + (f"\nOptional: {', '.join(result['optional_found'])}" if result["optional_found"] else "") if result["found"] else "Ready for use"
                        for widget in self.files_frame.winfo_children(): widget.destroy()
                        tk.Label(self.files_frame, text=files_text, font=("SF Pro Text", 10), fg=self.colors["success"], bg=self.colors["card"], anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W)
                        self.size_label.config(text=f"📁 Size: {result['folder_size_gb']} GB ({result['folder_size_mb']} MB)", fg=self.colors["text_light"])
                        self.update_next_steps_after_validation()
                        self.log(self.validator.get_scan_summary(), "output")
                    else:
                        self.validation_status.set(f"❌ {result['error']}")
                        self.status_label.config(fg=self.colors["error"])
                        for widget in self.files_frame.winfo_children(): widget.destroy()
                        self.size_label.config(text="")
                        self.log(f"Validation failed: {result['error']}", "error")
                    self.progress_value.set(100)
                    self.progress_message.set("Validation complete")
                    self.validate_btn.config(state=tk.NORMAL, text="🔍 Scan & Validate")
                    self.is_validating = False
                self.root.after(0, update_ui)
            except Exception as e:
                def error_ui():
                    self.log(f"Validation error: {e}", "error")
                    self.validation_status.set(f"❌ Error: {str(e)[:50]}")
                    self.validate_btn.config(state=tk.NORMAL, text="🔍 Scan & Validate")
                    self.is_validating = False
                    self.progress_message.set("Validation failed")
                self.root.after(0, error_ui)
        threading.Thread(target=validate, daemon=True).start()

    def update_next_steps_after_validation(self):
        self.steps_text.config(state=tk.NORMAL)
        self.steps_text.delete(1.0, tk.END)
        self.steps_text.insert(tk.END, "VALIDATION COMPLETE\n\n", "title")
        self.steps_text.insert(tk.END, "• Files verified and ready\n", "step")
        self.steps_text.insert(tk.END, "• Structure validated\n", "step")
        self.steps_text.insert(tk.END, "• No corruption detected\n", "step")
        self.steps_text.insert(tk.END, "\nResources can now be used in your workflow.\n", "info")
        self.steps_text.config(state=tk.DISABLED)

    def copy_validation_report(self):
        if self.current_result:
            report = f"""ZEMmacOS Validation Report
========================
Path: {self.path_var.get()}
Type: {self.current_result.get('input_type', 'Unknown')}
Status: {'Valid' if self.current_result.get('valid') else 'Invalid'}
Size: {self.current_result.get('folder_size_gb', 0):.2f} GB
Found: {', '.join(self.current_result.get('found', []))}
"""
            self.root.clipboard_clear()
            self.root.clipboard_append(report)
            self.log("Validation report copied to clipboard", "info")
            self.validation_status.set("📋 Report copied to clipboard!")

    def export_report(self):
        if not self.current_result: messagebox.showwarning("No Report", "Please validate a path first"); return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")], initialfile="ZEMmacOS_Validation_Report.txt")
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(f"ZEMmacOS Validation Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n\n")
                    f.write(f"Path: {self.path_var.get()}\nType: {self.current_result.get('input_type', 'Unknown')}\nStatus: {'Valid' if self.current_result.get('valid') else 'Invalid'}\n")
                    f.write(f"Size: {self.current_result.get('folder_size_gb', 0):.2f} GB\nFound Files: {', '.join(self.current_result.get('found', []))}\n")
                    if self.current_result.get('missing'): f.write(f"Missing Files: {', '.join(self.current_result.get('missing', []))}\n")
                self.log(f"Report exported to: {file_path}", "success")
                messagebox.showinfo("Exported", f"Report saved to:\n{file_path}")
            except Exception as e: self.log(f"Export failed: {e}", "error"); messagebox.showerror("Error", f"Failed to export report:\n{e}")

    def copy_console(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.console_text.get(1.0, tk.END))
        self.log("Console content copied to clipboard", "info")

    def open_path(self):
        path = self.path_var.get()
        if path and os.path.exists(path):
            if sys.platform == "win32": os.startfile(os.path.dirname(path) if os.path.isfile(path) else path)
            self.log(f"Opened: {path}", "info")
        else: self.log("No valid path selected", "warning")

    def clear_console(self):
        self.console_text.delete(1.0, tk.END)
        self.log("Console cleared", "info")

    def on_closing(self):
        if self._is_modal:
            try: self.root.grab_release()
            except: pass
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    app = USBCreatorUI()
    app.run()

def run_as_modal(parent_window):
    app = USBCreatorUI(parent_window=parent_window)
    app.run()

if __name__ == "__main__":
    main()