# ZEMmacOS Local Implementation — Logging Overlay

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  main.py  (app entry point)                                      │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  log_live(category, level, *messages)                     │   │
│  │    → LiveLog.log(category, level, " | ".join(messages))   │   │
│  └───────────────────────────────────────────────────────────┘   │
│    │                                                             │
│    │  injected as `log_fn=self.log_live` into:                   │
│    │    UniversalLicenseCenter.__init__()  (×3 instances)        │
│    └─────────────────────────────────────────────────────────┐   │
└──────────────────────────────────────────────────────────────┼───┘
                                                               │
┌──────────────────────────────────────────────────────────────▼──┐
│  WSD_SDKToolkit_ZEMMACOS/  (generated from python.ts templates) │
│                                                                  │
│  LiveLog._external_logger = callback                             │
│  LiveLog.log() → _external_logger(...) if set                    │
│                                                                  │
│  UniversalLicenseCenter.__init__(log_fn=None)                    │
│    stores self._log_fn = log_fn                                  │
│    calls LiveLog.set_external_logger(self._log_fn)               │
│                                                                  │
│  _log(category, level, *msgs) → self._log_fn                     │
│  _log_error(category, e, context) → _log + traceback             │
└──────────────────────────────────────────────────────────────────┘
                                                               │
┌──────────────────────────────────────────────────────────────▼──┐
│  py/live_log.py  (standalone LiveLog UI system)                 │
│                                                                  │
│  LiveLog class with:                                            │
│    _external_logger (class var, static)                          │
│    set_external_logger(callback)                                 │
│    log(category, level, *messages) → scrollable UI + callback    │
│                                                                  │
│  Categories:                                                     │
│    VALIDATION  (magenta) — license key validation                │
│    OTP         (cyan)    — OTP send/verify flows                 │
│    APP         (yellow)  — app-level UI events & restart         │
│    SDK         (blue)    — SDK engine init/license check         │
│    WELCOME     (green)   — welcome dialog / onboarding           │
│    ACTIVATION  (orange)  — activation API calls + confirmation   │
│    GENERAL     (gray)    — fallback                              │
└──────────────────────────────────────────────────────────────────┘
```

## Logging Points

### universal_license_center.py (SDK)

| Method | Category | Events |
|---|---|---|
| `show()` | WELCOME, SDK | License start, engine init, decision engine result, welcome dialog open, trial started/consumed, license center open |
| `_show_license_center()` | WELCOME | Opening dialog with status |
| `_start_trial()` | WELCOME | Trial button clicked, trial started, consumed, dialog closed |
| `_activate_license()` | VALIDATION | Activate clicked, request started, response received, success, failure |
| `_show_activation_confirmation()` | ACTIVATION | Confirmation dialog opened, user confirmed, closed |
| `_show_restart_prompt()` | APP | Restart prompt open, APP restart event |
| `_otp_send()` | OTP | Send clicked, request sent, verify started, verified, failure |
| `_renew_license()` | ACTIVATION | Renew exception with traceback |
| `_reactivate_license()` | ACTIVATION | Reactivation exception with traceback |

### welcome.py (SDK)

| Method | Category | Events |
|---|---|---|
| `_onboarding_complete()` | OTP | OTP send, sent, verify started, verified, failure |
| `show_onboarding()` | WELCOME | Exception with traceback |

### main.py (App)

| Context | Log calls |
|---|---|
| Root app init (`ZEMmacOS.__init__`) | 3x `UniversalLicenseCenter(log_fn=self.log_live)` |
| `_show_stylish_activation_success()` | `APP, SUCCESS` — success message |
| `_restart_app()` | `APP, INFO` — restart initiated |
| `_unlock_ui()` | `APP, INFO` — UI unlock |
| `__init__` / `_load_licensing` | Traceback on license exception |
| `start_main_app` | Traceback on exception |

## File Map

| File | Role |
|---|---|
| `python.ts` | **Source of truth** — edit here, then regenerate |
| `WSD_SDKToolkit_ZEMMACOS/*.py` | Generated output — do not edit directly |
| `main.py` | App entry — `log_fn` injection, UI/APP logs, tracebacks |
| `py/live_log.py` | LiveLog UI — categories, colors, `_external_logger` bridge |

## Regeneration Workflow

```bash
node D:\websmith\scripts\generate-sdk.mjs <output-dir>
# Copy output/*.py → WSD_SDKToolkit_ZEMMACOS/
```

Always verify with `python -m py_compile` on all changed files after regeneration.
