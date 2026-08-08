"""UI design system — the reusable, global source of every SDK style.

This module is the SDK's "global.css": design tokens (colour, radius, spacing,
type scale) plus compact, rounded, modern widgets. Every screen (Welcome,
Activation, Renewal, …) composes these widgets instead of sprinkling ad-hoc
inline styles, so the whole generated SDK has a consistent, professional,
compact, high-DPI look.

No product-specific UI here: everything is generic and reusable across every
generated SDK.
"""

import sys
import tkinter as tk
from typing import Callable, Optional

__all__ = [
    "RADIUS", "INPUT_H", "BUTTON_H", "COL", "theme_set_primary",
    "setup_dpi_awareness", "hex_lerp",
    "Label", "SectionLabel", "Subtitle", "StatusPill",
    "RoundedEntry", "Button", "Card", "GradientHeader", "ProgressBar",
]

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

RADIUS = 12.0
INPUT_H = 40
BUTTON_H = 38

COL = {
    "surface": "#ffffff",
    "surface_alt": "#f6f8fb",
    "bg": "#eef1f6",
    "primary": "#6366f1",
    "accent": "#38bdf8",
    "primary_hover": "#575ee8",
    "primary_pressed": "#4a51c9",
    "text": "#1e2430",
    "text_muted": "#5c6675",
    "text_faint": "#97a2b5",
    "border": "#e2e6ee",
    "success": "#16a34a",
    "warning": "#b45309",
    "error": "#dc2626",
    "info": "#0284c7",
    "shadow": "#dfe3e9",
    "font": "Segoe UI",
}


def theme_set_primary(color: str) -> None:
    """Bind branding.primary_color to the whole accent ramp (called once)."""
    COL["primary"] = color
    COL["primary_hover"] = hex_lerp(color, "#000000", 0.14)
    COL["primary_pressed"] = hex_lerp(color, "#000000", 0.28)
    COL["accent"] = hex_lerp(color, "#38bdf8", 0.42)


def setup_dpi_awareness() -> None:
    """Crisp HiDPI rendering on Windows; a safe no-op elsewhere."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def hex_lerp(a: str, b: str, t: float) -> str:
    """Interpolate two '#rrggbb' colours on 0..1 — drives the hover tween."""
    a = a.lstrip("#")
    b = b.lstrip("#")
    t = max(0.0, min(1.0, t))
    p = lambda s, i: int(s[i:i + 2], 16)
    c = lambda i: round((1 - t) * p(a, i) + t * p(b, i))
    return "#%02x%02x%02x" % (c(0), c(2), c(4))


def _rrect(cv: "tk.Canvas", x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle as a smooth polygon on a canvas."""
    r = max(1.0, r)
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1 + r, x2, y2 - r,
        x2 - r, y2, x1 + r, y2, x1, y2 - r, x1, y1 + r,
    ]
    return cv.create_polygon(pts, smooth=True, splinesteps=4, **kw)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

class Label(tk.Label):
    def __init__(self, parent, text: str = "", *, size: int = 10,
                 weight: str = "normal", color: Optional[str] = None,
                 justify: str = "left", **kw):
        tk.Label.__init__(self, parent, text=text,
                          font=(COL["font"], size, weight),
                          fg=color or COL["text"],
                          bg=COL["surface"],
                          anchor="center" if justify == "center" else "w",
                          justify="center" if justify == "center" else "left",
                          padx=2, pady=1, **kw)


class SectionLabel(tk.Label):
    """Tiny uppercase section heading."""

    def __init__(self, parent, text: str, *, color: Optional[str] = None, **kw):
        tk.Label.__init__(self, parent, text=text.upper(),
                          font=(COL["font"], 9, "bold"),
                          fg=color or COL["text_faint"],
                          bg=COL["surface"], anchor="w", **kw)


class Subtitle(tk.Label):
    """Muted helper text."""

    def __init__(self, parent, text: str, *, size: int = 9, **kw):
        tk.Label.__init__(self, parent, text=text, font=(COL["font"], size),
                          fg=COL["text_muted"], bg=COL["surface"],
                          anchor="w", **kw)


# ---------------------------------------------------------------------------
# Status pill (chip)
# ---------------------------------------------------------------------------

_PILL_COLORS = {
    "success": "#16a34a", "error": "#dc2626", "warning": "#b45309",
    "info": "#0284c7", "neutral": "#5c6675",
}


