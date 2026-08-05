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
from tkinter import colorchooser, filedialog, font as tkfont

from .live_log import LiveLog
from .validation import FieldIndicator, is_valid_email

MAX_ATTACHMENTS = 5
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (matches backend)
MAX_MESSAGE_CHARS = 5000

FONT_FAMILIES = [
    "Segoe UI", "Arial", "Calibri", "Georgia",
    "Times New Roman", "Courier New", "Verdana",
]
FONT_SIZES = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "30", "36", "48"]

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


class _ScrollableFrame:
    """Minimal horizontal-strip scrollable frame used by the attachment panel."""

    def __init__(self, parent: tk.Widget, bg: str):
        self.body = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self.body, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        if event.width:
            self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_enter(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_leave(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


class UniversalEmailDialog:
    """One email component for all request categories.

    Receives the owning UniversalLicenseCenter so it can reuse the engine,
    hardware detector, cached status (auto-fill) and the center's theme.

    Optional `prefill` (dict) — the public interface used by the Renew
    License dialog: overrides the auto-filled values, locks the customer
    fields and pre-populates the subject (reason) and message (notes).
    """

    def __init__(self, center: Any, title: str, category: str,
                 parent: Optional[tk.Widget] = None,
                 prefill: Optional[Dict[str, str]] = None):
        self._center = center
        self._title = title
        self._category = category
        self._parent = parent or getattr(center, '_root', None)
        self._engine = center.engine
        self._hardware = center.hardware
        self._status = getattr(center, '_status', None)
        self._prefill = prefill or {}

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

        self._bold_on = tk.BooleanVar(value=False)
        self._italic_on = tk.BooleanVar(value=False)
        self._underline_on = tk.BooleanVar(value=False)

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
        auto = {
            "customer_name": status.customer_name if status else "",
            "customer_email": status.customer_email if status else "",
            "customer_company": getattr(status, 'customer_company', '') if status else "",
            "product": self._product_name or (status.product_name if status else ""),
            "plan": getattr(status, 'plan', '') if status else "",
            "license_key": display_key,
            "hardware_id": self._hardware.get_fingerprint(),
        }
        for key, value in (self._prefill or {}).items():
            if key in auto and value:
                auto[key] = value
        return auto

    # ------------------------------------------------------------------
    # Small build helpers (consistent, modern widgets)
    # ------------------------------------------------------------------
    def _card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, bg=self._card_bg,
                        highlightthickness=1, highlightbackground=self._border,
                        highlightcolor=self._border, relief="flat")

    def _card_title(self, parent: tk.Widget, text: str) -> tk.Frame:
        header = tk.Frame(parent, bg=self._card_bg)
        header.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(header, text=text,
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")
        return header

    def _info_field(self, parent: tk.Widget, label: str,
                    var: tk.StringVar, readonly: bool,
                    suffix: Optional[tk.Widget] = None) -> "tk.Entry":
        row = tk.Frame(parent, bg=self._card_bg)
        row.pack(fill="x", pady=3)

        tk.Label(row, text=label,
                 font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=10, anchor="w").pack(side="left", padx=(16, 6))

        if readonly:
            entry = tk.Entry(row, font=("Segoe UI", 9),
                             relief="solid", bd=1,
                             bg="#f2f4f8", fg=self._text_primary,
                             readonlybackground="#f2f4f8",
                             cursor="arrow", width=22)
            entry.configure(textvariable=var, state="readonly")
            entry.pack(side="left", fill="x", expand=True)
        else:
            entry = tk.Entry(row, font=("Segoe UI", 9),
                             relief="solid", bd=1,
                             bg="white", fg=self._text_primary,
                             insertbackground=self._primary,
                             highlightthickness=1, highlightbackground=self._border,
                             highlightcolor=self._primary,
                             width=22)
            entry.configure(textvariable=var)
            entry.pack(side="left", fill="x", expand=True, ipady=3)
            if suffix is not None:
                suffix.pack(side="left", padx=(6, 0))
        return entry

    def _tool_button(self, parent: tk.Widget, text: str, command,
                     font: tuple = ("Segoe UI", 9, "bold"),
                     width: int = 3,
                     is_active: Optional[callable] = None) -> tk.Button:
        btn = tk.Button(parent, text=text, command=command,
                        font=font, width=width,
                        bg=self._card_bg, fg=self._text_secondary,
                        relief="flat", bd=0, padx=4, pady=3,
                        cursor="hand2", highlightthickness=0,
                        activebackground="#e5e7eb", activeforeground=self._text_primary)
        btn.pack(side="left", padx=1)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#e9ecf1"))
        btn.bind("<Leave>", lambda e, b=btn: (
            b.config(bg=self._primary, fg="white") if is_active and is_active()
            else b.config(bg=self._card_bg)))
        return btn

    def _dropdown(self, parent: tk.Widget, label: str, values: List[str],
                  current: str, command, width: int) -> "tk.Menubutton":
        menu_btn = tk.Menubutton(parent, text=f"{current}  ▾",
                                 font=("Segoe UI", 9),
                                 bg=self._card_bg, fg=self._text_primary,
                                 relief="flat", bd=0, padx=6, pady=3,
                                 cursor="hand2", highlightthickness=0,
                                 activebackground="#e9ecf1", activeforeground=self._text_primary,
                                 width=width, anchor="w")
        menu = tk.Menu(menu_btn, tearoff=0, bg="white", fg=self._text_primary,
                       activebackground=self._primary, activeforeground="white",
                       font=("Segoe UI", 9), relief="flat", bd=0)
        for value in values:
            menu.add_command(label=value, command=lambda v=value: command(v))
        menu_btn.configure(menu=menu)
        menu_btn.pack(side="left", padx=3)
        return menu_btn

    def _separator(self, parent: tk.Widget):
        tk.Frame(parent, width=1, bg=self._border).pack(side="left", fill="y", padx=5, pady=3)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def show(self) -> None:
        dialog = tk.Toplevel(self._parent)
        dialog.title(self._title)
        dialog.geometry("1220x820")
        dialog.minsize(1060, 700)
        dialog.configure(bg=self._bg)
        dialog.resizable(True, True)
        if self._parent is not None:
            dialog.transient(self._parent)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", self._close)
        self._dialog = dialog

        auto = self._auto_values()

        # ---- Bottom action bar (packed FIRST so it is always visible) ----
        action_bar = tk.Frame(dialog, bg=self._card_bg)
        action_bar.pack(side="bottom", fill="x")
        tk.Frame(action_bar, bg=self._border, height=1).pack(fill="x")  # top hairline
        action_inner = tk.Frame(action_bar, bg=self._card_bg)
        action_inner.pack(fill="x", padx=20, pady=12)

        self._status_message = tk.Label(action_inner, text="",
                                        font=("Segoe UI", 9),
                                        bg=self._card_bg, fg=self._success)
        self._status_message.pack(side="left")

        btn_frame = tk.Frame(action_inner, bg=self._card_bg)
        btn_frame.pack(side="right")

        cancel_btn = tk.Button(btn_frame, text="Cancel",
                               font=("Segoe UI", 9),
                               bg="#f3f4f6", fg=self._text_primary,
                               relief="flat", padx=16, pady=6,
                               cursor="hand2", highlightthickness=0,
                               activebackground="#e5e7eb", activeforeground=self._text_primary,
                               command=self._close)
        cancel_btn.pack(side="left", padx=(0, 10))

        preview_btn = tk.Button(btn_frame, text="Preview",
                                font=("Segoe UI", 9),
                                bg="#e0f2fe", fg="#0369a1",
                                relief="flat", padx=16, pady=6,
                                cursor="hand2", highlightthickness=0,
                                activebackground="#bae6fd", activeforeground="#075985",
                                command=self._preview)
        preview_btn.pack(side="left", padx=(0, 10))

        send_btn = tk.Button(btn_frame, text="Send Message",
                             font=("Segoe UI", 9, "bold"),
                             bg=self._primary, fg="white",
                             relief="flat", padx=20, pady=6,
                             cursor="hand2", highlightthickness=0,
                             activebackground=self._text_primary, activeforeground="white",
                             command=self._do_send)
        send_btn.pack(side="left")

        # ---- Title Bar ----
        title_frame = tk.Frame(dialog, bg=self._primary, height=56)
        title_frame.pack(fill="x", side="top")
        title_frame.pack_propagate(False)

        title_inner = tk.Frame(title_frame, bg=self._primary)
        title_inner.pack(fill="both", padx=20, pady=10)

        close_btn = tk.Label(title_inner, text="✕", font=("Segoe UI", 14, "bold"),
                             fg="white", bg=self._primary, cursor="hand2", padx=6)
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ff6b6b"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="white"))

        status_frame = tk.Frame(title_inner, bg=self._primary)
        status_frame.pack(side="right", padx=(0, 18))

        self._status_dot = tk.Canvas(status_frame, width=10, height=10,
                                     bg=self._primary, highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 6))
        self._status_dot.create_oval(2, 2, 8, 8, fill=self._success, outline="")

        self._status_text_label = tk.Label(status_frame, text="Ready",
                                           font=("Segoe UI", 10),
                                           fg="white", bg=self._primary)
        self._status_text_label.pack(side="left")

        tk.Label(title_inner, text="✉  " + self._title,
                 font=("Segoe UI", 14, "bold"),
                 fg="white", bg=self._primary).pack(side="left")

        # ---- Main container ----
        body = tk.Frame(dialog, bg=self._bg)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=330)
        body.columnconfigure(1, weight=1, minsize=460)
        body.rowconfigure(0, weight=1)

        left_col = tk.Frame(body, bg=self._bg)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(20, 12), pady=16)
        left_col.columnconfigure(0, weight=1)

        right_col = tk.Frame(body, bg=self._bg)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=16)
        right_col.columnconfigure(0, weight=1)

        # ==== Left: Customer Information ====
        info_card = self._card(left_col)
        info_card.grid(row=0, column=0, sticky="ew")

        header = self._card_title(info_card, "👤 Customer Information")
        tk.Label(header, text="auto-filled", font=("Segoe UI", 8),
                 fg=self._text_secondary, bg=self._card_bg).pack(side="right")

        self._name_var = tk.StringVar(value=auto["customer_name"])
        self._email_var = tk.StringVar(value=auto["customer_email"])
        self._company_var = tk.StringVar(value=auto["customer_company"])

        info_fields = tk.Frame(info_card, bg=self._card_bg)
        info_fields.pack(fill="x", padx=16, pady=(0, 14))

        self._email_indicator_label = tk.Label(info_fields, text="",
                                               font=("Segoe UI", 9, "bold"),
                                               bg=self._card_bg, fg=self._success)
        self._email_indicator = FieldIndicator(self._email_indicator_label,
                                               success_color=self._success,
                                               error_color=self._error)

        self._name_entry = self._info_field(info_fields, "Name", self._name_var, bool(self._prefill))
        email_entry = self._info_field(info_fields, "Email", self._email_var, bool(self._prefill),
                                       suffix=self._email_indicator_label)
        self._company_entry = self._info_field(info_fields, "Company", self._company_var, bool(self._prefill))

        product_var = tk.StringVar(value=auto["product"])
        plan_var = tk.StringVar(value=auto["plan"])
        license_var = tk.StringVar(value=auto["license_key"])
        self._info_field(info_fields, "Product", product_var, True)
        self._info_field(info_fields, "Plan", plan_var, True)
        self._info_field(info_fields, "License", license_var, True)

        # Hardware ID (truncated display, full value as tooltip)
        hw_row = tk.Frame(info_fields, bg=self._card_bg)
        hw_row.pack(fill="x", pady=3)
        tk.Label(hw_row, text="Hardware",
                 font=("Segoe UI", 9),
                 fg=self._text_secondary, bg=self._card_bg,
                 width=10, anchor="w").pack(side="left", padx=(0, 6))
        hw_value = auto["hardware_id"]
        hw_display = hw_value[:14] + "..." if len(hw_value) > 14 else hw_value
        tk.Label(hw_row, text=hw_display,
                 font=("Segoe UI", 9),
                 fg=self._text_secondary, bg="#f2f4f8",
                 relief="solid", bd=1, anchor="w",
                 padx=6, pady=3).pack(side="left", fill="x", expand=True)

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

        email_entry.bind("<KeyRelease>", _update_email_indicator)
        _update_email_indicator()

        # ==== Left: Attachments ====
        attach_card = self._card(left_col)
        attach_card.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        left_col.rowconfigure(1, weight=1)

        attach_inner = tk.Frame(attach_card, bg=self._card_bg)
        attach_inner.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        attach_header = tk.Frame(attach_inner, bg=self._card_bg)
        attach_header.pack(fill="x", pady=(14, 6))

        tk.Label(attach_header, text="📎 Attachments",
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        self._attach_count = tk.Label(attach_header,
                                      text="0/5",
                                      font=("Segoe UI", 8, "bold"),
                                      fg=self._text_secondary,
                                      bg="#eef1f6",
                                      padx=6, pady=1)
        self._attach_count.pack(side="right", padx=(0, 8))

        add_btn = tk.Button(attach_header, text="+ Add Files",
                            font=("Segoe UI", 8, "bold"),
                            bg=self._primary, fg="white",
                            relief="flat", padx=8, pady=2,
                            cursor="hand2",
                            activebackground=self._text_primary, activeforeground="white",
                            command=self._pick_files)
        add_btn.pack(side="right")

        hint_row = tk.Frame(attach_inner, bg=self._card_bg)
        hint_row.pack(fill="x")
        tk.Label(hint_row, text=f"Up to {MAX_ATTACHMENTS} files · {MAX_FILE_SIZE // (1024 * 1024)} MB max each",
                 font=("Segoe UI", 7),
                 fg=self._text_secondary, bg=self._card_bg).pack(anchor="w")

        self._attach_scroll = tk.Frame(attach_inner, bg=self._card_bg)
        self._attach_scroll.pack(fill="both", expand=True, pady=(8, 0))
        scroll_body = _ScrollableFrame(self._attach_scroll, self._card_bg)
        scroll_body.body.pack(fill="both", expand=True)
        self._attach_list = scroll_body.inner

        self._render_attachments()

        # ==== Right: Subject ====
        subject_card = self._card(right_col)
        subject_card.grid(row=0, column=0, sticky="ew")

        subject_inner = tk.Frame(subject_card, bg=self._card_bg)
        subject_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(subject_inner, text="Subject",
                 font=("Segoe UI", 9, "bold"),
                 fg=self._text_primary, bg=self._card_bg,
                 anchor="w").pack(fill="x", pady=(0, 4))

        self._subject_var = tk.StringVar(value=(self._prefill or {}).get('subject', ''))
        self._subject_entry = tk.Entry(subject_inner, font=("Segoe UI", 10),
                                       relief="solid", bd=1,
                                       bg="white", fg=self._text_primary,
                                       insertbackground=self._text_primary,
                                       highlightthickness=1, highlightbackground=self._border,
                                       highlightcolor=self._primary,
                                       textvariable=self._subject_var)
        self._subject_entry.pack(fill="x", ipady=6)

        # ==== Right: Editor ====
        editor_card = self._card(right_col)
        editor_card.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        right_col.rowconfigure(1, weight=1)

        editor_inner = tk.Frame(editor_card, bg=self._card_bg)
        editor_inner.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        editor_header = tk.Frame(editor_inner, bg=self._card_bg)
        editor_header.pack(fill="x", pady=(14, 2))

        tk.Label(editor_header, text="📝 Message",
                 font=("Segoe UI", 10, "bold"),
                 fg=self._text_primary, bg=self._card_bg).pack(side="left")

        self._char_label = tk.Label(editor_header, text="0 / 5000",
                                    font=("Segoe UI", 8, "bold"),
                                    fg=self._text_secondary, bg=self._card_bg)
        self._char_label.pack(side="right")

        # ---- Toolbar (two rows for a responsive, tidy layout) ----
        toolbar = tk.Frame(editor_inner, bg=self._card_bg)
        toolbar.pack(fill="x", pady=(6, 6))

        row1 = tk.Frame(toolbar, bg=self._card_bg)
        row1.pack(fill="x", pady=1)
        row2 = tk.Frame(toolbar, bg=self._card_bg)
        row2.pack(fill="x", pady=1)

        # Row 1: Undo / Redo / Clear Formatting | B I U | Color / Highlight
        self._tool_button(row1, "↶", lambda: self._msg_text.edit_undo(), width=3)
        self._tool_button(row1, "↷", lambda: self._msg_text.edit_redo(), width=3)
        self._tool_button(row1, "Clear", self._clear_formatting,
                          font=("Segoe UI", 8, "bold"), width=6)
        self._separator(row1)

        self._btn_bold = self._tool_button(row1, "B", self._toggle_bold,
                                           font=("Segoe UI", 9, "bold"), width=3,
                                           is_active=self._bold_on.get)
        self._btn_italic = self._tool_button(row1, "I", self._toggle_italic,
                                             font=("Segoe UI", 9, "italic"), width=3,
                                             is_active=self._italic_on.get)
        self._btn_underline = self._tool_button(row1, "U", self._toggle_underline,
                                                font=("Segoe UI", 9, "underline"), width=3,
                                                is_active=self._underline_on.get)
        self._separator(row1)

        self._tool_button(row1, "Text Colour", self._apply_text_color,
                          font=("Segoe UI", 8, "bold"), width=8)
        self._tool_button(row1, "Highlight", self._apply_highlight_color,
                          font=("Segoe UI", 8, "bold"), width=8)

        # bullets / numbering
        self._tool_button(row2, "• Bullets", self._apply_bullet,
                          font=("Segoe UI", 8, "bold"), width=8)
        self._tool_button(row2, "1. Numbers", self._apply_numbered,
                          font=("Segoe UI", 8, "bold"), width=9)
        self._separator(row2)

        # Row 2: Font family + size dropdowns
        tk.Label(row2, text="Font", font=("Segoe UI", 8),
                 fg=self._text_secondary, bg=self._card_bg).pack(side="left", padx=(0, 2))
        self._font_family_var = tk.StringVar(value=FONT_FAMILIES[0])
        self._font_family_dropdown = self._dropdown(
            row2, "Font Family", FONT_FAMILIES, FONT_FAMILIES[0],
            self._apply_font_family, width=14)

        tk.Label(row2, text="Size", font=("Segoe UI", 8),
                 fg=self._text_secondary, bg=self._card_bg).pack(side="left", padx=(4, 2))
        self._font_size_var = tk.StringVar(value="10")
        self._font_size_dropdown = self._dropdown(
            row2, "Font Size", FONT_SIZES, "10",
            self._apply_font_size, width=5)

        # ---- Editor text ----
        editor_text_frame = tk.Frame(editor_inner, bg=self._card_bg)
        editor_text_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(editor_text_frame)
        scrollbar.pack(side="right", fill="y")

        self._msg_text = tk.Text(editor_text_frame, font=("Segoe UI", 10),
                                 relief="solid", bd=1, wrap="word", undo=True,
                                 maxundo=-1, autoseparators=True,
                                 yscrollcommand=scrollbar.set,
                                 bg="white", fg=self._text_primary,
                                 insertbackground=self._text_primary,
                                 highlightthickness=1,
                                 highlightbackground=self._border,
                                 highlightcolor=self._primary)
        self._msg_text.pack(fill="both", expand=True)
        scrollbar.config(command=self._msg_text.yview)

        # Rich text tags
        self._configure_text_tags()

        # Renew integration: pre-filled generated body (Reason / Notes editable)
        prefill_message = (self._prefill or {}).get('message')
        if prefill_message:
            self._msg_text.insert("1.0", prefill_message)

        # Keyboard shortcuts for formatting + undo/redo
        self._msg_text.bind("<Control-b>", lambda e: self._toggle_style("bold", self._bold_on))
        self._msg_text.bind("<Control-i>", lambda e: self._toggle_style("italic", self._italic_on))
        self._msg_text.bind("<Control-u>", lambda e: self._toggle_style("underline", self._underline_on))
        self._msg_text.bind("<Control-z>", lambda e: self._msg_text.edit_undo())
        self._msg_text.bind("<Control-y>", lambda e: self._msg_text.edit_redo())
        self._msg_text.bind("<Control-Z>", lambda e: self._msg_text.edit_undo())
        dialog.bind("<Control-Return>", lambda e: self._do_send())
        dialog.bind("<Escape>", lambda e: self._close())

        self._msg_text.bind("<KeyRelease>", self._update_char_count)
        self._update_char_count()

        self._set_status("Ready", self._success)
        self._name_entry.focus_set()

        dialog.wait_window()

    # ------------------------------------------------------------------
    # Rich-text tag management
    # ------------------------------------------------------------------
    def _configure_text_tags(self):
        self._msg_text.tag_configure("bold", font=tkfont.Font(font=("Segoe UI", 10, "bold")))
        self._msg_text.tag_configure("italic", font=tkfont.Font(font=("Segoe UI", 10, "italic")))
        self._msg_text.tag_configure("underline",
                                     font=tkfont.Font(font=("Segoe UI", 10, "underline")))
        self._msg_text.tag_configure("text_color", foreground=self._text_primary)
        self._msg_text.tag_configure("bg_highlight", background="#fef08a")
        self._msg_text.tag_configure("font_family", font=("Segoe UI", 10))
        self._msg_text.tag_configure("font_size", font=("Segoe UI", 10))

    def _toggle_style(self, tag: str, var: tk.BooleanVar):
        var.set(not var.get())
        try:
            if var.get():
                self._msg_text.tag_add(tag, "sel.first", "sel.last")
            else:
                self._msg_text.tag_remove(tag, "sel.first", "sel.last")
        except tk.TclError:
            pass
        btn_map = {"bold": self._btn_bold, "italic": self._btn_italic,
                   "underline": self._btn_underline}
        btn = btn_map.get(tag)
        if btn is not None:
            if var.get():
                btn.config(bg=self._primary, fg="white",
                           activebackground=self._text_primary, activeforeground="white")
            else:
                btn.config(bg=self._card_bg, fg=self._text_secondary,
                           activebackground="#e5e7eb", activeforeground=self._text_primary)
        self._refresh_active_formatting()

    def _refresh_active_formatting(self):
        """Keep active toggles visually consistent for subsequent typing."""
        try:
            if self._bold_on.get():
                self._msg_text.tag_add("bold", "insert-1c wordstart", "insert-1c wordend")
        except tk.TclError:
            pass

    def _toggle_bold(self):
        self._toggle_style("bold", self._bold_on)

    def _toggle_italic(self):
        self._toggle_style("italic", self._italic_on)

    def _toggle_underline(self):
        self._toggle_style("underline", self._underline_on)

    # ------------------------------------------------------------------
    # Toolbar formatting functions
    # ------------------------------------------------------------------
    def _new_font(self, family: Optional[str] = None, size: Optional[int] = None):
        base = tkfont.Font(font=self._msg_text["font"])
        return tkfont.Font(family=family or base['family'] or "Segoe UI",
                           size=int(size if size is not None else base['size']),
                           weight=base['weight'], slant=base['slant'])

    def _apply_font_family(self, family):
        self._font_family_var.set(family)
        self._font_family_dropdown.configure(text=f"{family}  ▾")
        try:
            self._msg_text.tag_configure("font_family", font=self._new_font(family=family))
            self._msg_text.tag_add("font_family", "sel.first", "sel.last")
        except tk.TclError:
            pass

    def _apply_font_size(self, size):
        self._font_size_var.set(size)
        self._font_size_dropdown.configure(text=f"{size}  ▾")
        try:
            self._msg_text.tag_configure("font_size", font=self._new_font(size=int(size)))
            self._msg_text.tag_add("font_size", "sel.first", "sel.last")
        except tk.TclError:
            pass

    def _apply_text_color(self):
        color = colorchooser.askcolor(title="Choose text color",
                                      color=self._text_primary,
                                      parent=self._dialog)
        if color and color[0]:
            try:
                self._msg_text.tag_configure("text_color", foreground=color[1])
                self._msg_text.tag_add("text_color", "sel.first", "sel.last")
            except tk.TclError:
                pass

    def _apply_highlight_color(self):
        color = colorchooser.askcolor(title="Choose highlight color",
                                      color="#fef08a",
                                      parent=self._dialog)
        if color and color[0]:
            try:
                self._msg_text.tag_configure("bg_highlight", background=color[1])
                self._msg_text.tag_add("bg_highlight", "sel.first", "sel.last")
            except tk.TclError:
                pass

    def _apply_bullet(self):
        try:
            text = self._msg_text.get("sel.first", "sel.last")
            lines = text.split('\n')
            bulleted = ['• ' + line if line.strip() else line for line in lines]
            self._msg_text.delete("sel.first", "sel.last")
            self._msg_text.insert("sel.first", '\n'.join(bulleted))
        except tk.TclError:
            pass

    def _apply_numbered(self):
        try:
            lines = self._msg_text.get("sel.first", "sel.last").split('\n')
            numbered = [f"{i + 1}. {line}" if line.strip() else line
                        for i, line in enumerate(lines)]
            self._msg_text.delete("sel.first", "sel.last")
            self._msg_text.insert("sel.first", '\n'.join(numbered))
        except tk.TclError:
            pass

    def _clear_formatting(self):
        # Remove all formatting tags, reset font + toggles
        for tag in (self._msg_text.tag_names() or ()):
            try:
                self._msg_text.tag_remove(tag, "1.0", "end")
            except tk.TclError:
                continue
        self._msg_text.configure(font=("Segoe UI", 10, "normal"))
        self._configure_text_tags()
        for var, btn in ((self._bold_on, self._btn_bold),
                         (self._italic_on, self._btn_italic),
                         (self._underline_on, self._btn_underline)):
            var.set(False)
            btn.config(bg=self._card_bg, fg=self._text_secondary,
                       activebackground="#e5e7eb", activeforeground=self._text_primary)
        self._font_family_var.set(FONT_FAMILIES[0])
        self._font_size_var.set("10")
        self._font_family_dropdown.configure(text=f"{FONT_FAMILIES[0]}  ▾")
        self._font_size_dropdown.configure(text="10  ▾")
        self._set_status("Formatting cleared", self._text_secondary)

    def _update_char_count(self, _event=None):
        length = len(self._msg_text.get("1.0", "end-1c"))
        remaining = max(0, MAX_MESSAGE_CHARS - length)
        self._char_label.config(text=f"{length} / {MAX_MESSAGE_CHARS}")
        if remaining <= 200:
            self._char_label.config(fg=self._error)
        elif remaining <= 1000:
            self._char_label.config(fg=self._warning)
        else:
            self._char_label.config(fg=self._text_secondary)

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
            try:
                if os.path.getsize(path) > MAX_FILE_SIZE:
                    self._set_status(f"File exceeds 10 MB limit: {os.path.basename(path)}",
                                     self._error)
                    continue
            except OSError:
                continue
            if any(f.path == path for f in self._files):
                continue
            self._files.append(_AttachedFile(path))
        self._render_attachments()

    def _remove_file(self, file_obj: _AttachedFile):
        self._files = [f for f in self._files if f is not file_obj]
        self._render_attachments()

    def _render_attachments(self):
        if not getattr(self, '_attach_list', None):
            return
        for child in self._attach_list.winfo_children():
            child.destroy()

        self._attach_count.config(text=f"{len(self._files)}/{MAX_ATTACHMENTS}")

        if not self._files:
            empty = tk.Frame(self._attach_list, bg=self._card_bg)
            empty.pack(fill="both", expand=True)
            tk.Label(empty, text="No files attached",
                     font=("Segoe UI", 9),
                     fg=self._text_secondary, bg=self._card_bg).pack(pady=14)
            return

        for file_obj in self._files:
            card = tk.Frame(self._attach_list, bg="white",
                            highlightthickness=1, highlightbackground=self._border,
                            relief="flat")
            card.pack(fill="x", pady=3)

            tk.Label(card, text="📎", font=("Segoe UI", 11),
                     bg="white", fg=self._text_secondary).pack(side="left", padx=(8, 6))

            info_frame = tk.Frame(card, bg="white")
            info_frame.pack(side="left", fill="both", expand=True, pady=4)

            tk.Label(info_frame, text=file_obj.name, font=("Segoe UI", 9),
                     fg=self._text_primary, bg="white",
                     anchor="w").pack(fill="x")

            tk.Label(info_frame, text=_format_size(file_obj.size), font=("Segoe UI", 7),
                     fg=self._text_secondary, bg="white",
                     anchor="w").pack(fill="x")

            remove_btn = tk.Label(card, text="✕", font=("Segoe UI", 10, "bold"),
                                  bg="white", fg=self._error, cursor="hand2")
            remove_btn.pack(side="right", padx=(0, 10))
            remove_btn.bind("<Button-1>", lambda e, f=file_obj: self._remove_file(f))
            remove_btn.bind("<Enter>", lambda e, b=remove_btn: b.config(fg="#ff6b6b"))
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
        preview.geometry("620x520")
        preview.minsize(480, 380)
        preview.configure(bg=self._bg)
        preview.transient(self._dialog)
        preview.grab_set()

        header = tk.Frame(preview, bg=self._primary, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="📧 Email Preview",
                 font=("Segoe UI", 13, "bold"),
                 fg="white", bg=self._primary).pack(expand=True)

        body = tk.Frame(preview, bg=self._card_bg, padx=24, pady=18)
        body.pack(fill="both", expand=True)
        body.configure(highlightthickness=1, highlightbackground=self._border)

        tk.Label(body, text=f"To: {values['email']}",
                 font=("Segoe UI", 10), fg=self._text_secondary,
                 bg=self._card_bg, anchor="w").pack(fill="x", pady=(0, 3))

        tk.Label(body, text=f"Subject: {values['subject']}",
                 font=("Segoe UI", 10), fg=self._text_secondary,
                 bg=self._card_bg, anchor="w").pack(fill="x", pady=3)

        if self._files:
            tk.Label(body, text=f"Attachments: {', '.join(f.name for f in self._files)}",
                     font=("Segoe UI", 9), fg=self._text_secondary,
                     bg=self._card_bg, anchor="w").pack(fill="x", pady=3)

        tk.Frame(body, bg=self._border, height=1).pack(fill="x", pady=(8, 10))

        preview_text = tk.Text(body, font=("Segoe UI", 10),
                               bg="#ffffff", fg=self._text_primary,
                               relief="solid", bd=1, wrap="word",
                               highlightthickness=1, highlightbackground=self._border)
        preview_text.pack(fill="both", expand=True)
        preview_text.insert("1.0", values['message'])
        preview_text.config(state="disabled")

        btn_frame = tk.Frame(body, bg=self._card_bg)
        btn_frame.pack(fill="x", pady=(12, 0))

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
        """Update status in top bar and both status locators."""
        if hasattr(self, '_status_message'):
            self._status_message.config(text=text, fg=color)
        if self._status_text_label:
            self._status_text_label.config(text=text)
        if self._status_dot:
            dot_colors = {
                self._success: "#22c55e",
                self._error: "#ef4444",
                self._warning: "#f59e0b",
                self._text_secondary: "#6b7280",
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
            self._name_entry.focus_set()
            return None
        if not is_valid_email(email):
            self._set_status("Please enter a valid email address", self._error)
            if hasattr(self, '_email_indicator'):
                self._email_indicator.set_invalid()
                self._email_indicator._label.config(text="✗")
            return None
        if not subject:
            self._set_status("Please enter a subject", self._error)
            self._subject_entry.focus_set()
            return None
        if not message:
            self._set_status("Please enter a message", self._error)
            self._msg_text.focus_set()
            return None
        if len(message) > MAX_MESSAGE_CHARS:
            self._set_status(f"Message exceeds {MAX_MESSAGE_CHARS} characters", self._error)
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