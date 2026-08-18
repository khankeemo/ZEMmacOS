"""Universal License Activation — standalone activation window (UI LAYER ONLY).

Restored as the full standalone activation UI (See master doc SECTION 0E and
AGENTS.md "activation.py is the full standalone Activation UI again (ROLLBACK)").
It is a UI-layer module: the window delegates every operation to LicenseEngine
(validate_license_key -> auto send_otp -> verify_otp -> activate -> refresh)
and resolves every user-visible message through GlobalMessage. It never touches
client/cache/_client directly and never embeds backend decision logic.

Required workflow (SECTION 0B/0C, LOCKED §10):
  License key -> Validate -> Backend Status -> Validation Success ->
  Auto send OTP -> OTP sent (05:00 countdown) -> Enter OTP -> Verify OTP ->
  OTP verified -> Activate -> Bind hardware -> Update license -> Refresh ->
  Success dialog -> Restart.
"""
from typing import Any, Dict, Optional

import tkinter as tk

from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .global_message import GlobalMessage
from .workflow_progress import format_timer
from .live_log import LiveLog

__all__ = [
    "activate_license",
    "validate_license",
    "deactivate_license",
    "open_activation_dialog",
    "ActivationDialog",
]


# ---------------------------------------------------------------------------
# UI.MD visual system (docs/UI.MD) — cosmetic only, no behaviour changes.
#
# Faithful Tkinter translation of the four Uiverse.io reference patterns:
#   1. Form    (Smit-Prajabati)   -> `_UIForm`: light rounded panel, soft
#                                     blue shadow, white border, cyan heading.
#   2. Card    (05akalan57)       -> `_UICard`: layered dark card (#3d3c3d
#                                     ring, #323132 inset) + corner glow.
#   3. Button  (Navarog21)        -> `_CtaButton`: #212121 face, 3px ridge
#                                     #149CEA border, collapsing bars,
#                                     #1479EA inner glow on hover.
#   4. Textbox (alexruir)         -> `_FieldInput`: rectangular field with a
#                                     slight radius (never a pill) that lights
#                                     a 2px cyan ring on focus.
#
# Brand colors follow globals.css `--api-blue-500` family — no purple.
# All activation flow logic is untouched.
# ---------------------------------------------------------------------------
from .ui_styles import COL, hex_lerp, _rrect

_FORM_BG = "#f6f8fc"
_FORM_PANEL = "#ffffff"
_FORM_EDGE = "#eef2f8"
_CYAN = "#12B1D1"      # input focus / accent
_BLUE = "#149CEA"      # Navarog button ridge
_GLOW = "#1479EA"      # Navarog button hover glow
_DARK = "#212121"      # button face
_CARD_OUT = "#3d3c3d"  # 0.card outer layer
_CARD_IN = "#323132"    # 0.card inner layer
_ON_DARK = "#ffffff"
_MUTED_DARK = "#aeb6c2"
_OK = "#22c55e"
_BRAND_LABEL = "#c9d6e4"


# ---------------------------------------------------------------------------
# 1. FORM PATTERN (Smit-Prajapati) — compact light rounded header.
# ---------------------------------------------------------------------------
class _UIForm(tk.Canvas):
    """Smit-Prajapati form header: a soft white, blue-tinted rounded strip
    with a centered cyan title (heading) and a muted subtitle."""

    def __init__(self, parent, *, title: str = "", subtitle: str = "",
                 height: Optional[int] = None):
        self._title = title
        self._subtitle = subtitle
        self._h = height or 70
        tk.Canvas.__init__(self, parent, height=self._h, bg=_FORM_BG,
                           highlightthickness=0, bd=0)
        self.bind("<Configure>", self._redraw)

    def _redraw(self, *_args) -> None:
        self.delete("all")
        w = self.winfo_width() or 1
        _rrect(self, 3, 3, w - 3, self._h - 3, 14, fill="#d5e7f3",
               outline="", tags="sh")
        _rrect(self, 6, 4, w - 6, self._h - 4, 12, fill=_FORM_PANEL,
               outline=_FORM_EDGE, width=1, tags="sh")
        if self._subtitle:
            self.create_text(w // 2, self._h // 2 + 6, text=self._title,
                             fill=_CYAN, font=(COL["font"], 18, "bold"),
                             tags="sh")
            self.create_text(w // 2, self._h // 2 + 26, text=self._subtitle,
                             fill="#5b7491", font=(COL["font"], 10),
                             tags="sh")
        else:
            self.create_text(w // 2, self._h // 2, text=self._title,
                             fill=_CYAN, font=(COL["font"], 18, "bold"),
                             tags="sh")


