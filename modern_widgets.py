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
            bar.pack(fill=tk.X, padx=padding, pady=padding)
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
    """Premium sun/moon theme toggle switch with matching background"""

    def __init__(self, parent, command=None, colors=None, **kwargs):
        c = colors or {}
        bg = c.get("header_bg", "#f5f5f7")
        super().__init__(parent, width=56, height=30,
                         bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2", **kwargs)
        self._role = "header"
        self._command = command
        self._colors = c
        self._is_dark = False
        self._animating = False
        self._anim_step = 0

        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._draw(hover=True))
        self.bind("<Leave>", lambda e: self._draw(hover=False))
        self._hover = False
        self.after(20, self._draw)

    def _draw(self, hover=False):
        self.delete("all")
        cw = max(self.winfo_width(), 56)
        ch = max(self.winfo_height(), 30)
        r = ch / 2 - 3
        cy = ch / 2

        bg = self._colors.get("header_bg", "#f5f5f7")
        self.configure(bg=bg)

        if self._is_dark:
            track_fill = "#3a3a3c"
            knob_fill = "#636366" if not hover else "#7c7c80"
            icon = "\U0001f319"
            icon_fill = "#ffd60a"
        else:
            track_fill = "#c7c7cc" if not hover else "#a8a8ad"
            knob_fill = "#ffffff"
            icon = "\u2600\ufe0f"
            icon_fill = "#ff9500"

        track_r = ch / 2 - 1
        outline = self._colors.get("border", "#e0e0e0")
        self.create_rounded_rect(1, 1, cw - 1, ch - 1, track_r,
                                 fill=track_fill, outline=outline, width=1)

        knob_x = r + 3 if not self._is_dark else cw - r - 3
        self.create_oval(knob_x - r, cy - r, knob_x + r, cy + r,
                         fill=knob_fill, outline=self._colors.get("border", "#d1d1d6"),
                         width=1, tags="knob")

        fs = max(10, int(r * 1.2))
        self.create_text(knob_x, cy, text=icon, font=("Segoe UI", fs),
                         fill=icon_fill, tags="icon")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        steps = 10
        points = []
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


class DebugConsole(tk.Frame):
    """Collapsible developer debug log panel"""

    LEVEL_COLORS = {
        "INFO": "#0071e3",
        "SUCCESS": "#34c759",
        "WARNING": "#ff9f0a",
        "ERROR": "#ff3b30",
        "DEBUG": "#86868b",
        "NETWORK": "#af52de",
        "DOWNLOAD": "#ff6482",
        "SYSTEM": "#5ac8fa",
    }

    CAT_COLORS = {
        "APP": "#5ac8fa",
        "CATALOGUE": "#ff9f0a",
        "NETWORK": "#af52de",
        "DOWNLOAD": "#ff6482",
        "RESUME": "#34c759",
        "PERFORMANCE": "#0071e3",
    }

    def __init__(self, parent, colors, height=140, **kwargs):
        super().__init__(parent, bg=colors.get("card_bg", "#ffffff"), **kwargs)
        self._colors = colors
        self._paused = False
        self._autoscroll = True
        self._collapsed = False
        self._full_height = height

        header = tk.Frame(self, bg=colors.get("content_bg", "#f5f5f7"))
        header.pack(fill=tk.X)
        self._collapse_btn = tk.Button(header, text="\u25bc Debug Console",
                                       command=self._toggle_collapse,
                                       font=("SF Pro Text", 9, "bold"),
                                       fg=colors.get("muted", "#86868b"),
                                       bg=colors.get("content_bg", "#f5f5f7"),
                                       bd=0, anchor="w", padx=10, pady=4, cursor="hand2")
        self._collapse_btn.pack(side=tk.LEFT)

        ctrl_frame = tk.Frame(header, bg=colors.get("content_bg", "#f5f5f7"))
        ctrl_frame.pack(side=tk.RIGHT, padx=4)
        for text, cmd in [
            ("Copy", self.copy),
            ("Clear", self.clear),
            ("Export", self.export),
            ("Pause", self._toggle_pause),
            ("Auto", self._toggle_autoscroll),
        ]:
            tk.Button(ctrl_frame, text=text, command=cmd,
                      font=("SF Pro Text", 8), fg=colors.get("text", "#1d1d1f"),
                      bg=colors.get("btn_secondary_bg", "#e5e5ea"),
                      bd=1, relief=tk.FLAT, padx=8, pady=1, cursor="hand2"
                      ).pack(side=tk.LEFT, padx=2)

        self._log_frame = tk.Frame(self, bg=colors.get("card_bg", "#ffffff"))
        self._log_frame.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(
            self._log_frame,
            font=("SF Mono", 9),
            bg=colors.get("input_bg", "#ffffff"),
            fg=colors.get("text", "#1d1d1f"),
            bd=0, relief=tk.FLAT, height=6,
            wrap=tk.WORD, state=tk.DISABLED,
        )
        scrollbar = tk.Scrollbar(self._log_frame, orient=tk.VERTICAL,
                                 command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        for name, clr in self.LEVEL_COLORS.items():
            self._log_text.tag_config(f"level_{name}", foreground=clr, font=("SF Mono", 9, "bold"))
        for name, clr in self.CAT_COLORS.items():
            self._log_text.tag_config(f"cat_{name}", foreground=clr)
        self._log_text.tag_config("timestamp", foreground="#888888")
        self._log_text.tag_config("detail", foreground="#6e6e73")

    def log(self, category, level, message, detail=None):
        if self._paused:
            return
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        level_key = level.upper() if level.upper() in self.LEVEL_COLORS else "INFO"
        cat_key = category.upper() if category.upper() in self.CAT_COLORS else "APP"
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._log_text.insert(tk.END, f"[{cat_key}] ", f"cat_{cat_key}")
        self._log_text.insert(tk.END, f"[{level_key}] ", f"level_{level_key}")
        self._log_text.insert(tk.END, f"{message}\n")
        if detail:
            self._log_text.insert(tk.END, f"  {detail}\n", "detail")
        if self._autoscroll:
            self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def clear(self):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete(1.0, tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def copy(self):
        self._log_text.configure(state=tk.NORMAL)
        try:
            content = self._log_text.get(1.0, tk.END)
            self.clipboard_clear()
            self.clipboard_append(content)
        except:
            pass
        self._log_text.configure(state=tk.DISABLED)

    def export(self):
        from tkinter import filedialog, messagebox
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                self._log_text.configure(state=tk.NORMAL)
                content = self._log_text.get(1.0, tk.END)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._log_text.configure(state=tk.DISABLED)
                messagebox.showinfo("Export", f"Log saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _toggle_pause(self):
        self._paused = not self._paused

    def _toggle_autoscroll(self):
        self._autoscroll = not self._autoscroll

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._log_frame.pack_forget()
            self._collapse_btn.config(text="\u25b6 Debug Console")
        else:
            self._log_frame.pack(fill=tk.BOTH, expand=True)
            self._collapse_btn.config(text="\u25bc Debug Console")
