# 6. Import Structure

## 6.1 Package structure

```
WSD_SDKToolkit_ZEMMACOS/            <- top-level importable package
  ├── __init__.py                   # exports public symbols; imports submodules
  └── *.py                          # engine + UI + transport + storage modules
```

- `main.py` inserts `BASE_DIR` and `PY_DIR` (`py/`) into `sys.path`.
- The SDK is imported as a top-level package: `from WSD_SDKToolkit_ZEMMACOS import ...`.

## 6.2 SDK exports (`__init__.py`)

`__all__ = [UniversalLicenseCenter, UniversalEmailDialog, WelcomeDialog, SuccessDialog,
RestartDialog, LicenseEngine, LicenseStatus, ApiClient, ApiError, ConnectionUnavailable,
HardwareDetector, CacheManager, LiveLog, SingleInstance, EventBus, WorkflowProgress,
DialogManager]`. Submodules `activation`, `renewal`, `reactivation`, `trial`,
`communication`, `notifications`, `support`, `sales`, and `config` are also imported.

## 6.3 SDK module dependency graph

```
crypto.py --+
hardware.py |--> client.py (ApiClient, ApiError) --> requests
cache.py  --+        |
                     v
workflow_progress.py -+
event_bus.py ---------+--> license_engine.py (LicenseEngine, LicenseStatus)
live_log.py ----------+
                     ^
welcome.py / activation / renewal / reactivation / trial
sales / support / communication / notifications / config.py
                     v
      universal_license_center.py (ULC)
                     v
      universal_email_dialog / success_dialog / restart_dialog
```

**Circular-import note:** `LiveLog` lives in its own `live_log.py` module so that
`universal_license_center.py` and `universal_restart_dialog.py` can both use it without
creating an import cycle.

## 6.4 Application import relationships

- `main.py` imports from `py/` (`main_ui`, `logger`, `live_log`, `gib_macos_wrapper`,
  `idm_downloader`, `cleaner`, `settings`, `update`) and from the SDK package.
- `py/main_ui.py` lazily imports `UniversalLicenseCenter` inside `_on_about_clicked`.
- `py/settings_ui.py` lazily imports `UniversalLicenseCenter` inside `_show_about_dialog`.
- No `py/` module imports the SDK at module load time — ULC imports are function-local so
  that opening dialogs does not trigger import loops or slow startup.

## 6.5 Initialization order

1. `sys.path` setup: insert `BASE_DIR` and `PY_DIR`.
2. Build the Tk root (`tk.Tk()`), withdraw it.
3. `ZEMmacOSApp.__init__` — settings, logger, live log; **SDK top-level imports load
   here**.
4. Register UI callbacks (`set_callbacks`).
5. `_license_startup` -> splash -> `_init_license_engine`.
6. `LicenseEngine(config_path)` — constructs `HardwareDetector`, `CacheManager`,
   `ApiClient` from config.
7. `_init_license_engine` calls `get_hardware_id()` then `initialize()`.
8. On valid status -> `_launch_main_app` -> `build_main_ui`; otherwise -> `_open_ulc`.
9. Runtime refresh / re-entry reuse the singleton `self.license_engine`.