class _UICard(tk.Frame):
    """Layered dark card (05akalan52 reference): #3d3c3d outer ring with an
    inset #323132 body, drawn as a soft framed panel. Children pack into
    ``card.body``."""

    def __init__(self, parent, *, padx: int = 22, pady: int = 14):
        tk.Frame.__init__(self, parent, bg="#cfdde8")
        mid = tk.Frame(self, bg=_CARD_OUT)
        mid.pack(fill="both", expand=True, padx=3, pady=3)
        inner = tk.Frame(mid, bg=_CARD_IN)
        inner.pack(fill="both", expand=True, padx=3, pady=3)
        self.body = tk.Frame(inner, bg=_CARD_IN)
        self.body.pack(fill="both", expand=True, padx=padx, pady=pady)


# ---------------------------------------------------------------------------
# Dark-card helpers (phase pill, progress line, status labels)
# ---------------------------------------------------------------------------
_SECTION_FG = {
    "neutral": "#a9b4c0",
    "info": "#F2F9FF",
    "success": "#6BD59B",
    "warning": "#f2c94c",
    "error": "#ff8e8e",
    "muted": "#9aa3b0",
}


class _PhasePill(tk.Canvas):
    """Compact status chip styled for the dark card background."""

    def __init__(self, parent, *, height: int = 30):
        self._h = height
        tk.Canvas.__init__(self, parent, bg=_CARD_IN, height=height,
                           highlightthickness=0, bd=0)

    def set_text(self, text: str, kind: str = "neutral") -> None:
        self.delete("all")
        if not text:
            return
        fg = _SECTION_FG.get(kind, _SECTION_FG["neutral"])
        w = max(10, len(text)) * 8 + 34
        self.configure(width=w)
        _rrect(self, 1, 1, w, self._h, self._h // 2,
               fill=hex_lerp(fg, _CARD_IN, 0.82), outline="")
        self.create_text(w // 2, self._h // 2 + 1, text=text,
                         fill=fg, font=(COL["font"], 9, "bold"))


class _LineProgress(tk.Canvas):
    """Thin cyan indeterminate progress line designed for the dark card."""

    def __init__(self, parent, *, width: int = 420, height: int = 6):
        self._pw = width
        self._h = height
        tk.Canvas.__init__(self, parent, width=width, height=height,
                           bg=_CARD_IN, highlightthickness=0, bd=0)
        self._pos = 0
        self._running = False
        self._anim = None
        _rrect(self, 1, 1, width - 1, height - 1, height,
               fill="#41454b", outline="", tags="track")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._anim is not None:
            try:
                self.after_cancel(self._anim)
            except Exception:
                pass
            self._anim = None
        self.delete("bar")

    def _tick(self) -> None:
        if not self._running:
            return
        self.delete("bar")
        self._pos = (self._pos + 5) % (self._pw + 60)
        x = self._pos - 60
        _rrect(self, max(x, 1), 1, min(x + 60, self._pw - 1), self._h - 1,
               self._h, fill=_CYAN, outline="", tags="bar")
        self._anim = self.after(28, self._tick)


