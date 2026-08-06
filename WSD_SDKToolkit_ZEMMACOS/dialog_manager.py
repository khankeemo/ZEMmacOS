"""DialogManager — the one dialog implementation for every popup.

Success, Warning, Error, Loading and Confirmation popups all share this class:
one layout, one animation, one button style. Screens never build ad-hoc
``Toplevel`` popups for messages (the Welcome / License Center / Email /
Success dialogs are full flows and remain separate).

Design system (Phase 12):
- 48px header bar, color = kind (success green / warning amber / error red /
  info primary / confirm primary).
- Single message area with wrapping text; optional detail body.
- One primary button (Close/OK) or Yes/No for confirmations.
- Centered on the parent window; modal (grab_set); Esc closes; Enter confirms.
- Non-blocking loading indicator with a stage label.
"""
import tkinter as tk
from typing import Any, Callable, Optional

KIND_COLORS = {
    "info": "#6366f1",
    "success": "#16a34a",
    "warning": "#f59e0b",
    "error": "#dc2626",
    "confirm": "#6366f1",
}

_BG = "#f0f2f5"
_CARD_BG = "#ffffff"
_TEXT_PRIMARY = "#1a1a2e"
_TEXT_SECONDARY = "#6b7280"
_BORDER = "#d1d5db"


def _center_on(parent: Optional[tk.Misc], window: tk.Toplevel) -> None:
    try:
        window.update_idletasks()
        w = window.winfo_width()
        h = window.winfo_height()
        if parent is not None and parent.winfo_exists():
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        else:
            x = (window.winfo_screenwidth() - w) // 2
            y = (window.winfo_screenheight() - h) // 2
        window.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
    except Exception:
        pass


