# 12. UI / UX

## 12.1 Dialog flow overview

```
Startup
  -> Splash ("Checking license...")
  -> LicenseEngine.initialize()
       valid   -> Main application (dashboard)
       invalid -> Universal License Center (ULC)
                   |-> WelcomeDialog (new customer: register + OTP + Start Trial)
                   |-> License Center dashboard (status + action buttons)
                   |    |-> Activate License -> pre-dialog (Buy License / Existing License)
                   |    |        -> key flow: Validate License API -> OTP -> Verify -> Activate
                   |    |-> Renew License    -> same key flow in renewal mode (+ renewal details/plans)
                   |    |-> Reactivation / Device Replacement
                   |    |-> Contact Support / View Notifications
                   |-> SuccessDialog -> RestartDialog -> restart
```

## 12.2 Welcome screen (`WelcomeDialog`, SDK)

- Shown for a **new customer** (no onboarding flag): product title, description, Start
  Free Trial / Activate / Buy buttons.
- Registration fields: name, email, mobile, country code.
- Trial start requires OTP verification of the email (`send_otp` / `verify_otp`), then the
  backend creates the trial bound to the hardware ID.
- Closing the welcome dialog closes the application.

## 12.3 Activation flow (ULC — SDK-owned)

1. User selects **Activate License**.
2. Pre-dialog choice: **[ Buy License ]** (opens store URL derived from config) or
   **[ Existing License ]**.
3. **Validate License API** — one call; failure shows the exact backend message, **no
   OTP, no final action**.
4. On pass, OTP is sent to the license's registered email.
5. OTP verified -> **Activate** enabled -> activation pipeline
   (`engine.activate(key)`): bind hardware -> create activation -> download status ->
   clear local cache -> save new cache -> fire event -> refresh SDK.
6. Fresh activation **clears the old cached license state** (Rule 3).
7. `SuccessDialog` -> `RestartDialog` -> process restart -> next `initialize()` sees the
   valid license and launches the main app.

## 12.4 Renewal flow (ULC — SDK-owned)

1. User selects **Renew License**.
2. Pre-dialog choice: **[ Buy License ]** or **[ Existing License ]**.
3. Same mandatory flow: Validate License API -> OTP -> Verify.
4. In renewal mode the ULC calls `verify_license_for_renewal()` and shows renewal details:
   expiry status (EXPIRED — eligible), current days left, and available plans (name,
   duration, current-plan marker).
5. On success, `engine.renew(key)` extends the expiry; SuccessDialog shows the new expiry
   and days remaining.

## 12.5 Trial flow (ULC — SDK-owned)

1. New customer chooses **Start Free Trial** (or auto-trial on welcome).
2. Register -> OTP verify -> `engine.start_trial(email, ...)` -> trial license created and
   bound to hardware ID.
3. Auto-convert to paid runs when configured after expiry.
4. While a trial is active the app runs normally with `LicenseStatus(status='trial')`.
5. After trial ends: decision `trial_consumed` (onboarding complete, no paid license) ->
   ULC shows activation.

## 12.6 Notifications

- **SDK notifications:** `UniversalLicenseCenter` "View Notifications" opens the SDK
  notification viewer via `engine.get_notifications(email)`; `DialogManager` shows the
  list (up to 10), and SDK marks read. Sourced from the Internal API.
- **App notifications:** in-app toasts (`show_toast`) for catalogue/download/license
  events; a `notifications_enabled` toggle in settings; network dialogs for connectivity
  loss.

## 12.7 Error dialogs

| Dialog | Shown when | Content |
|---|---|---|
| Network dialog | internet lost during fetch/download/startup | retry countdown, pause/cancel actions |
| Inactive License dialog | server reports no active license while running | "This license is inactive or no longer exists..."; buttons **Activate License / Generate Request** |
| SDK error dialogs | validation / OTP / API failures | exact backend message, what/why/next (Rule 8) |
| `messagebox` errors | generic app failures (invalid index, missing directory, update errors) | user-friendly text |

**Inactive License dialog** is invoked from `main.py::_handle_license_revoked` (valid ->
invalid transition locks the UI) and defined in `py/main_ui.py::_show_inactive_license_dialog`.
"Activate License" routes to `open_activation`; "Generate Request" routes to
`_on_generate_request` (ULC request dialog).

## 12.8 Main application screens (ZEMmacOS)

| Screen | Contents |
|---|---|
| Dashboard | licence status card (status/plan/key/validity/expiry), Activate / Refresh / Renew buttons, version list, download console |
| Library | downloaded versions |
| Settings | download directory, threads, notifications toggle, License Information panel (status/product/plan/expiry/days/customer/license key with show-hide, Hardware ID, binding), About / Legal dialogs |

## 12.9 User workflow

```
Install -> Launch -> (license gate)
  New customer  -> Welcome -> Trial (free 7 days) or Activate existing key
  Existing paid -> Main app (dashboard)
  Expired       -> ULC renewal
  Hardware change -> "Hardware replacement requires administrator approval" -> contact
                     support / reactivation request -> admin approval -> rebind
  License revoked -> Inactive dialog -> Activate / Generate Request
```

Every licensing screen and workflow lives in the SDK ULC; ZEMmacOS renders only its own
application screens and reads `LicenseStatus` for display.