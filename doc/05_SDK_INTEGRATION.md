# 5. SDK Integration

## 5.1 Integration architecture

```
                 ┌─────────────────────────────────────────────┐
                 │              main.py (ZEMmacOS)             │
                 │                                             │
                 │  import WSD_SDKToolkit_ZEMMACOS             │
                 │     LicenseEngine, LicenseStatus,           │
                 │     UniversalLicenseCenter, ...             │
                 │                                             │
                 │  ZEMmacOSApp (subclass of ZEMmacOSUI)       │
                 │   ├─ startup: _license_startup              │
                 │   ├─ engine init: _init_license_engine      │
                 │   ├─ ULC open: _open_ulc / open_activation  │
                 │   │              / open_renew_license       │
                 │   ├─ refresh:  refresh_license              │
                 │   └─ shutdown: _shutdown_app / on_closing   │
                 └───────────────────┬─────────────────────────┘
                                     │  public APIs + callbacks + events
                 ┌───────────────────▼─────────────────────────┐
                 │      WSD_SDKToolkit_ZEMMACOS (READ-ONLY)    │
                 │                                             │
                 │  LicenseEngine ── ApiClient ── HTTP(S)      │
                 │       │            └── HardwareDetector     │
                 │       ├── CacheManager  (~/.websmith)       │
                 │       ├── EventBus ──> LicenseStatusChanged │
                 │       └── LiveLog   ──> app logger bridge   │
                 │                                             │
                 │  UniversalLicenseCenter + dialogs           │
                 └───────────────────┬─────────────────────────┘
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │   Websmith Digital Internal API (backend)   │
                 │   single source of truth for license state  │
                 └─────────────────────────────────────────────┘
```

ZEMmacOS never talks to the backend directly. Every licensing operation goes through the
SDK public interface. The SDK owns license logic, cache, hardware binding, dialogs, OTP,
trial, renewal, activation, reactivation, and notifications.

## 5.2 Configuration source

- **SDK config path** — `WSD_SDKToolkit_ZEMMACOS/config/api-config.json`, resolved by
  `main.py::_get_sdk_config_path()`.
- The same path is passed to `LicenseEngine(config_path=...)` and every
  `UniversalLicenseCenter(config_path=...)` instance.

## 5.3 SDK public interface used by ZEMmacOS

Imported in `main.py`:

```python
from WSD_SDKToolkit_ZEMMACOS import (
    LicenseEngine, LicenseStatus, UniversalLicenseCenter,
    WelcomeDialog, SuccessDialog, RestartDialog,
    ApiClient, ApiError, HardwareDetector, CacheManager,
)
from WSD_SDKToolkit_ZEMMACOS import (
    activation, renewal, reactivation, trial,
    communication, notifications, support, sales, config as sdk_config,
)
```

`py/main_ui.py` and `py/settings_ui.py` import `UniversalLicenseCenter` lazily to open the
About / license dialog.

## 5.4 Initialization flow

```
main() ──> ZEMmacOSApp.__init__
   └─ root.after(100, _license_startup)
        ├─ _create_splash()                       # splash overlay
        └─ root.after(50, _init_license_engine)   # worker thread (daemon)
             ├─ LicenseEngine(config_path)         # loads config, HardwareDetector,
             │                                     #   CacheManager, ApiClient
             ├─ engine.get_hardware_id()           # fingerprint the machine
             ├─ status = engine.initialize()       # decision engine (server-first)
             │     ├─ _sync_status_from_server()   # GET /internal/backend/license/status
             │     │     ├─ licensed|trial ──> valid status, cache it
             │     │     └─ no active      ──> clear cache+key, decision (inactive /
             │     │                           trial_consumed / no_license)
             │     └─ ConnectionUnavailable ──> cached-status fallback only
             │
             ├─ status.valid  ──> root.after(0, _launch_main_app)
             └─ else           ──> root.after(0, _open_ulc)
```