class MessageDialog:
    """One message popup (info / success / warning / error / confirmation)."""

    def __init__(self, parent: Optional[tk.Misc], title: str, message: str,
                 kind: str = "info", detail: str = "",
                 on_yes: Optional[Callable[[], None]] = None,
                 on_no: Optional[Callable[[], None]] = None,
                 yes_text: str = "Yes", no_text: str = "No",
                 button_text: str = "OK"):
        self._parent = parent
        self._title = title
        self._message = message
        self._kind = kind if kind in KIND_COLORS else "info"
        self._detail = detail
        self._on_yes = on_yes
        self._on_no = on_no
        self._yes_text = yes_text
        self._no_text = no_text
        self._button_text = button_text
        self._root: Optional[tk.Toplevel] = None
        self._result: Optional[bool] = None

    def _make_window(self) -> tk.Toplevel:
        parent = self._parent if (self._parent and self._parent.winfo_exists()) else None
        window = tk.Toplevel(parent) if parent else tk.Toplevel()
        window.title(self._title)
        window.geometry("460x260")
        window.resizable(False, False)
        window.configure(bg=_BG)
        if parent:
            window.transient(parent)
            window.grab_set()
        return window

    def show(self) -> Optional[bool]:
        window = self._make_window()
        self._root = window
        accent = KIND_COLORS[self._kind]

        header = tk.Frame(window, bg=accent, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self._title, font=("Segoe UI", 15, "bold"),
                 fg="white", bg=accent).pack(expand=True)

        main = tk.Frame(window, bg=_CARD_BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        tk.Label(main, text=self._message, font=("Segoe UI", 11),
                 bg=_CARD_BG, fg=_TEXT_PRIMARY, justify="left",
                 wraplength=400, anchor="w").pack(fill="x", pady=(4, 10))

        if self._detail:
            tk.Label(main, text=self._detail, font=("Segoe UI", 9),
                     bg=_CARD_BG, fg=_TEXT_SECONDARY, justify="left",
                     wraplength=400, anchor="w").pack(fill="x", pady=(0, 6))

        btn_frame = tk.Frame(main, bg=_CARD_BG)
        btn_frame.pack(fill="x", pady=(12, 0))

        def close(value: Optional[bool] = None):
            self._result = value
            try:
                window.grab_release()
            except Exception:
                pass
            try:
                window.destroy()
            except Exception:
                pass

        def do_yes():
            close(True)
            if self._on_yes:
                self._on_yes()

        def do_no():
            close(False)
            if self._on_no:
                self._on_no()

        if self._kind == "confirm":
            tk.Button(btn_frame, text=self._yes_text, command=do_yes,
                      font=("Segoe UI", 11, "bold"), bg=accent, fg="white",
                      relief="flat", padx=18, pady=7, cursor="hand2"
                      ).pack(side="left", expand=True, fill="x", padx=(0, 6))
            tk.Button(btn_frame, text=self._no_text, command=do_no,
                      font=("Segoe UI", 11), bg="#e5e7eb", fg=_TEXT_PRIMARY,
                      relief="flat", padx=18, pady=7, cursor="hand2"
                      ).pack(side="left", expand=True, fill="x")
            window.bind("<Return>", lambda e: do_yes())
        else:
            tk.Button(btn_frame, text=self._button_text, command=lambda: close(),
                      font=("Segoe UI", 11, "bold"), bg=accent, fg="white",
                      relief="flat", padx=18, pady=7, cursor="hand2"
                      ).pack(expand=True, fill="x")
            window.bind("<Return>", lambda e: close())

        window.bind("<Escape>", lambda e: close())
        window.protocol("WM_DELETE_WINDOW", lambda: close())
        _center_on(self._parent, window)
        window.wait_window()
        return self._result

    def update_message(self, message: str) -> None:
        if self._root and self._root.winfo_exists():
            try:
                for child in self._root.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grand in child.winfo_children():
                            if isinstance(grand, tk.Label) and grand.winfo_ismapped():
                                grand.config(text=message)
                                return
            except Exception:
                pass

    def close(self) -> None:
        if self._root and self._root.winfo_exists():
            try:
                self._root.destroy()
            except Exception:
                pass


class LoadingDialog:
    """Non-blocking working indicator (AWS-01 Rule 6)."""

    def __init__(self, parent: Optional[tk.Misc], title: str, message: str = "Working..."):
        self._parent = parent
        self._title = title
        self._message = message
        self._root: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None

    def show(self) -> "LoadingDialog":
        parent = self._parent if (self._parent and self._parent.winfo_exists()) else None
        window = tk.Toplevel(parent) if parent else tk.Toplevel()
        self._root = window
        window.title(self._title)
        window.geometry("380x140")
        window.resizable(False, False)
        window.configure(bg=_CARD_BG)
        if parent:
            window.transient(parent)
        window.attributes("-topmost", True)

        header = tk.Frame(window, bg="#6366f1", height=44)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self._title, font=("Segoe UI", 13, "bold"),
                 fg="white", bg="#6366f1").pack(expand=True)

        main = tk.Frame(window, bg=_CARD_BG, padx=20, pady=18)
        main.pack(fill="both", expand=True)
        self._label = tk.Label(main, text=self._message, font=("Segoe UI", 10),
                               bg=_CARD_BG, fg=_TEXT_SECONDARY,
                               justify="center", wraplength=320)
        self._label.pack(fill="x")
        _center_on(self._parent, window)
        return self

    def update_message(self, message: str) -> None:
        if self._label:
            try:
                self._label.config(text=message)
            except Exception:
                pass

    def close(self) -> None:
        if self._root and self._root.winfo_exists():
            try:
                self._root.destroy()
            except Exception:
                pass


class DialogManager:
    """Facade — every popup goes through these helpers. No module may create
    its own messagebox/Toplevel for standard messages."""

    @staticmethod
    def info(parent: Optional[tk.Misc], title: str, message: str) -> None:
        MessageDialog(parent, title, message, kind="info", button_text="OK").show()

    @staticmethod
    def success(parent: Optional[tk.Misc], title: str, message: str) -> None:
        MessageDialog(parent, title, message, kind="success", button_text="OK").show()

    @staticmethod
    def warning(parent: Optional[tk.Misc], title: str, message: str,
                detail: str = "") -> None:
        MessageDialog(parent, title, message, kind="warning", detail=detail,
                      button_text="OK").show()

    @staticmethod
    def error(parent: Optional[tk.Misc], title: str, message: str) -> None:
        MessageDialog(parent, title, message, kind="error", button_text="OK").show()

    @staticmethod
    def confirm(parent: Optional[tk.Misc], title: str, message: str,
                on_yes: Optional[Callable[[], None]] = None,
                on_no: Optional[Callable[[], None]] = None,
                yes_text: str = "Yes", no_text: str = "No") -> Optional[bool]:
        return MessageDialog(parent, title, message, kind="confirm",
                             on_yes=on_yes, on_no=on_no,
                             yes_text=yes_text, no_text=no_text).show()
