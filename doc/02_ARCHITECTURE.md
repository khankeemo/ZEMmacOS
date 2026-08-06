# 2. ZEMmacOS Architecture

## Layer diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ZEMmacOS Application                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Presentation layer  (Tkinter)                                     │  │
│  │  py/main_ui.py   py/settings_ui.py   py/modern_widgets.py          │  │
│  │  py/safe_console.py   py/themes.py                                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                        ▲ consumes LicenseStatus / events                │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Orchestration layer                                               │  │
│  │  main.py  (ZEMmacOSApp)                                            │  │
│  │    startup sequence, license gate, dashboard glue, downloads       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                        ▼ calls SDK public APIs only                     │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  SDK layer  WSD_SDKToolkit_ZEMMACOS  (generated, READ-ONLY)       │  │
│  │  LicenseEngine · UniversalLicenseCenter · ApiClient · Cache        │  │
│  │  HardwareDetector · EventBus · LiveLog · dialogs · services        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Websmith Digital Internal API  (websmith backend — single source of    │
│  truth for license state; owns the license database)                    │
└──────────────────────────────────────────────────────────────────────────┘
```

## Architectural rules

1. **Strict layering.** ZEMmacOS (presentation + orchestration) sits on top of the SDK.
   ZEMmacOS never bypasses the SDK to reach the backend, and never implements license
   logic.
2. **The backend is the single source of truth.** The SDK re-syncs from
   `GET /internal/backend/license/status` on `initialize()`, `refresh()`, and after every
   state-changing operation. ZEMmacOS never derives validity locally.
3. **The engine is the only state mutator.** Inside the SDK, `LicenseEngine` is the only
   module allowed to call the API, refresh the cache, update status, and fire status
   events. All other SDK modules are transport, storage, fingerprint, or UI.
4. **UI consumes state, never polls it.** Screens read the current `LicenseStatus` and
   subscribe to `EventBus.LicenseStatusChanged`; they do not re-run the engine themselves.
5. **The ULC is the only customer-facing license UI.** Activation, renewal, trial,
   reactivation, support, sales, and notifications all live in the ULC.

## Three runtime regions

| Region | Owner | Runtime lifetime |
|---|---|---|
| **Splash + license gate** | `main.py` (`_license_startup` → `_init_license_engine`) | startup only |
| **Universal License Center** | SDK (`UniversalLicenseCenter`) | startup when no valid license, or on re-entry |
| **Main application** | ZEMmacOS (`build_main_ui`, dashboard/library/settings) | after license is valid |

## Key flows

| Flow | Orchestrator | Details |
|---|---|---|
| Startup | `main.py` | init engine → decision → main app **or** ULC |
| Activation / Renewal / Trial | SDK ULC | opened by `main.py` via `open_activation` / `open_renew_license` |
| Refresh | `main.py` `refresh_license()` | calls `LicenseEngine.refresh()` |
| Revocation | `main.py` `_handle_license_revoked()` | valid→invalid transition locks UI + shows inactive dialog |
| Shutdown | `main.py` `_shutdown_app()` / `on_closing()` | stops loggers, destroys root, exits |

## Cross-cutting concerns

- **Logging** — two independent streams: rotating file logger (`py/logger.py`) and the
  timestamped live log (`py/live_log.py`). SDK events are also forwarded into the app log.
  See [10_CONFIGURATION.md](10_CONFIGURATION.md#logging).
- **Threading** — all network/API work runs in daemon threads; Tk updates are marshalled
  to the main thread via `root.after(0, ...)`.
- **UI lock** — during startup and on revocation the app locks navigation and shows an
  overlay (`_lock_ui` / `_unlock_ui`).
