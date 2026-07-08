import tkinter as tk
import math
import time


class RoundedRect:
    """Utility to draw rounded rectangles on a canvas"""

    @staticmethod
    def create(canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = []
        r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        steps = 16
        for i in range(steps + 1):
            a = math.pi + (math.pi * i) / (2 * steps)
            points.append((x1 + r + r * math.cos(a), y1 + r + r * math.sin(a)))
        for i in range(steps + 1):
            a = -math.pi / 2 + (math.pi * i) / (2 * steps)
            points.append((x2 - r + r * math.cos(a), y1 + r + r * math.sin(a)))
        for i in range(steps + 1):
            a = 0 + (math.pi * i) / (2 * steps)
            points.append((x2 - r + r * math.cos(a), y2 - r + r * math.sin(a)))
        for i in range(steps + 1):
            a = math.pi / 2 + (math.pi * i) / (2 * steps)
            points.append((x1 + r + r * math.cos(a), y2 - r + r * math.sin(a)))
        flat = [coord for p in points for coord in p]
        return canvas.create_polygon(flat, smooth=True, **kwargs)


class ModernCard(tk.Frame):
    """Premium card with shadow effect, rounded corners, and hover lift"""

    def __init__(self, parent, colors, title=None, subtitle=None, width=None, height=None, hover_raise=True, padding=20, **kwargs):
        super().__init__(parent, bg=colors["content_bg"], **kwargs)
        self.colors = colors
        self._hover_raise = hover_raise
        self._lifted = False
        self._shadow_items = []

        inner = tk.Frame(self, bg=colors["card_bg"])
        inner._role = "card"
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=3)

        self._canvas = tk.Canvas(inner, bg=colors["card_bg"], highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._content = tk.Frame(self._canvas, bg=colors["card_bg"])
        self._content._role = "card"

        self._canvas_frame = self._canvas.create_window((0, 0), window=self._content, anchor="nw", width=self._canvas.winfo_width())

        if title:
            self._title_bar = tk.Frame(self._content, bg=colors["card_bg"])
            self._title_bar.pack(fill=tk.X, padx=padding, pady=(padding - 4, 2))
            if subtitle:
                tk.Label(self._title_bar, text=title, font=("SF Pro Text", 14, "bold"), fg=colors["text"], bg=colors["card_bg"]).pack(anchor=tk.W)
                tk.Label(self._title_bar, text=subtitle, font=("SF Pro Text", 10), fg=colors["muted"], bg=colors["card_bg"]).pack(anchor=tk.W)
            else:
                tk.Label(self._title_bar, text=title, font=("SF Pro Text", 14, "bold"), fg=colors["text"], bg=colors["card_bg"]).pack(anchor=tk.W)
            sep = tk.Frame(self._content, bg=colors["border"], height=1)
            sep.pack(fill=tk.X, padx=padding)

        self._body = tk.Frame(self._content, bg=colors["card_bg"])
        self._body.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)

        self._config_after_id = None

        def on_enter(e):
            if self._hover_raise and not self._lifted:
                self._lift(True)
        def on_leave(e):
            if self._hover_raise and self._lifted:
                self._lift(False)
        inner.bind("<Enter>", on_enter)
        inner.bind("<Leave>", on_leave)
        self._canvas.bind("<Enter>", on_enter)
        self._canvas.bind("<Leave>", on_leave)
        self._content.bind("<Enter>", on_enter)
        self._content.bind("<Leave>", on_leave)

        self.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Configure>", self._on_resize)

        if width:
            self.config(width=width)
        if height:
            self.config(height=height)

        self.after(50, self._draw)

    def _on_resize(self, event=None):
        if self._config_after_id:
            self.after_cancel(self._config_after_id)
        self._config_after_id = self.after(50, self._draw)

    def _draw(self):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 10 or ch < 10:
            self.after(100, self._draw)
            return
        self._canvas.delete("all")
        self._canvas.itemconfig(self._canvas_frame, width=cw)
        colors = self.colors

        lift_offset = 3 if self._lifted else 0

        shadow_color = colors.get("shadow_color", "#000000")
        RoundedRect.create(self._canvas, 2, 4 + lift_offset, cw - 2, ch + 2 + lift_offset,
                          radius=14, fill=shadow_color, outline="", stipple="gray25", tags="shadow")

        RoundedRect.create(self._canvas, 2, 3 + lift_offset, cw - 2, ch + 1 + lift_offset,
                          radius=14, fill=shadow_color, outline="", stipple="gray50", tags="shadow")

        RoundedRect.create(self._canvas, 2, 2 + lift_offset, cw - 2, ch + lift_offset,
                          radius=14, fill=shadow_color, outline="", stipple="gray75", tags="shadow")

        RoundedRect.create(self._canvas, 1, 1, cw - 1, ch - 1,
                          radius=14, fill=colors["card_bg"], outline=colors["border"], width=1, tags="body")

    def _lift(self, up):
        self._lifted = up
        self._draw()

    def body(self):
        return self._body

    def get_body(self):
        return self._body


