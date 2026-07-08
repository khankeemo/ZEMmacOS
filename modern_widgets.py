import tkinter as tk
from tkinter import ttk
import math


class ModernCard(tk.Frame):
    """Premium card with clean border styling"""

    def __init__(self, parent, colors, title=None, subtitle=None, padding=18, **kwargs):
        super().__init__(parent, bg=colors["content_bg"], **kwargs)
        self._card = tk.Frame(self, bg=colors["card_bg"],
                              highlightbackground=colors["border"],
                              highlightthickness=1)
        self._card._role = "card"
        self._card.pack(fill=tk.BOTH, expand=True)

        if title:
            bar = tk.Frame(self._card, bg=colors["card_bg"])
            bar.pack(fill=tk.X, padx=padding, pady=(padding - 4, 2))
            if subtitle:
                tk.Label(bar, text=title, font=("SF Pro Text", 14, "bold"),
                         fg=colors["text"], bg=colors["card_bg"]).pack(anchor=tk.W)
                tk.Label(bar, text=subtitle, font=("SF Pro Text", 10),
                         fg=colors["muted"], bg=colors["card_bg"]).pack(anchor=tk.W)
            else:
                tk.Label(bar, text=title, font=("SF Pro Text", 14, "bold"),
                         fg=colors["text"], bg=colors["card_bg"]).pack(anchor=tk.W)
            sep = tk.Frame(self._card, bg=colors["border"], height=1)
            sep.pack(fill=tk.X, padx=padding)

        self._body = tk.Frame(self._card, bg=colors["card_bg"])
        self._body.pack(fill=tk.BOTH, expand=True,
                        padx=padding, pady=(padding if not title else padding - 4))

    def get_body(self):
        return self._body


class ModernProgressBar(tk.Frame):
    """Smooth animated progress bar"""

    def __init__(self, parent, colors, height=8, **kwargs):
        super().__init__(parent, bg=colors.get("content_bg", "#f5f5f7"), **kwargs)
        self._value = 0.0
        self._target = 0.0
        self._animating = False

        clr = ttk.Style()
        clr.configure("Smooth.Horizontal.TProgressbar",
                      background=colors.get("progress_fill", "#0071e3"),
                      troughcolor=colors.get("progress_bg", "#e9e9ed"),
                      borderwidth=0, thickness=height)

        self._bar = ttk.Progressbar(self, mode="determinate",
                                    style="Smooth.Horizontal.TProgressbar")
        self._bar.pack(fill=tk.X, expand=True)

    def set_value(self, value, animate=True):
        value = max(0.0, min(100.0, value))
        self._target = value
        if animate and abs(self._value - value) > 0.5:
            if not self._animating:
                self._animating = True
                self._animate_step()
        else:
            self._value = value
            self._bar["value"] = value

    def _animate_step(self):
        diff = self._target - self._value
        if abs(diff) < 0.3:
            self._value = self._target
            self._bar["value"] = self._target
            self._animating = False
            return
        self._value += diff * 0.25
        self._bar["value"] = self._value
        self.after(16, self._animate_step)


class StatusBadge(tk.Frame):
    """Status badge with colored label"""

    def __init__(self, parent, colors, text="Ready", status="idle", **kwargs):
        super().__init__(parent, bg=colors.get("card_bg", "#ffffff"), **kwargs)
        self._status_map = {
            "downloading": (colors.get("info_bg", "#e8f4fd"), colors.get("info", "#0071e3")),
            "paused":      (colors.get("warning_bg", "#fff4e5"), colors.get("warning", "#ff9f0a")),
            "completed":   (colors.get("success_bg", "#e8f8ed"), colors.get("success", "#34c759")),
            "failed":      (colors.get("error_bg", "#fde8e8"), colors.get("error", "#ff3b30")),
            "cancelled":   (colors.get("card_bg", "#ffffff"), colors.get("muted", "#86868b")),
            "idle":        (colors.get("card_bg", "#ffffff"), colors.get("muted", "#86868b")),
        }
        bg_c, fg_c = self._status_map.get(status, self._status_map["idle"])
        self._label = tk.Label(self, text=text, font=("SF Pro Text", 9, "bold"),
                               fg=fg_c, bg=bg_c, padx=8, pady=2)
        self._label.pack()

    def set_status(self, status, text=None):
        bg_c, fg_c = self._status_map.get(status, self._status_map["idle"])
        self._label.config(text=text or status.capitalize(), fg=fg_c, bg=bg_c)


class ThemeToggle(tk.Canvas):
    """Animated sun/moon theme toggle switch"""

    def __init__(self, parent, command=None, colors=None, **kwargs):
        bg = (colors or {}).get("btn_secondary_bg", "#e5e5ea")
        super().__init__(parent, width=56, height=30,
                         bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2", **kwargs)
        self._command = command
        self._colors = colors or {}
        self._is_dark = False
        self._animating = False
        self._anim_step = 0

        self.bind("<Button-1>", self._on_click)
        self.after(20, self._draw)

    def _draw(self):
        self.delete("all")
        cw = self.winfo_width() or 56
        ch = self.winfo_height() or 30
        r = ch / 2 - 2
        cx = cw / 2
        cy = ch / 2

        bg = self._colors.get("btn_secondary_bg", "#e5e5ea")
        self.configure(bg=bg)

        track_r = ch / 2
        self.create_rounded_rect(1, 1, cw - 1, ch - 1, track_r,
                                 fill=bg if not self._is_dark else "#3a3a3c", outline="")

        knob_x = r + 2 if not self._is_dark else cw - r - 2
        knob_color = "#ffcc00" if not self._is_dark else "#8e8e93"

        self.create_oval(knob_x - r, cy - r, knob_x + r, cy + r,
                         fill=knob_color, outline="", tags="knob")

        if self._is_dark:
            self.create_text(knob_x - 1, cy - 1, text="\u2601\ufe0f",
                             font=("Segoe UI", 8), fill="white", tags="icon")
        else:
            self.create_text(knob_x + 1, cy - 1, text="\u2600\ufe0f",
                             font=("Segoe UI", 8), fill="#1a1a1a", tags="icon")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = []
        steps = 12
        for i in range(steps + 1):
            a = math.pi + (math.pi * i) / (2 * steps)
            points.extend([x1 + r + r * math.cos(a), y1 + r + r * math.sin(a)])
        for i in range(steps + 1):
            a = -math.pi / 2 + (math.pi * i) / (2 * steps)
            points.extend([x2 - r + r * math.cos(a), y1 + r + r * math.sin(a)])
        for i in range(steps + 1):
            a = 0 + (math.pi * i) / (2 * steps)
            points.extend([x2 - r + r * math.cos(a), y2 - r + r * math.sin(a)])
        for i in range(steps + 1):
            a = math.pi / 2 + (math.pi * i) / (2 * steps)
            points.extend([x1 + r + r * math.cos(a), y2 - r + r * math.sin(a)])
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_click(self, e):
        self._is_dark = not self._is_dark
        if not self._animating:
            self._animating = True
            self._anim_step = 0
            self._animate_knob()
        if self._command:
            self._command()

    def _animate_knob(self):
        self._anim_step += 1
        self._draw()
        if self._anim_step < 6:
            self.after(30, self._animate_knob)
        else:
            self._animating = False

    def set_theme(self, is_dark):
        self._is_dark = is_dark
        self._draw()

    def toggle(self):
        self._is_dark = not self._is_dark
        self._draw()