class StatusPill(tk.Canvas):
    """A compact rounded status chip. Call `.set_text(text, kind)` to repaint."""

    def __init__(self, parent, *, height: int = 26):
        self._h = height
        tk.Canvas.__init__(self, parent, bg=COL["surface"], height=height,
                           highlightthickness=0, bd=0)
        self._drawn = False

    def set_text(self, text: str, kind: str = "neutral") -> None:
        self.delete("all")
        if not text:
            return
        color = _PILL_COLORS.get(kind, _PILL_COLORS["neutral"])
        w = max(10, len(text)) * 8 + 26
        self.configure(width=w)
        _rrect(self, 1, 1, w, self._h, self._h // 2,
               fill=hex_lerp(color, "#ffffff", 0.9), outline="")
        self.create_text(w // 2, self._h // 2 + 1, text=text,
                         fill=hex_lerp(color, "#000000", 0.25),
                         font=(COL["font"], 9, "bold"))


# ---------------------------------------------------------------------------
# Rounded text input
# ---------------------------------------------------------------------------

class RoundedEntry(tk.Canvas):
    """Compact rounded text box with a primary focus ring."""

    def __init__(self, parent, *, width: int = 320, justify: str = "center",
                 placeholder: str = "", password: bool = False):
        self._width = width
        inner = width - 28
        tk.Canvas.__init__(self, parent, width=width, height=INPUT_H,
                           bg=COL["surface"], highlightthickness=0, bd=0)
        self.entry = tk.Entry(
            self, font=(COL["font"], 12), justify=justify,
            relief="flat", bd=0, highlightthickness=0,
            bg=COL["surface_alt"], fg=COL["text"],
            insertbackground=COL["primary"])
        if password:
            self.entry.configure(show="\u2022")
        self._win = self.create_window(width // 2, INPUT_H // 2,
                                       window=self.entry, width=width - 24)
        self._paint(False)
        self.entry.bind("<FocusIn>", lambda e: self._paint(True))
        self.entry.bind("<FocusOut>", lambda e: self._paint(False))

    def _paint(self, focused: bool) -> None:
        tk.Canvas.delete(self, "frame")
        _rrect(self, 1, 1, self._width - 1, INPUT_H - 1, RADIUS,
               fill=COL["surface"], outline=COL["primary"] if focused else COL["border"],
               width=1, tags="frame")

    def get(self) -> str:
        return self.entry.get()

    def delete(self, first, last=None) -> None:
        self.entry.delete(first, last)

    def insert(self, index, string) -> None:
        self.entry.insert(index, string)

    def focus_set(self):
        self.entry.focus_set()

    def state(self, mode: str) -> None:
        self.entry.config(state=mode)


# ---------------------------------------------------------------------------
# Compact rounded button (smooth hover tween)
# ---------------------------------------------------------------------------

_KIND_FILLS = {
    "primary": ("#6366f1", "#575ee8"),
    "success": ("#16a34a", "#27b85d"),
    "warning": ("#d97706", "#e58a1a"),
    "danger":  ("#dc2626", "#e24a3d"),
    "ghost":   ("#eef1f6", "#e3e8f1"),
}


class Button(tk.Canvas):
    """A compact rounded button with a tweened hover animation.

    ``kind`` ∈ {primary, success, warning, danger, ghost}. Ghost uses dark
    text; every other kind uses white text.
    """

    def __init__(self, parent, text: str, *, kind: str = "primary",
                 command: Optional[Callable[[], None]] = None,
                 width: int = 200, height: Optional[int] = None):
        self._kind = kind
        self._text = text
        self._command = command
        self._width = width
        self._height = height or BUTTON_H
        self._over = False
        self._disabled = False
        self._current = "#6366f1"
        self._anim = None
        tk.Canvas.__init__(self, parent, width=width, height=self._height,
                           bg=COL["surface"], highlightthickness=0, bd=0)
        self.bind("<Button-1>", self._on_press)
        self.bind("<Enter>", lambda e: self._set_over(True))
        self.bind("<Leave>", lambda e: self._set_over(False))
        self._draw()

    # -- colour resolution ------------------------------------------------
    def _fill_now(self) -> str:
        if self._disabled:
            return COL["border"]
        base, hover = _KIND_FILLS.get(self._kind, _KIND_FILLS["primary"])
        return hover if self._over else base

    def _fg(self) -> str:
        if self._disabled:
            return COL["text_faint"]
        return COL["text"] if self._kind == "ghost" else "#ffffff"

    # -- drawing -----------------------------------------------------------
    def _draw(self) -> None:
        self.delete("all")
        self._current = self._fill_now()
        _rrect(self, 1, 1, self._width - 1, self._height - 1, RADIUS,
               fill=self._current, outline="", tags="body")
        self.create_text(self._width // 2, self._height // 2 + 1, text=self._text,
                         fill=self._fg(), font=(COL["font"], 11, "bold"),
                         tags="label")

    def _body_only(self, fill: str) -> None:
        self.delete("body")
        _rrect(self, 1, 1, self._width - 1, self._height - 1, RADIUS,
               fill=fill, outline="", tags="body")

    # -- hover animation ----------------------------------------------------
    def _set_over(self, over: bool) -> None:
        self._over = over
        if self._disabled:
            return
        self._tween(self._fill_now())

    def _tween(self, target: str) -> None:
        if self._anim is not None:
            try:
                self.after_cancel(self._anim)
            except Exception:
                pass
            self._anim = None
        start = self._current
        step = [0]
        steps = 6

        def _tick():
            step[0] += 1
            t = min(1.0, step[0] / steps)
            self._body_only(hex_lerp(start, target, t))
            self._current = hex_lerp(start, target, t)
            if step[0] >= steps:
                self._anim = None
                return
            self._anim = self.after(12, _tick)

        self._anim = self.after(1, _tick)

    # -- interaction ---------------------------------------------------------
    def _on_press(self, _event) -> None:
        if self._disabled or not self._command:
            return
        try:
            self._command()
        except Exception:
            pass

    def set_state(self, state: str) -> None:
        self._disabled = state == "disabled"
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()