class ModernButton(tk.Canvas):
    """Premium button with rounded rect, hover effect"""

    def __init__(self, parent, text, command=None, colors=None, bg_color=None, fg_color=None, width=None, height=36, radius=8, font_size=11, bold=True, **kwargs):
        self._colors = colors or {}
        self._bg = bg_color or self._colors.get("accent", "#0071e3")
        self._fg = fg_color or "#ffffff"
        self._hover_bg = self._colors.get("accent_hover", "#0077ed")
        self._text = text
        self._command = command
        self._radius = radius
        self._font = ("SF Pro Text", font_size, "bold" if bold else "normal")
        self._hovered = False
        self._disabled = False

        super().__init__(parent, bg=self._colors.get("card_bg", "#ffffff") if not bg_color else self._colors.get("content_bg", "#f5f5f7"),
                         highlightthickness=0, bd=0, cursor="hand2", **kwargs)

        if width:
            self.config(width=width)
        self.config(height=height)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)

        self.after(10, self._redraw)

    def _redraw(self):
        self.delete("all")
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 10:
            self.after(50, self._redraw)
            return
        bg = self._hover_bg if self._hovered else self._bg
        RoundedRect.create(self, 1, 1, cw - 1, ch - 1, radius=self._radius, fill=bg, outline="", tags="btn_bg")
        self.create_text(cw // 2, ch // 2, text=self._text, font=self._font, fill=self._fg, tags="btn_text")

    def _on_enter(self, e):
        if not self._disabled:
            self._hovered = True
            self._redraw()

    def _on_leave(self, e):
        self._hovered = False
        self._redraw()

    def _on_click(self, e):
        if not self._disabled:
            self._redraw()

    def _on_release(self, e):
        if not self._disabled and self._command:
            self._command()

    def set_disabled(self, disabled):
        self._disabled = disabled
        if disabled:
            self._hover_bg = self._bg
            self._hovered = False
            self.config(cursor="arrow")
        else:
            self._hover_bg = self._colors.get("accent_hover", "#0077ed")
            self.config(cursor="hand2")
        self._redraw()

    def config(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self._redraw()
        if "state" in kwargs:
            self.set_disabled(kwargs.pop("state") == tk.DISABLED)
        if "bg" in kwargs:
            self._bg = kwargs.pop("bg")
            self._redraw()
        if "fg" in kwargs:
            self._fg = kwargs.pop("fg")
            self._redraw()
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        super().config(**kwargs)


class ModernProgressBar(tk.Frame):
    """Smooth animated progress bar using canvas"""

    def __init__(self, parent, colors, height=8, radius=4, **kwargs):
        super().__init__(parent, bg=colors.get("content_bg", "#f5f5f7"), **kwargs)
        self.colors = colors
        self._value = 0.0
        self._target = 0.0
        self._height = height
        self._radius = radius
        self._animating = False

        self._canvas = tk.Canvas(self, bg=colors.get("progress_bg", "#e9e9ed"),
                                 highlightthickness=0, bd=0, height=height)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda e: self._redraw())

        self.after(50, self._redraw)

    def _redraw(self):
        self._canvas.delete("all")
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 10:
            self.after(50, self._redraw)
            return

        RoundedRect.create(self._canvas, 0, 0, cw, ch, radius=self._radius,
                          fill=self.colors.get("progress_bg", "#e9e9ed"), outline="", tags="track")

        fill_w = int(cw * (self._value / 100.0))
        if fill_w > self._radius * 2:
            RoundedRect.create(self._canvas, 0, 0, fill_w, ch, radius=self._radius,
                              fill=self.colors.get("progress_fill", "#0071e3"), outline="", tags="fill")
        elif fill_w > 0:
            r = min(self._radius, fill_w // 2) if fill_w < self._radius * 2 else self._radius
            RoundedRect.create(self._canvas, 0, 0, fill_w, ch, radius=r,
                              fill=self.colors.get("progress_fill", "#0071e3"), outline="", tags="fill")

    def set_value(self, value, animate=True):
        value = max(0.0, min(100.0, value))
        self._target = value
        if animate and abs(self._value - value) > 0.5:
            if not self._animating:
                self._animating = True
                self._animate_step()
        else:
            self._value = value
            self._redraw()

    def _animate_step(self):
        diff = self._target - self._value
        if abs(diff) < 0.3:
            self._value = self._target
            self._animating = False
            self._redraw()
            return
        self._value += diff * 0.25
        self._redraw()
        self.after(16, self._animate_step)


class AnimatedCounter(tk.Frame):
    """Count-up number animation"""

    def __init__(self, parent, colors, font=("SF Pro Display", 26, "bold"), fg=None, prefix="", suffix="", **kwargs):
        super().__init__(parent, bg=colors.get("card_bg", "#ffffff"), **kwargs)
        self.colors = colors
        self._current = 0.0
        self._target = 0.0
        self._prefix = prefix
        self._suffix = suffix
        self._animating = False

        self._label = tk.Label(self, text=f"{prefix}0{suffix}", font=font,
                               fg=fg or colors.get("accent", "#0071e3"),
                               bg=colors.get("card_bg", "#ffffff"))
        self._label.pack()

    def set_value(self, value, animate=True):
        self._target = float(value)
        if animate and abs(self._current - self._target) > 1:
            if not self._animating:
                self._animating = True
                self._animate_step()
        else:
            self._current = self._target
            self._label.config(text=f"{self._prefix}{int(self._target)}{self._suffix}")

    def _animate_step(self):
        diff = self._target - self._current
        if abs(diff) < 0.5:
            self._current = self._target
            self._animating = False
            self._label.config(text=f"{self._prefix}{int(self._target)}{self._suffix}")
            return
        self._current += diff * 0.2
        self._label.config(text=f"{self._prefix}{int(self._current)}{self._suffix}")
        self.after(20, self._animate_step)

    def config(self, **kwargs):
        if "fg" in kwargs:
            self._label.config(fg=kwargs.pop("fg"))
        if "text" in kwargs:
            self._label.config(text=kwargs.pop("text"))
        super().config(**kwargs)


class StatusBadge(tk.Frame):
    """Modern status badge with colored background"""

    def __init__(self, parent, colors, text="Ready", status="idle", **kwargs):
        super().__init__(parent, bg=colors.get("card_bg", "#ffffff"), **kwargs)
        self.colors = colors
        self._status = status
        self._text = text

        self._status_map = {
            "downloading": (colors.get("info_bg", "#e8f4fd"), colors.get("info", "#0071e3"), "Downloading"),
            "paused": (colors.get("warning_bg", "#fff4e5"), colors.get("warning", "#ff9f0a"), "Paused"),
            "completed": (colors.get("success_bg", "#e8f8ed"), colors.get("success", "#34c759"), "Completed"),
            "failed": (colors.get("error_bg", "#fde8e8"), colors.get("error", "#ff3b30"), "Failed"),
            "cancelled": (colors.get("error_bg", "#fde8e8"), colors.get("muted", "#86868b"), "Cancelled"),
            "idle": (colors.get("card_bg", "#ffffff"), colors.get("muted", "#86868b"), "Ready"),
        }

        bg_c, fg_c, _ = self._status_map.get(status, self._status_map["idle"])
        if text != "Ready":
            _, _, display = self._status_map.get(status, self._status_map["idle"])
            display = text if text else display

        self._badge = tk.Label(self, text=text or "Ready", font=("SF Pro Text", 9, "bold"),
                               fg=fg_c, bg=bg_c, padx=8, pady=2)
        self._badge.pack()

    def set_status(self, status, text=None):
        bg_c, fg_c, default = self._status_map.get(status, self._status_map["idle"])
        display = text or default
        self._badge.config(text=display, fg=fg_c, bg=bg_c)
