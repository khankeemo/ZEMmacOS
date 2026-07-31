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

---

# ZEMmacOS SDK Integration — Full Platform Integration

**Date:** 2026-07-27
**Phase:** 1 — Complete SDK Integration & Startup Refactor

## Completed

- Full WSD_SDKToolkit_ZEMMACOS SDK integration into `main.py`
- Startup flow refactored to match `UNIVERSAL_LICENSE_PLATFORM_IMPLEMENTATION.md` architecture
- All 19 SDK Python modules imported and accessible
- `LiveLog` extracted into its own module to break circular import
- `UniversalLicenseCenter` is the single entry point for all licensing operations
- `open_activation()` and `open_renew_license()` delegate to `UniversalLicenseCenter.show()`
- Application shutdown (Rule 18) when ULC closed without resolving license
- All custom duplicate logic removed (`_run_welcome_flow`, `_show_stylish_activation_success`, `_restart_app`, `_open_reactivation_web_dialog`, `_check_aws01_condition`)

## Startup Flow

```
Application Start
    │
    ▼
ZEMmacOSApp.__init__()
    │
    ▼
root.after(100, _license_startup)
    │
    ▼
_create_splash() → splash window with "Checking license..."
    │
    ▼  (after 50ms)
_init_license_engine()  [threaded — daemon]
    │
    ├─ LicenseEngine(config_path=api-config.json)
    ├─ license_engine.get_hardware_id()
    ├─ license_engine.initialize() → LicenseStatus
    │
    ▼
Decision Engine (inside LicenseEngine.initialize())
    │
    ├── status.valid == True → _launch_main_app()
    │       │
    │       ▼
    │   _finalize_startup()
    │       build_main_ui()
    │       apply_saved_theme()
    │       root.deiconify()
    │       show_dashboard()
    │       _start_network_monitor()
    │       _show_startup_toast()
    │       _auto_fetch()
    │       _check_internet_on_startup()
    │       _update_validity_countdown (every 1s)
    │       _unlock_ui()
    │
    └── all other states → _open_ulc()
            │
            ▼
        UniversalLicenseCenter.show()
            │
            ├── result.status.valid == True → _launch_main_app()
            │
            └── ULC closed without resolution → _shutdown_app()
                    (Rule 18: stop logger, destroy root, sys.exit)
```

## Licensing Operations Flow (post-startup)

```
open_activation(license_key=None)
    │
    ▼
UniversalLicenseCenter(config_path=..., log_fn=...).show()
    │
    ├── result.status.valid → _update_all_license_ui()
    └── cancelled/error → return None

open_renew_license()
    │
    ▼
UniversalLicenseCenter(config_path=..., log_fn=...).show()
    │
    ├── result.status.valid → _update_all_license_ui()
    └── cancelled/error → return None

refresh_license()
    │
    ▼
license_engine.initialize() → new LicenseStatus
    │
    └── _update_all_license_ui()
```

## Files Changed

| File | Change |
|---|---|
| `main.py` | Full refactor of startup: `LicenseEngine.initialize()` → Decision → ULC or Main App. Removed `_run_welcome_flow`, `_show_stylish_activation_success`, `_restart_app`, `_open_reactivation_web_dialog`, `_check_aws01_condition`. Added `_license_startup`, `_create_splash`, `_init_license_engine`, `_launch_main_app`, `_finalize_startup`, `_open_ulc`, `_shutdown_app`, `_lock_ui`, `_unlock_ui`, `open_activation`, `open_renew_license`, `refresh_license`, `_update_all_license_ui`, `_update_validity_countdown`. All import statements updated for SDK modules. |
| `WSD_SDKToolkit_ZEMMACOS/__init__.py` | Added `from .livelog import LiveLog`; updated `__all__` to include `LiveLog` |
| `WSD_SDKToolkit_ZEMMACOS/universal_license_center.py` | Removed `LiveLog` class definition (moved to `livelog.py`); added `from .livelog import LiveLog` |
| `WSD_SDKToolkit_ZEMMACOS/universal_restart_dialog.py` | Changed import: `from .universal_license_center import LiveLog` → `from .livelog import LiveLog` |
| `WSD_SDKToolkit_ZEMMACOS/livelog.py` | **NEW** — Extracted `LiveLog` class to break circular import between `universal_license_center.py` and `universal_restart_dialog.py` |

