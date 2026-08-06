# 7. Integration Flow

## 7.1 Complete runtime flow

```
ZEMmacOS (main.py)
        |
        v
Initialize SDK
   LicenseEngine(config_path) --> build hardware detector, cache, client
        |
        v
LicenseEngine.initialize()   [server-first]
   GET /internal/backend/license/status?hardware_id=...
        |
        +-- licensed / trial        -> valid LicenseStatus  -> cache -> emit event -> callback
        +-- no active license       -> clear cache + key -> decision (inactive /
                                          trial_consumed / no_license) -> emit event
        +-- ConnectionUnavailable   -> offline: cached valid status only, else decision
        |
        v
License Status (LicenseStatus object held on ZEMmacOSApp.license_status)
        |
        +-- valid -> Application UI (dashboard / library / settings)
        |
        +-- invalid -> Universal License Center (SDK UI)
              |
              +-- customer workflow (Welcome / Trial / Activation / Renewal /
              |        Reactivation / Support / Sales / Notifications)
              |
              +-- success -> SuccessDialog -> RestartDialog -> relaunch process
              |        -> next boot initialize() -> valid -> main UI
              |
              +-- closed unresolved -> shutdown
```

## 7.2 End-to-end scenario: valid license at startup

```
python main.py
  -> ZEMmacOSApp
  -> splash ("Checking license...")
  -> LicenseEngine.initialize()
      -> server answers licensed
      -> LicenseStatus(status='licensed', days_left, plan, key, customer, expiry)
      -> EventBus.emit_status_changed(status)
  -> _launch_main_app
      -> build_main_ui, show_dashboard
      -> header badge + dashboard license card reflect status
  -> validity countdown refreshes UI every second; periodic refresh calls engine.refresh()
```

## 7.3 End-to-end scenario: new customer (no license)

```
startup -> engine.initialize() -> server: no_license
  -> decision status = no_license (new customer)
  -> _open_ulc
     -> UniversalLicenseCenter.show()
        -> WelcomeDialog (registration: name/email/mobile, OTP verify)
        -> Start Free Trial -> trial created -> status valid (trial)
           success -> SuccessDialog -> RestartDialog -> restart
        -> or Activate License (existing key): Validate -> OTP -> Activate
           -> success -> SuccessDialog -> RestartDialog -> restart
  -> restart -> initialize() -> server: licensed -> main UI
```

## 7.4 End-to-end scenario: license revoked while running

```
refresh_license (periodic / manual)
  -> engine.refresh() -> server: no active license
  -> self.license_status updated invalid (status 'inactive')
  -> main.py detects valid -> invalid transition
  -> _handle_license_revoked()
       -> _lock_ui() (disable nav, overlay)
       -> _show_inactive_license_dialog()  (Activate License / Generate Request)
       -> "Activate License" -> open_activation -> ULC
       -> "Generate Request" -> _on_generate_request -> ULC request dialog
```

## 7.5 Runtime operations from the UI

| User action | App method | SDK entry |
|---|---|---|
| Activate License (dashboard / settings / inactive dialog) | `open_activation` | `UniversalLicenseCenter.show()` |
| Renew License (dashboard / settings) | `open_renew_license` | `UniversalLicenseCenter.show()` |
| Refresh Status (settings) | `refresh_license` | `engine.initialize()` / `engine.refresh()` |
| About dialog | `_on_about_clicked` | `UniversalLicenseCenter(reentry=True).show()` |
| Contact Support | `_on_contact_support` | `center._show_request_dialog("Support", ...)` |
| Generate Request | `_on_generate_request` | `center._show_request_dialog("Request", ...)` |
| Start Trial | (ULC) | `WelcomeDialog` / `engine.start_trial` |

## 7.6 Synchronization invariant

Dashboard license card, header badge, Settings license panel, ULC status panel, and the
SuccessDialog all read the **same** `LicenseStatus` instance held by `main.py`. The engine
always populates that object from the normalized backend response
(`days_remaining`, plan, key, customer, expiry). Nothing is computed locally — every
surface displays identical values. See [09_API.md](09_API.md) and
[11_DATABASE.md](11_DATABASE.md).