# ---------------------------------------------------------------------------
# 2. BUTTON PATTERN (Navarog21) — dark face, 3px ridge border + hover glow.
# ---------------------------------------------------------------------------
class _CtaButton(tk.Canvas):
    """Navarog21-style action button. Dark #212121 face with a 3px ridge
    #149CEA border, white bold text; hover shows the #1479EA inset glow and
    the crossing bars recede. ``kind`` ∈ {primary, success, ghost}."""

    _RIDGE = {
        "primary": _BLUE,
        "success": "#2a9d6f",
        "ghost":   hex_lerp(_CARD_IN, "#ffffff", 0.18),
    }

    def __init__(self, parent, text: str, *, kind: str = "primary",
                 command=None, width: int = 220, height: Optional[int] = None):
        self._kind = kind
        self._text = text
        self._command = command
        self._over = False
        self._pressed = False
        self._disabled = False
        self._width = width
        self._hgt = height or 42
        tk.Canvas.__init__(self, parent, width=width, height=self._hgt,
                           bg=_CARD_IN, highlightthickness=0, bd=0)
        self.bind("<Button-1>", self._press)
        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))
        self._draw()

    # -- mouse ------------------------------------------------------------
    def _on_hover(self, on: bool) -> None:
        self._over = on
        self._draw()

    def _press(self, _ev) -> None:
        if self._disabled or not self._command:
            return
        self._pressed = True
        self._draw()
        try:
            self.after(90, lambda: (setattr(self, "_pressed", False),
                                    self._draw()))
        except Exception:
            pass
        try:
            self._command()
        except Exception:
            pass

    # -- visual logic -------------------------------------------------------
    def _draw(self) -> None:
        self.delete("all")
        w = self._width
        h = self._hgt
        ridge = self._RIDGE[self._kind]
        if self._disabled:
            fill = "#2b2e33"
            ridge = "#50555c"
            fg = "#8b909a"
        elif self._pressed:
            fill = "#101113"
            fg = "#ffffff"
        elif self._kind == "ghost":
            fill = "#2a2d33"
            fg = "#dfe5ec"
        else:
            fill = _DARK
            fg = "#ffffff"
        if self._over and not self._disabled:
            fill = hex_lerp(fill, ridge, 0.12)
        step = 1
        _rrect(self, 2, 2 + step, w - 2, h - 2 + step, 8, fill=fill,
               outline="", tags="a")
        _rrect(self, 3, 3, w - 3, h - 3, 7, outline=ridge, width=2, tags="a")
        _rrect(self, 6, 6, w - 6, h - 6, 6, outline=hex_lerp(ridge, "#ffffff",
                                                            0.55), width=1,
               tags="a")
        if self._over and not self._disabled:
            _rrect(self, 3, 3, w - 3, h - 3, 7,
                   fill=hex_lerp(ridge, "#ffffff", 0.85), outline="",
                   tags="a")
            _rrect(self, 4, 4, w - 4, h - 4, 6,
                   outline=hex_lerp(ridge, _CARD_IN, 0.35), width=2,
                   tags="a")
        self.create_text(w // 2, h // 2 + 1, text=self._text, fill=fg,
                         font=(COL["font"], 11, "bold"))

    # -- public API (matches shared ui_styles.Button) ----------------------
    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def set_state(self, state: str) -> None:
        self._disabled = state == "disabled"
        self._draw()


# ---------------------------------------------------------------------------
# 3. TEXTBOX PATTERN (alex / input) — rectangular, slightly rounded, cyan focus.
# ---------------------------------------------------------------------------
class _UiEntry(tk.Canvas):
    """Rectangular input field (alexruvi reference). A normal rectangular box
    with only slightly rounded corners; transparent border lighting to a clean
    2px cyan ring on focus. Never an oval/pill."""

    def __init__(self, parent, *, width: int = 300, justify: str = "center",
                 placeholder: str = "", password: bool = False):
        self._width = width
        self._ph = placeholder
        self._password = password
        tk.Canvas.__init__(self, parent, width=width, height=40,
                           bg=_CARD_IN, highlightthickness=0, bd=0)
        self.entry = tk.Entry(
            self, font=(COL["font"], 11), justify=justify,
            relief="flat", bd=0, highlightthickness=0,
            bg="#fafcff", fg="#223047", insertbackground=_BLUE)
        if password:
            self.entry.configure(show="\u2022")
        self._win = self.create_window(width // 2, 20, window=self.entry,
                                       width=width - 10)
        self._draw(False)
        self.entry.bind("<FocusIn>", lambda e: self._draw(True))
        self.entry.bind("<FocusOut>", lambda e: self._draw(False))

    def _draw(self, focused: bool) -> None:
        tk.Canvas.delete(self, "frame")
        if focused:
            _rrect(self, 1, 1, self._width - 1, 39, 7, fill="#ffffff",
                   outline=_CYAN, width=2, tags="frame")
            _rrect(self, 3, 3, self._width - 3, 37, 6,
                   outline=hex_lerp("#ffffff", _CYAN, 0.28), width=1,
                   tags="frame")
        else:
            _rrect(self, 1, 1, self._width - 1, 39, 7, fill="#1d2022",
                   outline=hex_lerp(_CARD_IN, "#ffffff", 0.12), width=1,
                   tags="frame")

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