## SDK Modules Connected

All 20 Python files in `WSD_SDKToolkit_ZEMMACOS/`:

| Module | Role | Imported in main.py |
|---|---|---|
| `license_engine.py` | `LicenseEngine`, `LicenseStatus` | ✅ |
| `hardware.py` | `HardwareDetector` | ✅ |
| `cache.py` | `CacheManager` | ✅ |
| `client.py` | `ApiClient`, `ApiError` | ✅ |
| `crypto.py` | Signing, timestamp, nonce | ✅ (via modules) |
| `config.py` | `load_api_config()` | ✅ |
| `livelog.py` | `LiveLog` — shared event logger | ✅ |
| `welcome.py` | `WelcomeDialog` | ✅ |
| `universal_license_center.py` | `UniversalLicenseCenter` — main licensing UI | ✅ |
| `universal_success_dialog.py` | `SuccessDialog` — post-operation success | ✅ |
| `universal_restart_dialog.py` | `RestartDialog` — post-success restart prompt | ✅ |
| `activation.py` | `activate_license()` | ✅ |
| `renewal.py` | `renew_license()` | ✅ |
| `reactivation.py` | `send_reactivation_request()` | ✅ |
| `trial.py` | `start_trial()` | ✅ |
| `communication.py` | `create_communication()` | ✅ |
| `notifications.py` | `get_notifications()` | ✅ |
| `support.py` | `send_support_request()` | ✅ |
| `sales.py` | `send_sales_enquiry()` | ✅ |

## API Integration

- **Config source:** `WSD_SDKToolkit_ZEMMACOS/config/api-config.json` — single source of truth
- **API URL:** `https://websmith-z.vercel.app` (from `api-config.json`)
- **API version:** `v1`
- **Product ID:** `prod_zemmacos`
- All API calls go through `ApiClient` in the SDK
- No hardcoded API URLs, product IDs, or branding values in `main.py`
- All branding, labels, colors loaded via `config.load_api_config()` → `branding` section

## Bug Fixes

### Circular Import: `universal_license_center.py` ↔ `universal_restart_dialog.py`

- **Root Cause:** `universal_restart_dialog.py` imported `LiveLog` from `universal_license_center.py`, while `universal_license_center.py` imported `RestartDialog` from `universal_restart_dialog.py`. This created a circular dependency that caused `ImportError` when Python tried to resolve the imports.
- **Investigation:** The `LiveLog` class was defined in `universal_license_center.py` and used by multiple modules (`universal_license_center.py` itself, `universal_restart_dialog.py`, and `welcome.py`). Since `restart_dialog` needed `LiveLog`, and `license_center` needed `RestartDialog`, neither could load first.
- **Fix:** Extracted `LiveLog` class into a standalone module `WSD_SDKToolkit_ZEMMACOS/livelog.py`. Both modules now import from `.livelog` with no circular dependency.
- **Files Modified:**
  - `WSD_SDKToolkit_ZEMMACOS/livelog.py` — created (33 lines)
  - `WSD_SDKToolkit_ZEMMACOS/__init__.py` — added `from .livelog import LiveLog`
  - `WSD_SDKToolkit_ZEMMACOS/universal_license_center.py` — removed `LiveLog` class, added `from .livelog import LiveLog`
  - `WSD_SDKToolkit_ZEMMACOS/universal_restart_dialog.py` — changed import to `from .livelog import LiveLog`
- **Verification:** All 20 SDK files parse and import without errors. Import chain test passed.

## Configuration Changes

- No changes to `api-config.json` — it was already correctly configured for `prod_zemmacos`
- `main.py` now loads config path via `_get_sdk_config_path()` → `WSD_SDKToolkit_ZEMMACOS/config/api-config.json`
- `LicenseEngine` and `UniversalLicenseCenter` both receive `config_path` parameter pointing to the config file

