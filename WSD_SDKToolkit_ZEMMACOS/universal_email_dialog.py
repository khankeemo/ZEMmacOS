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
        self._status_dot: Optional[tk.Canvas] = None
        self._status_text_label: Optional[tk.Label] = None

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
            "customer_company": getattr(status, 'customer_company', '') if status else "",
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
        dialog.geometry("1100x820")
        dialog.minsize(980, 720)
        dialog.configure(bg=self._bg)
        dialog.resizable(True, True)
        if self._parent is not None:
            dialog.transient(self._parent)
        dialog.grab_set()
        self._dialog = dialog

        auto = self._auto_values()

        # ---- Title Bar ----
        title_frame = tk.Frame(dialog, bg=self._primary, height=52)
        title_frame.pack(fill="x", side="top")
        title_frame.pack_propagate(False)

        title_inner = tk.Frame(title_frame, bg=self._primary)
        title_inner.pack(fill="both", padx=20, pady=10)

        # Title left
        tk.Label(title_inner, text="📧 " + self._title,
                 font=("Segoe UI", 14, "bold"),
                 fg="white", bg=self._primary).pack(side="left")

        # Status indicator (center-right)
        status_frame = tk.Frame(title_inner, bg=self._primary)
        status_frame.pack(side="right", padx=(0, 10))

        self._status_dot = tk.Canvas(status_frame, width=10, height=10,
                                     bg=self._primary, highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 6))
        self._status_dot.create_oval(2, 2, 8, 8, fill=self._success, outline="")

        self._status_text_label = tk.Label(status_frame, text="Ready",
                                           font=("Segoe UI", 10),
                                           fg="white", bg=self._primary)
        self._status_text_label.pack(side="left")

        # Close button
        close_btn = tk.Label(title_inner, text="✕", font=("Segoe UI", 16, "bold"),
                             fg="white", bg=self._primary, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff6b6b"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="white"))

        # ---- Main Container (2-column) ----
        main_container = tk.Frame(dialog, bg=self._bg)
        main_container.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        # Left column (Customer Info + Attachments)
        left_col = tk.Frame(main_container, bg=self._bg)
        left_col.pack(side="left", fill="both", expand=False, padx=(0, 10))

        # Right column (Subject + Editor)
        right_col = tk.Frame(main_container, bg=self._bg)
        right_col.pack(side="left", fill="both", expand=True)

        # ---- Left Column: Customer Information Card ----
        info_card = tk.Frame(left_col, bg=self._card_bg,
                             highlightthickness=1, highlightbackground=self._border,
                             relief="flat")
        info_card.pack(fill="x", pady=(0, 10))

        # Card header
        info_header = tk.Frame(info_card, bg=self._card_bg, height=34)
        info_header.pack(fill="x", padx=14, pady=(6, 0))
        info_header.pack_propagate(False)

        tk.Label(info_header, text="Customer Information",
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        # Info grid
        info_grid = tk.Frame(info_card, bg=self._card_bg)
        info_grid.pack(fill="x", padx=14, pady=(4, 12))

        self._name_var = tk.StringVar(value=auto["customer_name"])
        self._email_var = tk.StringVar(value=auto["customer_email"])
        self._company_var = tk.StringVar(value=auto["customer_company"])

        # Field definitions: (label, icon, variable, readonly)
        info_fields = [
            ("Name", "👤", self._name_var, False),
            ("Email", "✉", self._email_var, False),
            ("Company", "🏢", self._company_var, False),
            ("Product", "📦", tk.StringVar(value=auto["product"]), True),
            ("Plan", "📋", tk.StringVar(value=auto["plan"]), True),
            ("License", "🔑", tk.StringVar(value=auto["license_key"]), True),
        ]

        for i, (label, icon, var, readonly) in enumerate(info_fields):
            row = tk.Frame(info_grid, bg=self._card_bg)
            row.pack(fill="x", pady=2)

            # Icon + Label
            label_w = tk.Label(row, text=f"{icon} {label}:",
                               font=("Segoe UI", 9),
                               fg=self._text_secondary, bg=self._card_bg,
                               width=12, anchor="e")
            label_w.pack(side="left", padx=(0, 6))

            if readonly:
                entry = tk.Entry(row, font=("Segoe UI", 9),
                                 relief="solid", bd=1,
                                 bg="#f3f4f6", fg=self._text_primary,
                                 state="readonly", readonlybackground="#f3f4f6")
                entry.configure(textvariable=var)
                entry.pack(side="left", fill="x", expand=True)
            else:
                entry = tk.Entry(row, font=("Segoe UI", 9),
                                 relief="solid", bd=1,
                                 bg="white", fg=self._text_primary,
                                 textvariable=var)
                entry.pack(side="left", fill="x", expand=True)

                if label == "Email":
                    indicator_label = tk.Label(row, text="", font=("Segoe UI", 9, "bold"),
                                               bg=self._card_bg, fg=self._success)
                    indicator_label.pack(side="left", padx=(4, 0))
                    self._email_indicator = FieldIndicator(indicator_label,
                                                           success_color=self._success,
                                                           error_color=self._error)

                    def _update_email_indicator(_event=None):
                        value = self._email_var.get().strip()
                        if not value:
                            self._email_indicator.clear()
                            self._email_indicator._label.config(text="")
                        elif is_valid_email(value):
                            self._email_indicator.set_valid()
                            self._email_indicator._label.config(text="✓")
                        else:
                            self._email_indicator.set_invalid()
                            self._email_indicator._label.config(text="✗")

                    entry.bind("<KeyRelease>", _update_email_indicator)
                    _update_email_indicator()

        # Hardware ID (special case - truncated display)
        hw_row = tk.Frame(info_grid, bg=self._card_bg)
        hw_row.pack(fill="x", pady=2)
        tk.Label(hw_row, text="🖥 Hardware ID:",
                 font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=12, anchor="e").pack(side="left", padx=(0, 6))
        hw_value = auto["hardware_id"]
        hw_display = hw_value[:14] + "..." if len(hw_value) > 14 else hw_value
        tk.Label(hw_row, text=hw_display,
                 font=("Segoe UI", 9),
                 fg=self._text_primary, bg="#f3f4f6",
                 relief="solid", bd=1, anchor="w",
                 padx=4, pady=3).pack(side="left", fill="x", expand=True)

        # ---- Left Column: Attachments Card ----
        attach_card = tk.Frame(left_col, bg=self._card_bg,
                               highlightthickness=1, highlightbackground=self._border,
                               relief="flat")
        attach_card.pack(fill="both", expand=True)

        attach_inner = tk.Frame(attach_card, bg=self._card_bg)
        attach_inner.pack(fill="both", expand=True, padx=14, pady=10)

        attach_header = tk.Frame(attach_inner, bg=self._card_bg)
        attach_header.pack(fill="x", pady=(0, 6))

        tk.Label(attach_header, text="📎 Attachments",
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        add_btn = tk.Button(attach_header, text="+ Add",
                            font=("Segoe UI", 8, "bold"),
                            bg=self._primary, fg="white",
                            relief="flat", padx=10, pady=2,
                            cursor="hand2",
                            command=self._pick_files)
        add_btn.pack(side="right")
        add_btn.bind("<Enter>", lambda e, b=add_btn: b.config(bg=self._text_primary))
        add_btn.bind("<Leave>", lambda e, b=add_btn: b.config(bg=self._primary))

        self._attach_count = tk.Label(attach_header,
                                      text="0/5",
                                      font=("Segoe UI", 8),
                                      fg=self._text_secondary, bg=self._card_bg)
        self._attach_count.pack(side="right", padx=(0, 8))

        # Attachments list (scrollable)
        attach_scroll = tk.Frame(attach_inner, bg=self._card_bg)
        attach_scroll.pack(fill="both", expand=True)

        self._attach_list = tk.Frame(attach_scroll, bg=self._card_bg)
        self._attach_list.pack(fill="both", expand=True)
        
        self._render_attachments()

        # ---- Right Column: Subject ----
        subject_frame = tk.Frame(right_col, bg=self._card_bg,
                                 highlightthickness=1, highlightbackground=self._border,
                                 relief="flat")
        subject_frame.pack(fill="x", pady=(0, 8))

        subject_inner = tk.Frame(subject_frame, bg=self._card_bg)
        subject_inner.pack(fill="x", padx=14, pady=8)

        tk.Label(subject_inner, text="Subject",
                 font=("Segoe UI", 9, "bold"),
                 fg=self._text_primary, bg=self._card_bg,
                 anchor="w").pack(fill="x", pady=(0, 2))

        self._subject_var = tk.StringVar()
        subject_entry = tk.Entry(subject_inner, font=("Segoe UI", 10),
                                 relief="solid", bd=1,
                                 bg="white", fg=self._text_primary,
                                 textvariable=self._subject_var)
        subject_entry.pack(fill="x", ipady=4)

        # ---- Right Column: Editor (scrollable) ----
        editor_card = tk.Frame(right_col, bg=self._card_bg,
                               highlightthickness=1, highlightbackground=self._border,
                               relief="flat")
        editor_card.pack(fill="both", expand=True)

        editor_inner = tk.Frame(editor_card, bg=self._card_bg)
        editor_inner.pack(fill="both", expand=True, padx=14, pady=8)

        # Editor header with char count
        editor_header = tk.Frame(editor_inner, bg=self._card_bg)
        editor_header.pack(fill="x", pady=(0, 4))

        tk.Label(editor_header, text="Message",
                 font=("Segoe UI", 9, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        self._char_label = tk.Label(editor_header, text="0 / 5000",
                                    font=("Segoe UI", 8),
                                    fg=self._text_secondary, bg=self._card_bg)
        self._char_label.pack(side="right")

        # Toolbar
        toolbar = tk.Frame(editor_inner, bg=self._card_bg, height=30)
        toolbar.pack(fill="x", pady=(0, 4))
        toolbar.pack_propagate(False)

        # Editor text area (with scrollbar)
        editor_text_frame = tk.Frame(editor_inner, bg=self._card_bg)
        editor_text_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(editor_text_frame)
        scrollbar.pack(side="right", fill="y")

        self._msg_text = tk.Text(editor_text_frame, font=("Segoe UI", 10),
                                 relief="solid", bd=1, wrap="word",
                                 yscrollcommand=scrollbar.set,
                                 bg="white", fg=self._text_primary)
        self._msg_text.pack(fill="both", expand=True)
        scrollbar.config(command=self._msg_text.yview)

        # Rich text tags
        self._msg_text.tag_configure("bold", font=tkfont.Font(font=("Segoe UI", 10, "bold")))
        self._msg_text.tag_configure("italic", font=tkfont.Font(font=("Segoe UI", 10, "italic")))
        self._msg_text.tag_configure("underline",
                                     font=tkfont.Font(font=("Segoe UI", 10, "underline")))

        # Toolbar buttons
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

        def _apply_bullet():
            try:
                sel_start = self._msg_text.index("sel.first")
                sel_end = self._msg_text.index("sel.last")
                lines = self._msg_text.get(sel_start, sel_end).split('\n')
                if lines:
                    line_start = sel_start.split('.')[0] + ".0"
                    current_text = self._msg_text.get(line_start, sel_end)
                    lines = current_text.split('\n')
                    bulleted = ['• ' + line if line.strip() else line for line in lines]
                    self._msg_text.delete(line_start, sel_end)
                    self._msg_text.insert(line_start, '\n'.join(bulleted))
            except tk.TclError:
                pass

        def _apply_numbered():
            try:
                sel_start = self._msg_text.index("sel.first")
                sel_end = self._msg_text.index("sel.last")
                line_start = sel_start.split('.')[0] + ".0"
                current_text = self._msg_text.get(line_start, sel_end)
                lines = current_text.split('\n')
                numbered = [f"{i+1}. {line}" if line.strip() else line for i, line in enumerate(lines)]
                self._msg_text.delete(line_start, sel_end)
                self._msg_text.insert(line_start, '\n'.join(numbered))
            except tk.TclError:
                pass

        def _insert_link():
            # Future-ready: placeholder for link insertion
            pass

        # Toolbar button config
        button_config = {
            'font': ("Segoe UI", 9, "bold"),
            'bg': self._card_bg,
            'fg': self._text_secondary,
            'relief': "flat",
            'padx': 6,
            'pady': 1,
            'cursor': "hand2",
            'width': 3
        }

        btn_bold = tk.Button(toolbar, text="B", command=lambda: _toggle_style("bold", self._bold_on),
                            **button_config)
        btn_bold.pack(side="left", padx=(0, 1))
        btn_bold.bind("<Enter>", lambda e, b=btn_bold: b.config(bg="#e5e7eb"))
        btn_bold.bind("<Leave>", lambda e, b=btn_bold: b.config(bg=self._card_bg))

        btn_italic = tk.Button(toolbar, text="I", command=lambda: _toggle_style("italic", self._italic_on),
                              font=("Segoe UI", 9, "italic"), **button_config)
        btn_italic.pack(side="left", padx=1)
        btn_italic.bind("<Enter>", lambda e, b=btn_italic: b.config(bg="#e5e7eb"))
        btn_italic.bind("<Leave>", lambda e, b=btn_italic: b.config(bg=self._card_bg))

        btn_underline = tk.Button(toolbar, text="U", command=lambda: _toggle_style("underline", self._underline_on),
                                 font=("Segoe UI", 9, "underline"), **button_config)
        btn_underline.pack(side="left", padx=1)
        btn_underline.bind("<Enter>", lambda e, b=btn_underline: b.config(bg="#e5e7eb"))
        btn_underline.bind("<Leave>", lambda e, b=btn_underline: b.config(bg=self._card_bg))

        tk.Frame(toolbar, width=1, bg=self._border).pack(side="left", padx=4, fill="y", pady=2)

        btn_bullet = tk.Button(toolbar, text="•", command=_apply_bullet,
                              **button_config)
        btn_bullet.pack(side="left", padx=1)
        btn_bullet.bind("<Enter>", lambda e, b=btn_bullet: b.config(bg="#e5e7eb"))
        btn_bullet.bind("<Leave>", lambda e, b=btn_bullet: b.config(bg=self._card_bg))

        btn_numbered = tk.Button(toolbar, text="1.", command=_apply_numbered,
                               **button_config)
        btn_numbered.pack(side="left", padx=1)
        btn_numbered.bind("<Enter>", lambda e, b=btn_numbered: b.config(bg="#e5e7eb"))
        btn_numbered.bind("<Leave>", lambda e, b=btn_numbered: b.config(bg=self._card_bg))

        btn_link = tk.Button(toolbar, text="🔗", command=_insert_link,
                           **button_config)
        btn_link.pack(side="left", padx=1)
        btn_link.bind("<Enter>", lambda e, b=btn_link: b.config(bg="#e5e7eb"))
        btn_link.bind("<Leave>", lambda e, b=btn_link: b.config(bg=self._card_bg))

        tk.Frame(toolbar, width=1, bg=self._border).pack(side="left", padx=4, fill="y", pady=2)

        btn_undo = tk.Button(toolbar, text="↩", command=lambda: self._msg_text.edit_undo(),
                           **button_config)
        btn_undo.pack(side="left", padx=1)
        btn_undo.bind("<Enter>", lambda e, b=btn_undo: b.config(bg="#e5e7eb"))
        btn_undo.bind("<Leave>", lambda e, b=btn_undo: b.config(bg=self._card_bg))

        btn_redo = tk.Button(toolbar, text="↪", command=lambda: self._msg_text.edit_redo(),
                            **button_config)
        btn_redo.pack(side="left", padx=1)
        btn_redo.bind("<Enter>", lambda e, b=btn_redo: b.config(bg="#e5e7eb"))
        btn_redo.bind("<Leave>", lambda e, b=btn_redo: b.config(bg=self._card_bg))

        # Font Family dropdown
        font_families = ["Segoe UI", "Arial", "Helvetica", "Times New Roman", "Courier New", "Georgia"]
        self._font_family_var = tk.StringVar(value=font_families[0])
        font_family_menu = tk.OptionMenu(toolbar, self._font_family_var, *font_families,
                                         command=self._apply_font_family)
        font_family_btn = font_family_menu.nametowidget(font_family_menu.children['menu'])
        font_family_btn.config(**button_config, text="⬇")
        font_family_btn.pack(side="left", padx=1)
        font_family_btn.bind("<Enter>", lambda e, b=font_family_btn: b.config(bg="#e5e7eb"))
        font_family_btn.bind("<Leave>", lambda e, b=font_family_btn: b.config(bg=self._card_bg))

        # Font Size dropdown
        font_sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "30", "36", "48"]
        self._font_size_var = tk.StringVar(value="10")
        font_size_menu = tk.OptionMenu(toolbar, self._font_size_var, *font_sizes,
                                       command=self._apply_font_size)
        font_size_btn = font_size_menu.nametowidget(font_size_menu.children['menu'])
        font_size_btn.config(**button_config, text="⬇")
        font_size_btn.pack(side="left", padx=1)
        font_size_btn.bind("<Enter>", lambda e, b=font_size_btn: b.config(bg="#e5e7eb"))
        font_size_btn.bind("<Leave>", lambda e, b=font_size_btn: b.config(bg=self._card_bg))

        # Text Color button
        btn_color = tk.Button(toolbar, text="🎨", command=self._apply_text_color,
                             **button_config)
        btn_color.pack(side="left", padx=1)
        btn_color.bind("<Enter>", lambda e, b=btn_color: b.config(bg="#e5e7eb"))
        btn_color.bind("<Leave>", lambda e, b=btn_color: b.config(bg=self._card_bg))

        # Highlight Color button
        btn_highlight = tk.Button(toolbar, text="🔆", command=self._apply_highlight_color,
                                 **button_config)
        btn_highlight.pack(side="left", padx=1)
        btn_highlight.bind("<Enter>", lambda e, b=btn_highlight: b.config(bg="#e5e7eb"))
        btn_highlight.bind("<Leave>", lambda e, b=btn_highlight: b.config(bg=self._card_bg))

        # Emoji button
        btn_emoji = tk.Button(toolbar, text="😀", command=self._apply_emoji,
                            **button_config)
        btn_emoji.pack(side="left", padx=1)
        btn_emoji.bind("<Enter>", lambda e, b=btn_emoji: b.config(bg="#e5e7eb"))
        btn_emoji.bind("<Leave>", lambda e, b=btn_emoji: b.config(bg=self._card_bg))

        # Clear Formatting button
        btn_clear = tk.Button(toolbar, text="📄", command=self._clear_formatting,
                            **button_config)
        btn_clear.pack(side="left", padx=1)
        btn_clear.bind("<Enter>", lambda e, b=btn_clear: b.config(bg="#e5e7eb"))
        btn_clear.bind("<Leave>", lambda e, b=btn_clear: b.config(bg=self._card_bg))

        def _update_char_count(_event=None):
            length = len(self._msg_text.get("1.0", "end-1c"))
            remaining = max(0, 5000 - length)
            self._char_label.config(text=f"{length}/5000")

        self._msg_text.bind("<KeyRelease>", _update_char_count)

        # ---- Bottom Action Bar (fixed) ----
        action_bar = tk.Frame(dialog, bg=self._card_bg,
                              highlightthickness=1, highlightbackground=self._border,
                              relief="flat")
        action_bar.pack(fill="x", side="bottom")

        action_inner = tk.Frame(action_bar, bg=self._card_bg)
        action_inner.pack(fill="x", padx=16, pady=12)

        # Status on left
        self._status_message = tk.Label(action_inner, text="",
                                        font=("Segoe UI", 9),
                                        bg=self._card_bg, fg=self._success)
        self._status_message.pack(side="left")

        # Buttons on right
        btn_frame = tk.Frame(action_inner, bg=self._card_bg)
        btn_frame.pack(side="right")

        cancel_btn = tk.Button(btn_frame, text="Cancel",
                               font=("Segoe UI", 9),
                               bg="#f3f4f6", fg=self._text_primary,
                               relief="flat", padx=14, pady=6,
                               cursor="hand2", highlightthickness=0,
                               command=self._close)
        cancel_btn.pack(side="left", padx=(0, 8))
        cancel_btn.bind("<Enter>", lambda e, b=cancel_btn: b.config(bg="#e5e7eb"))
        cancel_btn.bind("<Leave>", lambda e, b=cancel_btn: b.config(bg="#f3f4f6"))
        cancel_btn.bind("<FocusIn>", lambda e, b=cancel_btn: b.config(relief="sunken"))
        cancel_btn.bind("<FocusOut>", lambda e, b=cancel_btn: b.config(relief="flat"))

        preview_btn = tk.Button(btn_frame, text="Preview",
                               font=("Segoe UI", 9),
                               bg="#e0f2fe", fg="#0369a1",
                               relief="flat", padx=14, pady=6,
                               cursor="hand2", highlightthickness=0,
                               command=self._preview)
        preview_btn.pack(side="left", padx=(0, 8))
        preview_btn.bind("<Enter>", lambda e, b=preview_btn: b.config(bg="#bae6fd"))
        preview_btn.bind("<Leave>", lambda e, b=preview_btn: b.config(bg="#e0f2fe"))
        preview_btn.bind("<FocusIn>", lambda e, b=preview_btn: b.config(relief="sunken"))
        preview_btn.bind("<FocusOut>", lambda e, b=preview_btn: b.config(relief="flat"))

        send_btn = tk.Button(btn_frame, text="Send",
                             font=("Segoe UI", 9, "bold"),
                             bg=self._primary, fg="white",
                             relief="flat", padx=16, pady=6,
                             cursor="hand2", highlightthickness=0,
                             command=self._do_send)
        send_btn.pack(side="left")
        send_btn.bind("<Enter>", lambda e, b=send_btn: b.config(bg=self._text_primary))
        send_btn.bind("<Leave>", lambda e, b=send_btn: b.config(bg=self._primary))
        send_btn.bind("<FocusIn>", lambda e, b=send_btn: b.config(relief="sunken"))
        send_btn.bind("<FocusOut>", lambda e, b=send_btn: b.config(relief="flat"))
        send_btn.focus_set()

        # Initial status
        self._set_status("Ready", self._success)

        # ---- Extra Toolbar Buttons ----
        # Separator before advanced features
        tk.Frame(toolbar, width=1, bg=self._border).pack(side="left", padx=4, fill="y", pady=2)

        # Font Family dropdown
        font_families = ["Segoe UI", "Arial", "Helvetica", "Times New Roman", "Courier New", "Georgia"]
        self._font_family_var = tk.StringVar(value=font_families[0])
        font_family_menu = tk.OptionMenu(toolbar, self._font_family_var, *font_families,
                                         command=self._apply_font_family)
        font_family_btn = font_family_menu.nametowidget(font_family_menu.children['menu'])
        font_family_btn.config(**button_config, text="⬇")
        font_family_btn.pack(side="left", padx=1)
        font_family_btn.bind("<Enter>", lambda e, b=font_family_btn: b.config(bg="#e5e7eb"))
        font_family_btn.bind("<Leave>", lambda e, b=font_family_btn: b.config(bg=self._card_bg))

        # Font Size dropdown
        font_sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "30", "36", "48"]
        self._font_size_var = tk.StringVar(value="10")
        font_size_menu = tk.OptionMenu(toolbar, self._font_size_var, *font_sizes,
                                       command=self._apply_font_size)
        font_size_btn = font_size_menu.nametowidget(font_size_menu.children['menu'])
        font_size_btn.config(**button_config, text="⬇")
        font_size_btn.pack(side="left", padx=1)
        font_size_btn.bind("<Enter>", lambda e, b=font_size_btn: b.config(bg="#e5e7eb"))
        font_size_btn.bind("<Leave>", lambda e, b=font_size_btn: b.config(bg=self._card_bg))

        # Text Color button
        btn_color = tk.Button(toolbar, text="🎨", command=self._apply_text_color,
                             **button_config)
        btn_color.pack(side="left", padx=1)
        btn_color.bind("<Enter>", lambda e, b=btn_color: b.config(bg="#e5e7eb"))
        btn_color.bind("<Leave>", lambda e, b=btn_color: b.config(bg=self._card_bg))

        # Highlight Color button
        btn_highlight = tk.Button(toolbar, text="🔆", command=self._apply_highlight_color,
                                 **button_config)
        btn_highlight.pack(side="left", padx=1)
        btn_highlight.bind("<Enter>", lambda e, b=btn_highlight: b.config(bg="#e5e7eb"))
        btn_highlight.bind("<Leave>", lambda e, b=btn_highlight: b.config(bg=self._card_bg))

        # Emoji button
        btn_emoji = tk.Button(toolbar, text="😀", command=self._apply_emoji,
                            **button_config)
        btn_emoji.pack(side="left", padx=1)
        btn_emoji.bind("<Enter>", lambda e, b=btn_emoji: b.config(bg="#e5e7eb"))
        btn_emoji.bind("<Leave>", lambda e, b=btn_emoji: b.config(bg=self._card_bg))

        # Clear Formatting button
        btn_clear = tk.Button(toolbar, text="📄", command=self._clear_formatting,
                            **button_config)
        btn_clear.pack(side="left", padx=1)
        btn_clear.bind("<Enter>", lambda e, b=btn_clear: b.config(bg="#e5e7eb"))
        btn_clear.bind("<Leave>", lambda e, b=btn_clear: b.config(bg=self._card_bg))

        # Undo/Redo buttons added earlier

        def _update_char_count(_event=None):
            length = len(self._msg_text.get("1.0", "end-1c"))
            remaining = max(0, 5000 - length)
            self._char_label.config(text=f"{length}/5000")
            # Update color based on remaining characters
            if length >= 4500:
                self._char_label.config(fg="#dc2626")  # Red
            elif length >= 4000:
                self._char_label.config(fg="#ea580c")  # Orange
            else:
                self._char_label.config(fg=self._text_secondary)

        self._msg_text.bind("<KeyRelease>", _update_char_count)

        dialog.wait_window()

    # ------------------------------------------------------------------
    # Toolbar formatting functions
    # ------------------------------------------------------------------
    def _apply_font_family(self, family):
        try:
            self._msg_text.tag_configure("font_family", font=family)
            self._msg_text.tag_add("font_family", "sel.first", "sel.last")
        except tk.TclError:
            pass

    def _apply_font_size(self, size):
        try:
            current_font = tkfont.Font(font=self._msg_text["font"])
            new_font = tkfont.Font(size=int(size), family=current_font['family'],
                                  weight=current_font['weight'], slant=current_font['slant'])
            self._msg_text.tag_configure("font_size", font=new_font)
            self._msg_text.tag_add("font_size", "sel.first", "sel.last")
        except tk.TclError:
            pass

    def _apply_text_color(self):
        color = tk.colorchooser.askcolor(title="Choose Text Color")
        if color[0]:
            try:
                self._msg_text.tag_configure("text_color", foreground=color[1])
                self._msg_text.tag_add("text_color", "sel.first", "sel.last")
            except tk.TclError:
                pass

    def _apply_highlight_color(self):
        color = tk.colorchooser.askcolor(title="Choose Highlight Color")
        if color[0]:
            try:
                self._msg_text.tag_configure("bg_highlight", background=color[1])
                self._msg_text.tag_add("bg_highlight", "sel.first", "sel.last")
            except tk.TclError:
                pass

    def _apply_emoji(self):
        # Open emoji picker dialog
        emoji_window = tk.Toplevel(self._dialog)
        emoji_window.title("Emoji Picker")
        emoji_window.geometry("400x300")
        emoji_window.configure(bg="white")
        emoji_window.transient(self._dialog)
        
        # Simple grid of common emojis
        emojis = ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣",
                 "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰",
                 "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
                 "🤗", "🤭", "🤫", "🤔", "😐", "😑", "😶", "😐",
                 "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪",
                 "😫", "😴", "😌", "😛", "😜", "😝", "🤤", "😒",
                 "😓", "😔", "😕", "🙃", "🤑", "😲", "🙀", "😨",
                 "😧", "😦", "😟", "😕", "🙁", "😞", "😓", "😩",
                 "😫", "😤", "😡", "😠", "🤬", "😈", "👿", "💀",
                 "☠️", "💩", "🤡", "👹", "👺", "👻", "👽", "👾",
                 "🤖", "😺", "😸", "😹", "😻", "😼", "😽", "🙀",
                 "😿", "😾"]
        
        row, col = 0, 0
        for emoji in emojis:
            btn = tk.Button(emoji_window, text=emoji, font=("Segoe UI", 12),
                          bg="white", relief="flat", width=4, height=2,
                          command=lambda e=emoji: self._insert_emoji(e, emoji_window))
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 7:
                col = 0
                row += 1
                if row > 6:
                    break
        
        tk.Button(emoji_window, text="Close", command=emoji_window.destroy,
                 bg="#f3f4f6", relief="flat").place(relx=0.5, rely=0.95, anchor="center")

    def _insert_emoji(self, emoji, window):
        try:
            self._msg_text.insert("insert", emoji)
            window.destroy()
        except tk.TclError:
            pass

    def _clear_formatting(self):
        # Remove all formatting tags
        for tag in self._msg_text.tag_names():
            self._msg_text.tag_remove(tag, "1.0", "end")
        # Reset font to default
        self._msg_text.configure(font=("Segoe UI", 10))

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

        if not self._files:
            self._attach_count.config(text="0/5")
            empty_label = tk.Label(self._attach_list,
                                  text="No files attached",
                                  font=("Segoe UI", 8),
                                  fg=self._text_secondary, bg=self._card_bg)
            empty_label.pack(pady=10)
            return

        self._attach_count.config(text=f"{len(self._files)}/5")

        for file_obj in self._files:
            # File card
            card = tk.Frame(self._attach_list, bg="white",
                           highlightthickness=1, highlightbackground=self._border,
                           relief="flat")
            card.pack(fill="x", pady=2, padx=1)

            # Icon
            icon_frame = tk.Frame(card, bg="white", width=28)
            icon_frame.pack(side="left", fill="y", padx=(6, 0))
            icon_frame.pack_propagate(False)
            tk.Label(icon_frame, text="📎", font=("Segoe UI", 10),
                     bg="white", fg=self._text_secondary).pack(expand=True)

            # Info
            info_frame = tk.Frame(card, bg="white")
            info_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

            tk.Label(info_frame, text=file_obj.name, font=("Segoe UI", 9),
                     fg=self._text_primary, bg="white",
                     anchor="w").pack(fill="x")

            tk.Label(info_frame, text=_format_size(file_obj.size), font=("Segoe UI", 7),
                     fg=self._text_secondary, bg="white",
                     anchor="w").pack(fill="x")

            # Remove button
            remove_btn = tk.Label(card, text="✕", font=("Segoe UI", 9, "bold"),
                                 bg="white", fg=self._error, cursor="hand2")
            remove_btn.pack(side="right", padx=(0, 8))
            remove_btn.bind("<Button-1>", lambda e, f=file_obj: self._remove_file(f))
            remove_btn.bind("<Enter>", lambda e, b=remove_btn: b.config(fg="#dc2626"))
            remove_btn.bind("<Leave>", lambda e, b=remove_btn: b.config(fg=self._error))

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _preview(self):
        """Preview the email without sending."""
        values = self._validate()
        if values is None:
            return

        preview = tk.Toplevel(self._dialog)
        preview.title("Email Preview")
        preview.geometry("600x500")
        preview.configure(bg=self._bg)
        preview.transient(self._dialog)
        preview.grab_set()

        header = tk.Frame(preview, bg=self._primary, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="Email Preview",
                font=("Segoe UI", 14, "bold"),
                fg="white", bg=self._primary).pack(expand=True)

        body = tk.Frame(preview, bg=self._card_bg, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Preview content
        tk.Label(body, text=f"To: {values['email']}",
                font=("Segoe UI", 10), fg=self._text_secondary,
                bg=self._card_bg, anchor="w").pack(fill="x", pady=2)

        tk.Label(body, text=f"Subject: {values['subject']}",
                font=("Segoe UI", 10), fg=self._text_secondary,
                bg=self._card_bg, anchor="w").pack(fill="x", pady=2)

        tk.Label(body, text="Message:",
                font=("Segoe UI", 10, "bold"),
                fg=self._text_primary, bg=self._card_bg,
                anchor="w").pack(fill="x", pady=(8, 4))

        preview_text = tk.Text(body, font=("Segoe UI", 10),
                              bg="#f9fafb", fg=self._text_primary,
                              relief="solid", bd=1, wrap="word",
                              height=15)
        preview_text.pack(fill="both", expand=True)
        preview_text.insert("1.0", values['message'])
        preview_text.config(state="disabled")

        btn_frame = tk.Frame(body, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(10, 0))

        tk.Button(btn_frame, text="Close",
                 font=("Segoe UI", 10),
                 bg="#e5e7eb", fg=self._text_primary,
                 relief="flat", padx=20, pady=6,
                 cursor="hand2",
                 command=preview.destroy).pack(side="right")

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------
    def _set_status(self, text: str, color: str):
        """Update status in title bar and bottom bar."""
        # Update bottom status
        if hasattr(self, '_status_message'):
            self._status_message.config(text=text, fg=color)
        
        # Update title bar status
        if self._status_text_label:
            self._status_text_label.config(text=text)
        
        # Update dot color
        if self._status_dot:
            dot_colors = {
                self._success: "#22c55e",
                self._error: "#ef4444",
                self._warning: "#f59e0b",
                self._text_secondary: "#6b7280"
            }
            dot_color = dot_colors.get(color, "#6b7280")
            self._status_dot.delete("all")
            self._status_dot.create_oval(2, 2, 8, 8, fill=dot_color, outline="")

    # ------------------------------------------------------------------
    # Validation + send
    # ------------------------------------------------------------------
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
            if hasattr(self, '_email_indicator'):
                self._email_indicator.set_invalid()
                self._email_indicator._label.config(text="✗")
            return None
        if not subject:
            self._set_status("Please enter a subject", self._error)
            return None
        if not message:
            self._set_status("Please enter a message", self._error)
            return None
        self._set_status("Ready", self._success)
        return {"name": name, "email": email,
                "subject": subject, "message": message}

    def _do_send(self):
        if self._dialog is None:
            return
        values = self._validate()
        if values is None:
            return
        status = self._status

        # Update status for sending
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
                self._set_status("Uploading attachments...", self._warning)
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