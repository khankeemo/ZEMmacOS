# 3. Project Structure

```
ZEMmacOS/
│
├── main.py                      # Application entry point; license gate & orchestration
│
├── py/                          # ZEMmacOS application source (business logic + UI)
│   ├── main_ui.py               #   Main window, dashboard, nav, license widgets
│   ├── settings_ui.py           #   Settings panel (incl. license panel + About dialog)
│   ├── settings.py              #   SettingsManager (config/config.json) + AppSettingsService
│   ├── logger.py                #   Rotating file logger (singleton)
│   ├── live_log.py              #   LiveLog UI + timestamped live log file
│   ├── themes.py                #   Light/dark theme application
│   ├── modern_widgets.py        #   Custom Tk widgets (cards, progress, badges)
│   ├── safe_console.py          #   Console widget
│   ├── cleaner.py               #   Temp / pycache / log cleanup
│   ├── update.py               #   AppUpdater (version check + update browser links)
│   ├── idm_downloader.py        #   Segmented resumable downloader
│   ├── gib_macos_wrapper.py     #   Thin wrapper around gibMacOS catalogue fetch
│   └── gibMacOS.py              #   gibMacOS catalogue parser/engine (vendor)
│
├── WSD_SDKToolkit_ZEMMACOS/     # GENERATED WSD Universal SDK — READ-ONLY
│   ├── __init__.py
│   ├── license_engine.py        #   Decision engine + LicenseStatus
│   ├── universal_license_center.py  # Customer-facing license UI (ULC)
│   ├── universal_email_dialog.py    # Shared email dialog
│   ├── universal_success_dialog.py  # SuccessDialog
│   ├── universal_restart_dialog.py  # RestartDialog
│   ├── welcome.py               #   WelcomeDialog (onboarding + trial + OTP)
│   ├── activation.py  renewal.py  reactivation.py  trial.py
│   ├── sales.py  support.py  communication.py  notifications.py
│   ├── client.py                #   ApiClient / ApiError / ConnectionUnavailable
│   ├── crypto.py                #   HMAC signing, timestamp, nonce
│   ├── hardware.py              #   HardwareDetector
│   ├── cache.py                 #   CacheManager (offline cache)
│   ├── config.py                #   load_api_config() helpers
│   ├── live_log.py              #   SDK LiveLog (shared) + external logger bridge
│   ├── event_bus.py             #   EventBus + LicenseStatusChanged
│   ├── workflow_progress.py     #   WorkflowProgress stages
│   ├── dialog_manager.py        #   DialogManager helper
│   ├── single_instance.py       #   SingleInstance lock
│   ├── manifest.json
│   ├── Integrations.md          #   Generated integration guide (keep as reference)
│   ├── docs/                    #   Generated SDK docs (README, API, ARCHITECTURE, ...)
│   ├── assets/                  #   Branding assets
│   └── config/api-config.json   #   per-product config (injected by publisher)
│
├── config/
│   ├── config.json              #   App settings (download dir, theme, threads, ...)
│   ├── project_manifest.json    #   Product/version/publisher metadata
│   ├── installer.iss            #   Inno Setup installer script
│   ├── license_agreement.txt  privacy_policy.txt  terms_of_use.txt
│   ├── query_db.mjs             #   Developer SQL probe against the Websmith DB
│   ├── macos/  linux/           #   Platform packaging assets
│   └── ...
│
├── bat/                         # Build / run scripts (build.bat, build_prod.bat, ...)
├── spec/                        # PyInstaller specs
├── Scripts/                     # gibMacOS runtime (settings.json lives here)
├── env/.env.production          # Backend (Render/Vercel) production env — SERVER-side
├── help/index.html              # In-app help page
├── logs/                        # Runtime logs (see 10_CONFIGURATION.md)
├── public/                      # Static web assets for the packaged app
└── WSD_SDKToolkit_ZEMMACOS/     # The target program already-local SDK (see above)
```

## Where licensing lives

- **All licensing integrations** are inside `main.py` and the read-only SDK package
  `WSD_SDKToolkit_ZEMMACOS/`.
- `py/main_ui.py`, `py/settings_ui.py` only **consume** the `LicenseStatus` object held on
  the app and open the ULC for About/Support. They contain **no** licensing logic.
- No legacy wrappers, helper classes, activation/renewal/trial flows, or deprecated
  utilities remain in `py/` or `main.py`.

## Note on `WSD_SDKToolkit_ZEMMACOS/config/api-config.json`

The config file shipped inside the generated SDK is specific to the SDK *instance* that
ZEMmacOS was built against. It is injected by the Websmith SDK Publisher and must stay in
sync with the SDK version. Do not hand-edit values like the API public key except as part
of a vendor-authorized product reconfiguration.