## Workflow Changes

### Startup Workflow (New)
```
ZEMmacOSApp.__init__()
  → root.after(100, _license_startup)
    → _create_splash()             # Splash window
    → root.after(50, _init_license_engine)
      → LicenseEngine(config_path)
      → get_hardware_id()
      → initialize()               # Decision Engine inside SDK
        → valid status             → _launch_main_app() → _finalize_startup()
        → non-valid status         → _open_ulc() → UniversalLicenseCenter.show()
        → ULC closed without valid → _shutdown_app() (Rule 18)
```

### Restart Workflow (SDK-owned)
```
Licensing operation succeeds in ULC
  → SDK shows SuccessDialog internally
  → SDK shows RestartDialog internally
  → User confirms restart
  → SDK restarts the process (sys.executable)
  → New process starts → LicenseEngine.initialize()
  → Valid license found → Main App loads
```

### Licensing Operation Workflow (SDK-owned)
```
open_activation() / open_renew_license()
  → UniversalLicenseCenter.show()
    → ULC handles: Welcome → Trial / Activation / Renewal / Reactivation
    → All OTP, validation, API calls handled internally
    → On success: SuccessDialog → RestartDialog → restart
    → On cancel/error: returns result dict
```

## UI Changes

| Change | Details |
|---|---|
| Splash screen | New `_create_splash()` — dark overlay with "ZEMmacOS" title and "Checking license..." status |
| UniversalLicenseCenter | Single entry point for all licensing — replaces old `_run_welcome_flow` and separate dialogs |
| UI Lock/Unlock | `_lock_ui()` — disables nav buttons + lock overlay. `_unlock_ui()` — re-enables nav + hides overlay + updates license displays |
| SuccessDialog | Provided by SDK — shown automatically by ULC after successful operation |
| RestartDialog | Provided by SDK — shown automatically after SuccessDialog, triggers app restart |
| Dashboard license | Updated via `_update_dashboard_license()` (inherited from `ZEMmacOSUI`) |
| Header badge | Updated via `_update_header_license_badge()` (inherited from `ZEMmacOSUI`) |
| Settings panel | Updated via `settings_ui._update_license_panel()` |

## Removed (Replaced by SDK)

| Removed Method | Replaced By |
|---|---|
| `_run_welcome_flow()` | `UniversalLicenseCenter.show()` |
| `_show_stylish_activation_success()` | SDK's `SuccessDialog` |
| `_restart_app()` | SDK's `RestartDialog` + restart logic |
| `_open_reactivation_web_dialog()` | SDK's `UniversalLicenseCenter.reactivation` workflow |
| `_check_aws01_condition()` | SDK's `LicenseEngine.initialize()` + Decision Engine |

## Decision Record

| Decision | Reason | Impact |
|---|---|---|
| `LiveLog` extracted to `livelog.py` | Circular import between `universal_license_center.py` and `universal_restart_dialog.py` | Clean dependency graph; `livelog.py` has no internal imports beyond stdlib |
| `UniversalLicenseCenter` as single licensing entry point | Architecture mandates ULC as the only customer-facing license UI | All licensing contexts (activation, renewal, settings) share same dialog, no code duplication |
| SDK owns the restart lifecycle | Global architecture defines restart as SDK responsibility after any successful operation | No app-specific restart logic; SDK handles process restart transparently |
| `LicenseStatus.from_dict()` used for deserialization | ULC returns result dict, engine returns `LicenseStatus` object | Consistent object interface regardless of origin |

## Validation

| Check | Result |
|---|---|
| Syntax Verification | All .py files pass `ast.parse()` |
| Import Verification | All 20 SDK modules import without errors in dependency order |
| Circular Import Check | No circular imports detected (import chain: crypto → hardware → cache → client → engine → livelog → welcome → success → restart → ULC → all service modules → config) |
| Package Export Check | All SDK symbols exported from `__init__.__all__` |
| Config Load Check | `api-config.json` loads via `config.load_api_config()` — product `prod_zemmacos` confirmed |
| Runtime Build Check | N/A — pending full application launch test |

