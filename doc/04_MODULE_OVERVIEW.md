# 4. Module Overview

## ZEMmacOS application modules

| Module | Role | Owned by |
|---|---|---|
| `main.py` | Entry point. Builds the Tk root, orchestrates the SDK startup sequence, gates the app on the license decision, glues UI callbacks, runs the catalogue/download/network workflows. | ZEMmacOS |
| `py/main_ui.py` | Main window shell: sidebar navigation, dashboard, library, licence status card + header badge, inactive-license dialog, network dialog, toasts. Reads `self.license_status` (SDK object) only. | ZEMmacOS |
| `py/settings_ui.py` | Settings panel: download directory, threads, notifications toggle, License Information panel, About dialog (opens the SDK ULC). | ZEMmacOS |
| `py/settings.py` | `SettingsManager` reads/writes `config/config.json`; `AppSettingsService` applies themes, first-run directory, and saves UI values. | ZEMmacOS |
| `py/logger.py` | Rotating file logger (10 MB, 5 backups) + console callback. Singleton. | ZEMmacOS |
| `py/live_log.py` | `LiveLog` UI overlay and timestamped live log file. Provides `get_live_log()` singleton. | ZEMmacOS |
| `py/themes.py` | Light/dark theme application via `apply_theme()`. | ZEMmacOS |
| `py/modern_widgets.py` | Custom widgets: `ModernCard`, `ModernProgressBar`, `StatusBadge`, `ThemeToggle`, `DebugConsole`. | ZEMmacOS |
| `py/safe_console.py` | Console text widget with safe clear. | ZEMmacOS |
| `py/cleaner.py` | Cleans `__pycache__`, `.pyc`, gibMacOS temp, and old logs. | ZEMmacOS |
| `py/update.py` | `AppUpdater` fetches the latest version and opens the update website. | ZEMmacOS |
| `py/idm_downloader.py` | Segmented resumable downloader (state JSON per download). | ZEMmacOS |
| `py/gib_macos_wrapper.py` | Wraps `gibMacOS` catalogue fetch. | ZEMmacOS |
| `py/gibMacOS.py` | Vendor catalogue parser / download engine. | ZEMmacOS (vendor) |

## SDK modules (`WSD_SDKToolkit_ZEMMACOS/` — generated, read-only)

| Module | Role | Layer |
|---|---|---|
| `license_engine.py` | `LicenseEngine` — decision engine, workflow controller, state owner. `LicenseStatus`. | Engine |
| `universal_license_center.py` | `UniversalLicenseCenter` — the customer-facing license UI and all workflows. | UI |
| `welcome.py` | `WelcomeDialog` — onboarding, registration, OTP, trial start. | UI |
| `universal_email_dialog.py` | `UniversalEmailDialog` — one email form for all request categories. | UI |
| `universal_success_dialog.py` | `SuccessDialog` — post-operation success summary. | UI |
| `universal_restart_dialog.py` | `RestartDialog` — merged restart workflow (flush cache → relaunch). | UI |
| `client.py` | `ApiClient`, `ApiError`, `ConnectionUnavailable` — HMAC-signed HTTP transport. | Transport |
| `crypto.py` | `generate_timestamp`, `generate_nonce`, `sign_request`. | Transport |
| `hardware.py` | `HardwareDetector` — machine fingerprint. | Fingerprint |
| `cache.py` | `CacheManager` — offline cache at `~/.websmith/<product>/`. | Storage |
| `config.py` | `load_api_config`, `get_branding`, `get_product_info`, `get_store_url`. | Config |
| `live_log.py` | SDK `LiveLog` + `set_external_logger` bridge to the app. | Logging |
| `event_bus.py` | `EventBus` — `LicenseStatusChanged` + generic events. `LICENSE_STATUS_CHANGED`. | Events |
| `workflow_progress.py` | `WorkflowProgress` — stage tracking (checking server, sending OTP, ...). | Events |
| `dialog_manager.py` | `DialogManager` — modal helpers. | UI |
| `single_instance.py` | `SingleInstance` — one-process lock for the licensing workflow. | Utils |
| `activation.py`, `renewal.py`, `reactivation.py`, `trial.py` | Thin SDK wrappers that delegate to the engine. | Services |
| `sales.py`, `support.py`, `communication.py`, `notifications.py` | Thin SDK wrappers that delegate to the engine. | Services |
| `config/api-config.json` | Per-product configuration (injected by the Publisher). | Config |

## Layering of the SDK internals

```
transport (client/crypto)  ←  engine (license_engine)  ←  UI (ULC + dialogs)
      storage (cache)                        │
      fingerprint (hardware)                 ▼
                                             events (event_bus / live_log / workflow_progress)
```

The engine is the only module that mutates state; everything else is transport, storage,
fingerprint, UI, or a thin delegation wrapper.