# ---------------------------------------------------------------------------
# Card, gradient header, progress bar
# ---------------------------------------------------------------------------

class Card(tk.Frame):
    """A white card with a soft shadow and a subtle border.

    Children pack into ``card.body``.
    """

    def __init__(self, parent, *, padx: int = 20, pady: int = 18):
        tk.Frame.__init__(self, parent, bg=COL["shadow"])
        inner = tk.Frame(self, bg=COL["surface"],
                         highlightthickness=1, highlightbackground=COL["border"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)
        self.body = tk.Frame(inner, bg=COL["surface"])
        self.body.pack(fill="both", expand=True, padx=padx, pady=pady)


class GradientHeader(tk.Canvas):
    """A soft left→right gradient band with a title and optional subtitle."""

    def __init__(self, parent, *, title: str = "", subtitle: str = "",
                 height: int = 64):
        self._title = title
        self._subtitle = subtitle
        self._h = height
        tk.Canvas.__init__(self, parent, height=height,
                         bg=COL["primary"], highlightthickness=0, bd=0)
        self.bind("<Configure>", self._redraw)

    def _redraw(self, *_args) -> None:
        self.delete("all")
        w = self.winfo_width() or 1
        steps = 22
        left = COL["primary"]
        right = hex_lerp(COL["primary"], COL["accent"], 0.5)
        for i in range(steps):
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps) + 1
            self.create_rectangle(x1, 0, x2, self._h,
                                  fill=hex_lerp(left, right, i / (steps - 1)),
                                  outline="", tags="grad")
        if self._subtitle:
            self.create_text(w // 2, self._h // 2 + 6, text=self._title,
                             fill="#ffffff", font=(COL["font"], 15, "bold"),
                             tags="gtitle")
            self.create_text(w // 2, self._h // 2 + 22, text=self._subtitle,
                             fill="#ffffff", font=(COL["font"], 9),
                             tags="gsub")
        else:
            self.create_text(w // 2, self._h // 2, text=self._title,
                             fill="#ffffff", font=(COL["font"], 15, "bold"),
                             tags="gtitle")


class ProgressBar(tk.Canvas):
    """Indeterminate rounded progress bar. ``start()`` animates, ``stop()`` resets."""

    def __init__(self, parent, *, width: int = 220, height: int = 8):
        tk.Canvas.__init__(self, parent, width=width, height=height,
                           bg=COL["surface"], highlightthickness=0, bd=0)
        self._pw = width
        self._h = height
        self._pos = 0
        self._running = False
        self._anim = None
        _rrect(self, 0, 0, width, height, height, fill=COL["border"], outline="",
               tags="track")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop()

    def stop(self) -> None:
        self._running = False
        if self._anim is not None:
            try:
                self.after_cancel(self._anim)
            except Exception:
                pass
            self._anim = None
        self.delete("bar")

    def _loop(self) -> None:
        if not self._running:
            return
        self.delete("bar")
        span = 46
        self._pos = (self._pos + 4) % (self._pw + span)
        x = self._pos - span
        _rrect(self, x, 0, x + span, self._h, self._h, fill=COL["primary"],
               outline="", tags="bar")
        self._anim = self.after(28, self._loop)