Key points:

- `initialize()` is called **exactly once** at startup.
- If the backend answers, its answer is authoritative (valid or not).
- Offline, only a cached *valid* status is trusted; otherwise the no-license decision is
  used and the ULC is shown.
- All network work runs on a daemon thread; UI updates are marshalled via
  `root.after(0, ...)`.

## 5.5 SDK lifecycle

| Phase | App entry | SDK call | Result |
|---|---|---|---|
| Construct | `_init_license_engine` | `LicenseEngine(config_path)` | engine with config/hardware/cache/client |
| Fingerprint | `_init_license_engine` | `get_hardware_id()` | machine hardware ID |
| Initialize | `_init_license_engine` | `initialize()` | `LicenseStatus` decision + event + callback |
| Launch | `_launch_main_app` | (none) | app consumes `self.license_status` |
| ULC open | `_open_ulc` / `open_activation` / `open_renew_license` | `UniversalLicenseCenter(...).show()` | workflow; success → status update |
| Refresh | `refresh_license` | `engine.refresh()` | re-sync from backend, emit event |
| Re-entry | About / Support | `UniversalLicenseCenter(reentry=True).show()` | SDK dialogs |
| Restart | (SDK) | `RestartDialog` → relaunch process | fresh `initialize()` on next boot |
| Shutdown | `_shutdown_app` / `on_closing` | `live_log.stop()`, `logger.stop()` | clean exit |

## 5.6 Startup sequence

```
1. main()  — DPI awareness, create Tk root, withdraw, create ZEMmacOSApp
2. ZEMmacOSApp.__init__  — settings, logger, live log, callbacks, network monitor flag
3. _license_startup  — splash, "Checking license..."
4. _init_license_engine (thread)  — engine init → decision
5. Decision:
     valid  → _launch_main_app
        ├─ build_main_ui()
        ├─ apply_saved_theme()
        ├─ deiconify + zoom + show_dashboard()
        ├─ _start_network_monitor()
        ├─ toast / auto-fetch / internet check
        ├─ _update_validity_countdown (1 s loop)
        └─ _unlock_ui()
     invalid → _open_ulc
        ├─ UniversalLicenseCenter(config_path, on_license_ready, log_fn, initial_status)
        ├─ result valid → _launch_main_app()
        └─ closed without resolution → _shutdown_app()   # Rule 18
```

## 5.7 Shutdown sequence

- **ULC closed without a resolved license** (`_shutdown_app`):
  1. Log "License flow incomplete — shutting down".
  2. `live_log.write(STARTUP, WARNING, ...)` then `live_log.stop()`.
  3. `logger.stop()`.
  4. Destroy the Tk root (fallback `sys.exit(1)`).
- **Main window closed** (`on_closing`):
  1. Stop the validity countdown.
  2. If downloads are active, prompt; cancel downloaders on confirm.
  3. `_stop_network_monitor()`.
  4. `live_log` shutdown + `logger.stop()`.
  5. `root.destroy()`.

There is no "SDK shutdown API" to call — the SDK keeps no global background threads
beyond the app-managed ones; the restart dialog handles its own process relaunch.

## 5.8 Delegate operations

`main.py` methods that forward to the SDK:

| App method | SDK call | Purpose |
|---|---|---|
| `open_activation(license_key=None)` | `UniversalLicenseCenter(reentry=True).show()` | Activation from dashboard |
| `open_renew_license()` | `UniversalLicenseCenter(reentry=True).show()` | Renewal from dashboard/settings |
| `refresh_license()` | `engine.initialize()` / `engine.refresh()` | Refresh status + event |
| `_on_contact_support()` | `center._show_request_dialog("Support", "support")` | Support request dialog |
| `_on_generate_request()` | `center._show_request_dialog("Generate Request", "request")` | Request dialog |

All of these pass `config_path=_get_sdk_config_path()` and `log_fn=self.log_live`.
