"""Universal Email Dialog - single email form reused by every request flow
(Support, Sales, Generate Request, ...) inside the Universal License Center.

Matches the platform's UniversalEmailDialog contract:
- Automatically populates Customer Name, Customer Email, Product, Plan,
  License Key and Hardware ID from the engine status.
- Attachment upload (max 5 files, 10 MB each) via the public attach API.
- Rich message editor (subject + formatted message + character counter).
- Universal validation via FieldIndicator (email, required fields, limits).
"""
import os
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, font as tkfont

from .live_log import LiveLog
from .validation import FieldIndicator, is_valid_email

MAX_ATTACHMENTS = 5
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (matches backend)

__all__ = ["UniversalEmailDialog", "MAX_ATTACHMENTS", "MAX_FILE_SIZE"]


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if (value >= 10 or unit == "B") else f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


class _AttachedFile:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        try:
            self.size = os.path.getsize(path)
        except OSError:
            self.size = 0


class UniversalEmailDialog:
    """One email component for all request categories.

    Receives the owning UniversalLicenseCenter so it can reuse the engine,
    hardware detector, cached status (auto-fill) and the center's theme.
    """

    def __init__(self, center: Any, title: str, category: str,
                 parent: Optional[tk.Widget] = None):
        self._center = center
        self._title = title
        self._category = category
        self._parent = parent or getattr(center, '_root', None)
        self._engine = center.engine
        self._hardware = center.hardware
        self._status = getattr(center, '_status', None)

        self._primary = center._primary
        self._bg = center._bg
        self._card_bg = center._card_bg
        self._text_primary = center._text_primary
        self._text_secondary = center._text_secondary
        self._success = center._success
        self._error = center._error
        self._warning = center._warning
        self._border = center._border
        self._product_name = center._product_name

        self._files: List[_AttachedFile] = []
        self._dialog: Optional[tk.Toplevel] = None

    # ------------------------------------------------------------------
    # Logging helpers (reuse the center's logger)
    # ------------------------------------------------------------------
    def _log(self, category: str, level: str, message: str, detail: Optional[str] = None):
        LiveLog.log(f"[{category}] [{level}] {message}", detail)
        log_fn = getattr(self._center, '_log', None)
        if log_fn:
            try:
                log_fn(category, level, message, detail)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Auto-fill values (read-only, from the engine status)
    # ------------------------------------------------------------------
    def _auto_values(self) -> Dict[str, str]:
        status = self._status
        display_key = ""
        if status and status.license_key:
            key = status.license_key
            display_key = key[:8] + "..." if len(key) > 8 else key
        return {
            "customer_name": status.customer_name if status else "",
            "customer_email": status.customer_email if status else "",
            "product": self._product_name or (status.product_name if status else ""),
            "plan": status.plan if status else "",
            "license_key": display_key,
            "hardware_id": self._hardware.get_fingerprint(),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def show(self) -> None:
        dialog = tk.Toplevel(self._parent)
        dialog.title(self._title)
        dialog.geometry("680x720")
        dialog.minsize(620, 640)
        dialog.configure(bg=self._bg)
        dialog.resizable(True, True)
        if self._parent is not None:
            dialog.transient(self._parent)
        dialog.grab_set()
        self._dialog = dialog

        auto = self._auto_values()

        header = tk.Frame(dialog, bg=self._primary, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self._title,
                 font=("Segoe UI", 18, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        main = tk.Frame(dialog, bg=self._card_bg, padx=22, pady=14)
        main.pack(fill="both", expand=True)

        # ---------------- Customer info section ----------------
        info = tk.LabelFrame(main, text="Customer Information",
                             font=("Segoe UI", 10, "bold"),
                             bg=self._card_bg, fg=self._text_secondary,
                             bd=0, highlightthickness=1,
                             highlightbackground=self._border,
                             padx=12, pady=8)
        info.pack(fill="x")

        self._name_var = tk.StringVar(value=auto["customer_name"])
        self._email_var = tk.StringVar(value=auto["customer_email"])

        name_row = tk.Frame(info, bg=self._card_bg)
        name_row.pack(fill="x", pady=2)
        tk.Label(name_row, text="Name:", font=("Segoe UI", 10),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=14, anchor="w").pack(side="left")
        tk.Entry(name_row, font=("Segoe UI", 10), relief="solid", bd=1,
                 textvariable=self._name_var).pack(side="left", fill="x", expand=True)

        email_row = tk.Frame(info, bg=self._card_bg)
        email_row.pack(fill="x", pady=2)
        tk.Label(email_row, text="Email:", font=("Segoe UI", 10),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=14, anchor="w").pack(side="left")
        email_entry = tk.Entry(email_row, font=("Segoe UI", 10), relief="solid", bd=1,
                               textvariable=self._email_var)
        email_entry.pack(side="left", fill="x", expand=True)
        indicator_label = tk.Label(email_row, text="", font=("Segoe UI", 11, "bold"),
                                   bg=self._card_bg, fg=self._success)
        indicator_label.pack(side="left", padx=(6, 0))
        self._email_indicator = FieldIndicator(indicator_label,
                                               success_color=self._success,
                                               error_color=self._error)

        def _update_email_indicator(_event=None):
            value = self._email_var.get().strip()
            if not value:
                self._email_indicator.clear()
            elif is_valid_email(value):
                self._email_indicator.set_valid()
            else:
                self._email_indicator.set_invalid()

        email_entry.bind("<KeyRelease>", _update_email_indicator)
        _update_email_indicator()

        for label, value in (("Product", auto["product"]),
                             ("Plan", auto["plan"]),
                             ("License Key", auto["license_key"])):
            row = tk.Frame(info, bg=self._card_bg)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", 10),
                     fg=self._text_secondary, bg=self._card_bg,
                     width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value or "—", font=("Segoe UI", 10, "bold"),
                     fg=self._text_primary, bg=self._card_bg,
                     anchor="w").pack(side="left", fill="x", expand=True)

        hw_row = tk.Frame(info, bg=self._card_bg)
        hw_row.pack(fill="x", pady=1)
        tk.Label(hw_row, text="Hardware ID:", font=("Segoe UI", 10),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=14, anchor="w").pack(side="left")
        hw_value = auto["hardware_id"]
        tk.Label(hw_row, text=(hw_value[:16] + "..." if len(hw_value) > 16 else hw_value),
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg,
                 anchor="w").pack(side="left", fill="x", expand=True)

        # ---------------- Subject ----------------
        tk.Label(main, text="Subject:", font=("Segoe UI", 10),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor="w", pady=(10, 3))
        self._subject_var = tk.StringVar()
        tk.Entry(main, font=("Segoe UI", 10), relief="solid", bd=1,
                 textvariable=self._subject_var).pack(fill="x")

        # ---------------- Message (rich editor) ----------------
        tk.Label(main, text="Message:", font=("Segoe UI", 10),
                 fg=self._text_primary, bg=self._card_bg).pack(anchor="w", pady=(10, 3))

        editor_frame = tk.Frame(main, bg=self._card_bg)
        editor_frame.pack(fill="both", expand=True)

        toolbar = tk.Frame(editor_frame, bg=self._card_bg)
        toolbar.pack(fill="x", pady=(0, 4))

        self._msg_text = tk.Text(editor_frame, font=("Segoe UI", 11),
                                 relief="solid", bd=1, wrap="word",
                                 height=9, undo=True)
        self._msg_text.pack(fill="both", expand=True)

        rich_font = tkfont.Font(font=("Segoe UI", 11))
        self._msg_text.tag_configure("bold", font=rich_font.copy() ** {"weight": "bold"})
        self._msg_text.tag_configure("italic", font=rich_font.copy() ** {"slant": "italic"})
        self._msg_text.tag_configure("underline",
                                     font=rich_font.copy() ** {"underline": True})

        self._bold_on = tk.BooleanVar(value=False)
        self._italic_on = tk.BooleanVar(value=False)
        self._underline_on = tk.BooleanVar(value=False)

        def _toggle_style(tag: str, var: tk.BooleanVar):
            var.set(not var.get())
            try:
                if var.get():
                    self._msg_text.tag_add(tag, "sel.first", "sel.last")
                else:
                    self._msg_text.tag_remove(tag, "sel.first", "sel.last")
            except tk.TclError:
                pass

        tk.Checkbutton(toolbar, text="B", variable=self._bold_on, width=3,
                       command=lambda: _toggle_style("bold", self._bold_on),
                       font=("Segoe UI", 11, "bold"),
                       bg=self._card_bg, fg=self._text_primary,
                       activebackground=self._card_bg).pack(side="left", padx=(0, 4))
        tk.Checkbutton(toolbar, text="I", variable=self._italic_on, width=3,
                       command=lambda: _toggle_style("italic", self._italic_on),
                       font=("Segoe UI", 11, "italic"),
                       bg=self._card_bg, fg=self._text_primary,
                       activebackground=self._card_bg).pack(side="left", padx=(0, 4))
        tk.Checkbutton(toolbar, text="U", variable=self._underline_on, width=3,
                       command=lambda: _toggle_style("underline", self._underline_on),
                       font=("Segoe UI", 11, "underline"),
                       bg=self._card_bg, fg=self._text_primary,
                       activebackground=self._card_bg).pack(side="left", padx=(0, 4))

        self._char_label = tk.Label(toolbar, text="0 characters",
                                    font=("Segoe UI", 9), fg=self._text_secondary,
                                    bg=self._card_bg)
        self._char_label.pack(side="right")

        def _update_char_count(_event=None):
            length = len(self._msg_text.get("1.0", "end-1c"))
            self._char_label.config(text=f"{length} characters")

        self._msg_text.bind("<KeyRelease>", _update_char_count)

        # ---------------- Attachments ----------------
        attach_frame = tk.LabelFrame(main, text="Attachments (max 5, 10 MB each)",
                                     font=("Segoe UI", 10, "bold"),
                                     bg=self._card_bg, fg=self._text_secondary,
                                     bd=0, highlightthickness=1,
                                     highlightbackground=self._border,
                                     padx=12, pady=6)
        attach_frame.pack(fill="x", pady=(10, 0))

        attach_header = tk.Frame(attach_frame, bg=self._card_bg)
        attach_header.pack(fill="x")
        tk.Label(attach_header, text="No files attached", font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg).pack(side="left")
        tk.Button(attach_header, text="Add files",
                  font=("Segoe UI", 9, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=10, pady=2, cursor="hand2",
                  command=self._pick_files).pack(side="right")

        self._attach_list = tk.Frame(attach_frame, bg=self._card_bg)
        self._attach_list.pack(fill="x", pady=(4, 0))

        # ---------------- Status + actions ----------------
        self._status_label = tk.Label(main, text="", font=("Segoe UI", 10),
                                      bg=self._card_bg, fg=self._success,
                                      wraplength=600, justify="left")
        self._status_label.pack(fill="x", pady=(8, 0))

        btn_frame = tk.Frame(main, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(8, 0))
        tk.Button(btn_frame, text="Send", command=self._do_send,
                  font=("Segoe UI", 12, "bold"),
                  bg=self._primary, fg="white", relief="flat",
                  padx=20, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))
        tk.Button(btn_frame, text="Cancel",
                  font=("Segoe UI", 11),
                  bg="#e5e7eb", fg=self._text_primary, relief="flat",
                  command=self._close, cursor="hand2",
                  padx=12, pady=4).pack(fill="x")

        dialog.wait_window()

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------
    def _pick_files(self):
        paths = filedialog.askopenfilenames(parent=self._dialog,
                                            title="Attach files (max 5, 10 MB each)")
        for path in paths:
            if len(self._files) >= MAX_ATTACHMENTS:
                self._set_status(f"Maximum {MAX_ATTACHMENTS} attachments allowed.",
                                 self._error)
                break
            if os.path.getsize(path) > MAX_FILE_SIZE:
                self._set_status(f"File exceeds 10 MB limit: {os.path.basename(path)}",
                                 self._error)
                continue
            if any(f.path == path for f in self._files):
                continue
            self._files.append(_AttachedFile(path))
        self._render_attachments()

    def _remove_file(self, file_obj: _AttachedFile):
        self._files = [f for f in self._files if f is not file_obj]
        self._render_attachments()

    def _render_attachments(self):
        for child in self._attach_list.winfo_children():
            child.destroy()
        header_label = self._attach_list.master
        if not self._files:
            self._attach_list.pack_forget()
            header_label.winfo_children()[0].config(text="No files attached")
            return
        header_label.winfo_children()[0].config(
            text=f"{len(self._files)}/{MAX_ATTACHMENTS} files attached")
        self._attach_list.pack(fill="x", pady=(4, 0))
        for file_obj in self._files:
            row = tk.Frame(self._attach_list, bg=self._card_bg)
            row.pack(fill="x", pady=1)
            tk.Label(row, text="📎", font=("Segoe UI", 10),
                     bg=self._card_bg).pack(side="left")
            tk.Label(row, text=file_obj.name, font=("Segoe UI", 9),
                     fg=self._text_primary, bg=self._card_bg,
                     anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(row, text=_format_size(file_obj.size), font=("Segoe UI", 8),
                     fg=self._text_secondary, bg=self._card_bg).pack(side="right")
            tk.Button(row, text="×", font=("Segoe UI", 9, "bold"),
                      bg=self._card_bg, fg=self._error, relief="flat",
                      cursor="hand2",
                      command=lambda f=file_obj: self._remove_file(f)).pack(side="right")

    # ------------------------------------------------------------------
    # Validation + send
    # ------------------------------------------------------------------
    def _set_status(self, text: str, color: str):
        self._status_label.config(text=text, fg=color)

    def _validate(self) -> Optional[Dict[str, str]]:
        name = self._name_var.get().strip()
        email = self._email_var.get().strip()
        subject = self._subject_var.get().strip()
        message = self._msg_text.get("1.0", "end-1c").strip()
        if not name:
            self._set_status("Please enter your name", self._error)
            return None
        if not is_valid_email(email):
            self._set_status("Please enter a valid email address", self._error)
            self._email_indicator.set_invalid()
            return None
        if not subject:
            self._set_status("Please enter a subject", self._error)
            return None
        if not message:
            self._set_status("Please enter a message", self._error)
            return None
        return {"name": name, "email": email,
                "subject": subject, "message": message}

    def _do_send(self):
        if self._dialog is None:
            return
        values = self._validate()
        if values is None:
            return
        status = self._status
        self._set_status("Sending...", self._text_secondary)
        try:
            LiveLog.log(f"Sending {self._category} request",
                        f"Category: {self._category}")
            result = self._engine.create_communication(
                category=self._category,
                customer_email=values["email"],
                customer_name=values["name"],
                subject=values["subject"],
                message=values["message"],
                license_key=status.license_key if status else '',
                hardware_id=self._hardware.get_fingerprint(),
            )
            if not result.get('success'):
                if result.get('queued'):
                    self._set_status("Message queued - will send when online.",
                                     self._warning)
                    self._dialog.after(1800, self._close)
                else:
                    err = result.get('message', 'Failed to send message')
                    self._set_status(str(err), self._error)
                return

            conversation_id = result.get('conversation_id', '')
            if conversation_id and self._files:
                self._upload_attachments(conversation_id)
            self._set_status("Message sent successfully!", self._success)
            LiveLog.log(f"{self._category} request sent",
                        f"Conversation: {conversation_id or 'n/a'}")
            self._dialog.after(1500, self._close)
        except Exception as e:
            LiveLog.log(f"{self._category} request error", str(e))
            self._set_status(str(e), self._error)

    def _upload_attachments(self, conversation_id: str):
        for file_obj in self._files:
            try:
                upload = self._engine._client.upload_attachment(
                    conversation_id, file_obj.path)
                if not upload.get('success'):
                    self._log("ATTACHMENT", "WARNING",
                              f"Attachment {file_obj.name} upload failed",
                              upload.get('error', {}).get('message'))
            except Exception as e:
                self._log("ATTACHMENT", "ERROR",
                          f"Attachment {file_obj.name} upload failed", str(e))

    def _close(self):
        if self._dialog is not None:
            try:
                self._dialog.destroy()
            except Exception:
                pass
            self._dialog = None