def activate_license(engine: LicenseEngine, license_key: str) -> Dict[str, Any]:
    return engine.activate(license_key)


def validate_license(engine: LicenseEngine, license_key: str = "") -> Dict[str, Any]:
    return engine.validate_license_key(license_key)


def deactivate_license(engine: LicenseEngine, license_key: str = "") -> Dict[str, Any]:
    return engine.deactivate(license_key)


def open_activation_dialog(center) -> None:
    """Open the standalone activation window against the given Universal License
    Center. ``center.engine`` is the single controller used for every step."""
    ActivationDialog(
        engine=center.engine,
        product_name=getattr(center, "_product_name", None) or "",
    ).show()


class ActivationDialog:
    """Standalone 'Activate your license' window.

    Pure UI: every state change comes back from the engine, and every message is
    resolved through GlobalMessage. Close cancels; success hand-off restarts
    via the shared SuccessDialog (single restart workflow).
    """

    def __init__(self, engine: LicenseEngine, product_name: Optional[str] = None):
        self.engine = engine
        self.config = getattr(engine, "config", None)
        cfg = {}
        if self.config is not None:
            try:
                cfg = self.config.raw() if hasattr(self.config, "raw") else dict(self.config)
            except Exception:
                cfg = {}
        self.product_name = product_name or (cfg.get("product", {}) or {}).get("name", "")
        self.hardware = HardwareDetector()
        self._root = None
        self._hardware_id = ""
        self._email = ""
        self._validated = False
        self._otp_verified = False
        self._otp_expires_at = 0.0
        self._otp_timer_id = None

    # -- window lifespan --------------------------------------------------
    def show(self) -> Dict[str, Any]:
        def field_label(parent, text: str) -> tk.Label:
            return tk.Label(parent, text=text, font=(COL["font"], 9, "bold"),
                            fg=_MUTED_DARK, bg=_CARD_IN, anchor="w")

        self._root = tk.Toplevel()
        self._root.title("UNIVERSAL LICENSE ACTIVATION")
        self._root.geometry("520x640")
        self._root.configure(bg=_FORM_BG)
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_closing)
        try:
            self._root.transient()
            self._root.grab_set()
        except Exception:
            pass

        _UIForm(self._root, title="Activate License",
                subtitle=self.product_name or "Universal License Engine").pack(fill="x")
        card = _UICard(self._root)
        card.pack(fill="both", expand=True)
        main = card.body

        phase = _PhasePill(main)
        phase.pack(anchor="w", pady=(0, 8))
        phase.set_text("Ready", "neutral")

        field_label(main, GlobalMessage.get("ui_enter_license_key")).pack(anchor="w", pady=(2, 4))
        key_entry = _UiEntry(main, width=460, justify="left")
        key_entry.pack(fill="x")
        if self.engine.get_license_key():
            key_entry.insert(0, self.engine.get_license_key())
        self._hardware_id = self.hardware.get_fingerprint()
        hw = tk.Label(main, text=GlobalMessage.get("ui_hardware_hint", (self._hardware_id or "")[:16] + "…"),
                      font=(COL["font"], 8), fg=_MUTED_DARK, bg=_CARD_IN, anchor="w")
        hw.pack(fill="x", pady=(4, 10))

        validate_btn = _CtaButton(main, "Validate License", kind="primary", width=200)
        validate_btn.pack(pady=(2, 6))

        status = tk.Label(main, text="", justify="center", wraplength=430,
                         font=(COL["font"], 10, "bold"), bg=_CARD_IN, fg=_ON_DARK)
        status.pack(fill="x", pady=(2, 2))
        progress = _LineProgress(main, width=430)
        progress.pack(fill="x", pady=(6, 2))
        details = tk.Label(main, text="", justify="left",
                          wraplength=430, font=(COL["font"], 9), bg=_CARD_IN, fg=_MUTED_DARK)
        details.pack(fill="x", pady=(2, 2))

        field_label(main, GlobalMessage.get("ui_otp_label")).pack(anchor="w", pady=(10, 4))
        otp_row = tk.Frame(main, bg=_CARD_IN)
        otp_row.pack(fill="x", pady=(0, 4))
        otp_entry = _UiEntry(otp_row, width=300, justify="center")
        otp_entry.pack(side="left", expand=True, fill="x")
        verify_btn = _CtaButton(otp_row, "Verify", kind="primary", width=128)
        verify_btn.pack(side="left", padx=(8, 0))

        resend_btn = _CtaButton(main, "Resend OTP", kind="ghost", width=150)
        resend_btn.pack(anchor="w", pady=(6, 2))

        # Final action
        activate_btn = _CtaButton(main, "Activate License", kind="primary", width=200)
        activate_btn.pack(pady=(12, 4))
        cancel_btn = _CtaButton(main, "Cancel", kind="ghost", width=150)
        cancel_btn.pack(pady=(0, 0))

        # Initial disabled states
        otp_entry.state("disabled")
        verify_btn.set_state("disabled")
        resend_btn.set_state("disabled")
        activate_btn.set_state("disabled")

        STATUS_FG = {
            "success": "#69d494", "error": "#ff9b9b",
            "warning": "#f2c94c", "info": "#9cd2ff",
            "muted": _MUTED_DARK, "neutral": _ON_DARK,
        }

        def _set_status(text: str, kind: str = "muted") -> None:
            status.config(text=text, fg=STATUS_FG.get(kind, COL["text"]))

        def _set_phase(text: str, kind: str = "neutral") -> None:
            phase.set_text(text, kind)

        def _cancel_otp():
            if self._otp_timer_id is not None:
                try:
                    self._root.after_cancel(self._otp_timer_id)
                except Exception:
                    pass
                self._otp_timer_id = None

        def _update_otp_timer():
            import time as _time
            _cancel_otp()
            remaining = int(self._otp_expires_at - _time.time())
            if remaining <= 0:
                self._otp_expires_at = 0.0
                _set_status(GlobalMessage.get("ui_otp_expired"), "error")
                _set_phase("OTP expired", "error")
                otp_entry.state("disabled")
                verify_btn.set_state("disabled")
                resend_btn.set_state("normal")
                return
            _set_status(
                GlobalMessage.get("ui_otp_expires_in", format_timer(remaining)),
                "info")
            self._otp_timer_id = self._root.after(1000, _update_otp_timer)

        def _validation_message(result: dict) -> str:
            status_kind = result.get("status", "")
            lic = result.get("license") or {}
            cust = result.get("customer") or {}
            err = result.get("error") or {}
            # Rule 5: pass through the server-provided message verbatim when the
            # backend supplied one (it is the source of truth for the failure).
            server_msg = result.get("message")
            if not server_msg and isinstance(err, dict):
                server_msg = err.get("message")
            if isinstance(server_msg, dict):
                server_msg = server_msg.get("message")
            if server_msg:
                return str(server_msg)
            if result.get("new_customer") or not lic:
                if not cust.get("email"):
                    return GlobalMessage.get("ui_customer_not_found")
                return GlobalMessage.get("ui_license_not_found")
            if status_kind in ("not_found", "no_license", "unlicensed", ""):
                return GlobalMessage.get("ui_license_not_found")
            if status_kind in ("inactive", "deleted", "disabled"):
                return GlobalMessage.get("ui_license_inactive")
            if status_kind == "revoked":
                return GlobalMessage.get("ui_license_revoked")
            if status_kind == "expired":
                return GlobalMessage.get("ui_license_expired")
            msg = err.get("message") if isinstance(err, dict) else None
            if msg:
                return str(msg)  # pass through real server message verbatim (Rule 5)
            return GlobalMessage.get("validation_failed")

        def do_send_otp():
            if not self._validated:
                return
            email = self._email
            if not email:
                _set_status(GlobalMessage.get("otp_no_email"), "error")
                return
            resend_btn.set_state("disabled")
            _set_status(GlobalMessage.get("ui_sending_otp"), "info")
            _set_phase("Sending OTP", "info")
            try:
                result = self.engine.send_otp(email)
            except Exception as exc:
                _set_status(str(exc), "error")
                resend_btn.set_state("normal")
                return
            if result.get("success"):
                import time as _time
                self._otp_expires_at = _time.time() + int(result.get("expires_in", 300))
                otp_entry.state("normal")
                verify_btn.set_state("normal")
                resend_btn.set_state("normal")
                _set_phase("OTP sent", "success")
                _update_otp_timer()
            else:
                msg = result.get("message") or result.get("error") or "Failed to send OTP"
                _set_status(str(msg), "error")
                resend_btn.set_state("normal")

        def do_validate():
            key = key_entry.get().strip()
            if not key:
                _set_status(GlobalMessage.get("validation_key_required"), "error")
                _set_phase("Enter a key", "error")
                return
            validate_btn.set_state("disabled")
            validate_btn.set_text("Validating…")
            _set_status(GlobalMessage.get("ui_validating"), "info")
            _set_phase("Checking license", "info")
            progress.start()
            try:
                result = self.engine.validate_license_key(key)
            except Exception as exc:
                progress.stop()
                _set_status(str(exc), "error")
                validate_btn.set_state("normal")
                validate_btn.set_text("Validate License")
                return

            cust = result.get("customer") or {}
            lic = result.get("license") or {}
            api_status = result.get("status", "")

            if result.get("already_activated"):
                progress.stop()
                LiveLog.log("ALREADY_ACTIVATED",
                            "This device already has this license")
                _set_status(GlobalMessage.get("already_activated"), "success")
                _set_phase("Already activated", "success")
                try:
                    self.engine.refresh()
                except Exception:
                    pass
                activate_btn.set_state("normal")
                return

            if result.get("new_customer"):
                progress.stop()
                _set_status(GlobalMessage.get("ui_customer_not_found"), "warning")
                _set_phase("New customer", "warning")
                validate_btn.set_state("normal")
                validate_btn.set_text("Validate License")
                return

            if not result.get("validated"):
                progress.stop()
                msg = _validation_message(result)
                LiveLog.log("operation.error", msg)
                _set_status(msg, "error")
                _set_phase("Not validated", "error")
                validate_btn.set_state("normal")
                validate_btn.set_text("Validate License")
                otp_entry.state("disabled")
                verify_btn.set_state("disabled")
                resend_btn.set_state("disabled")
                activate_btn.set_state("disabled")
                self._validated = False
                return

            progress.stop()
            self._validated = True
            self._otp_verified = False
            self._email = cust.get("email", "")
            validate_btn.set_state("normal")
            validate_btn.set_text("Validate License")

            lines = []
            if cust.get("name"):
                lines.append("Customer: %s" % cust["name"])
            if self._email:
                lines.append("Email: %s" % self._email)
            if self.product_name:
                lines.append("Product: %s" % self.product_name)
            if lic.get("plan"):
                lines.append("Plan: %s" % lic["plan"])
            if lic.get("expiry_date"):
                lines.append("Expiry: %s" % lic["expiry_date"])
            rem = lic.get("days_remaining")
            if rem is None:
                rem = lic.get("days_left")
            if rem is not None:
                lines.append("Days remaining: %s" % rem)
            if not lines:
                lines.append(GlobalMessage.get("ui_license_active"))
            details.config(text="\n".join(lines))

            _set_status(GlobalMessage.get("ui_sending_otp"), "info")
            LiveLog.log("activation.validated", "License validated — auto-sending OTP")
            _set_phase("Validated", "success")
            do_send_otp()

        def do_verify():
            if not self._validated:
                return
            otp = otp_entry.get().strip()
            if not otp or len(otp) < 4:
                _set_status(GlobalMessage.get("otp_required"), "error")
                return
            verify_btn.set_state("disabled")
            verify_btn.set_text("Verifying…")
            try:
                result = self.engine.verify_otp(self._email, otp)
            except Exception as exc:
                _set_status(str(exc), "error")
                verify_btn.set_state("normal")
                verify_btn.set_text("Verify")
                return
            if result.get("success"):
                self._otp_verified = True
                verify_btn.set_state("normal")
                verify_btn.set_text("Verify")
                otp_entry.state("disabled")
                activate_btn.set_state("normal")
                _set_status(GlobalMessage.get("ui_otp_verified"), "success")
                _set_phase("OTP verified", "success")
            else:
                otp_entry.delete(0, "end")
                _set_status(GlobalMessage.get("ui_otp_invalid"), "error")
                verify_btn.set_state("normal")
                verify_btn.set_text("Verify")
                otp_entry.focus_set()

        def finish_success() -> None:
            steps = [
                (GlobalMessage.get("ui_creating_activation"), "info"),
                (GlobalMessage.get("ui_updating_license"), "info"),
                (GlobalMessage.get("ui_refreshing_license"), "info"),
                (GlobalMessage.get("ui_updating_application"), "info"),
            ]
            for text, kind in steps:
                _set_status(text, kind)
                _set_phase("In progress", "info")
                try:
                    self._root.update()
                except Exception:
                    pass
                self._root.after(110)
            progress.stop()
            _set_status(GlobalMessage.get("ui_activation_completed"), "success")
            _set_phase("Completed", "success")
            self._root.after(160)
            try:
                self.engine.refresh()
            except Exception:
                pass
            status_obj: Optional[LicenseStatus] = None
            try:
                status_obj = self.engine.get_status()
            except Exception:
                status_obj = None
            if status_obj is None:
                self._root.destroy()
                return
            LiveLog.log("Showing Success Dialog", "Operation: activation")
            from .universal_success_dialog import SuccessDialog
            try:
                SuccessDialog(
                    parent=self._root,
                    status=status_obj,
                    product_name=self.product_name,
                    operation="activation",
                    engine=self.engine,
                ).show()
            except Exception:
                try:
                    self._root.destroy()
                except Exception:
                    pass

        def do_activate():
            if not self._validated or not self._otp_verified:
                return
            key = key_entry.get().strip()
            activate_btn.set_state("disabled")
            activate_btn.set_text("Activating…")
            _set_status(GlobalMessage.get("ui_binding_hardware"), "info")
            _set_phase("Binding hardware", "info")
            progress.start()
            try:
                result = self.engine.activate(key)
            except Exception as exc:
                progress.stop()
                _set_status(str(exc), "error")
                activate_btn.set_state("normal")
                activate_btn.set_text("Activate License")
                return
            if result.get("success") or result.get("already_activated"):
                LiveLog.log("activation.success", "License activated on this device")
                finish_success()
            else:
                progress.stop()
                err = result.get("error") or result.get("data") or result
                msg = err.get("message") if isinstance(err, dict) else str(err)
                if not msg:
                    msg = (GlobalMessage.get("activation_failed") + " "
                           "Please contact support.")
                LiveLog.log("operation.error", msg)
                _set_status(str(msg), "error")
                _set_phase("Failed", "error")
                activate_btn.set_state("normal")
                activate_btn.set_text("Activate License")

        validate_btn._command = do_validate
        verify_btn._command = do_verify
        resend_btn._command = do_send_otp
        activate_btn._command = do_activate
        cancel_btn._command = self._on_closing
        key_entry.entry.bind("<Return>", lambda e: do_validate())
        otp_entry.entry.bind("<Return>", lambda e: do_verify())
        self._root.after(60, key_entry.focus_set)
        self._root.wait_window()
        return {"activated": bool(self._validated and self._otp_verified)}

    # -------------------------------------------------------------------
    def _on_closing(self):
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:
                pass

    def _on_cancel(self):
        self._on_closing()