## Progress

- **Completed:** 90%
  - ✅ SDK integration (all modules)
  - ✅ Startup flow refactor
  - ✅ Circular import fix
  - ✅ Config integration
  - ✅ Import verification
- **Remaining:** 10%
  - ⬜ Runtime test — launch application and verify startup flow
  - ⬜ Trial workflow test — Start Free Trial through ULC
  - ⬜ Activation workflow test — Enter license key → OTP → activate
  - ⬜ Renewal workflow test — Renew through ULC
  - ⬜ Reactivation workflow test — Reactivate through ULC
  - ⬜ Restart flow test — Verify SuccessDialog → RestartDialog → restart → main app
  - ⬜ UI lock/unlock test — Verify lock during startup and unlock after license resolved
  - ⬜ Network dialog test — Verify connectivity handling during startup
  - ⬜ Settings license panel test — Verify license info displays in settings
  - ⬜ Edge cases — No internet, expired license, invalid key, hardware change

## Known Issues

- (none currently identified)

## Blockers

- (none)

## Next Task

- Run the application to verify full startup flow end-to-end
- Test all ULC workflows: trial, activation, renewal, reactivation, support, sales, communication
- Test UI lock/unlock behavior during startup

---

## Session Summary — 2026-07-31 (AWS-01 Local SDK Validation)

### Changes in this session (local only — no Websmith template modifications)

| File | Change | Reason |
|------|--------|--------|
| `WSD_SDKToolkit_ZEMMACOS/client.py` | `get_license_status()` raises `ConnectionUnavailable` on timeout/connection errors instead of swallowing them | Engine must distinguish "offline" (→ safe cache fallback) from "backend answered" (→ backend is truth) |
| `WSD_SDKToolkit_ZEMMACOS/license_engine.py` | Server-first `initialize()`; new `_sync_status_from_server()`, `_build_status_from_unified()`, `_build_no_license_decision()`; `activate/validate/validate_hardware/start_trial/convert_trial/renew/bind_device` re-sync from `GET /internal/backend/license/status` after success; days read via `days_remaining` first; decision flags peek-first | Removes stale cached license data when the backend reports no active license; remaining days always from backend; fixes returning customers misclassified as new (TTL-aware `get()` was deleting `onboarding_complete` / `has_ever_activated_paid_license` when `cache_days: 0`) |
| `main.py` | `refresh_license()` detects valid→invalid transition → `_handle_license_revoked()` locks UI + messagebox with the backend message (fallback: "License not found or inactive. Please contact your administrator or activate a valid license.") | "Immediately remove all displayed license info and lock premium access, show message" |
| `py/main_ui.py` | Plan fallback `'Active'` → `'--'` | No hardcoded license values (plan always from backend) |

### Startup / refresh flow (after fix)

```
initialize() / refresh_license()
  → _sync_status_from_server()          # backend is single source of truth
      → licensed | trial                # build from normalized response, cache, valid
      → no_license | inactive | revoked | deleted | expired | ...
                                        # DELETE cached status + license.key, clear key,
                                        # decision: inactive / trial_consumed / no_license
      → ConnectionUnavailable (offline) # fall back to cached valid status only
  → valid → _launch_main_app()
  → invalid → _open_ulc()               # startup
  → invalid after refresh (was valid)   # _lock_ui() + messagebox (main.py)
```

### Synchronization invariant

Dashboard (`_update_dashboard_license`), header badge, Settings license panel, ULC status panel and SuccessDialog all read the SAME `LicenseStatus` instance held by `main.py`. Since the engine now always populates that object from the normalized backend response (`days_remaining`, plan, key, customer, expiry), every surface displays identical values. Nothing is computed locally.

### Verification

- 20/20 mock-API checks PASS (licensed days=365, deletion → cache cleared + inactive + required message, offline cache fallback, activate/renew sync days, trial days=14)
- `py_compile` clean on all modified files
- Grep confirms no hardcoded license values remain in `main.py` / `py/main_ui.py` / `py/settings_ui.py`; no `lic.get('days_left', 0)` patterns left in the SDK
