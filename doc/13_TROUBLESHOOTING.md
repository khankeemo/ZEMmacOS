# 13. Troubleshooting Guide

## 13.0 Diagnostic discipline

1. **Read the documentation first** (`doc/`), then the logs.
2. **Log locations:**
   - App file log: `logs/ZEMmacOS_<timestamp>.log`
   - Live log: `logs/ZEMmacOS_live_<timestamp>.log`
3. **Find the canonical SDK events** (see 08_EVENT_SYSTEM / 10_CONFIGURATION):
   `WORKFLOW_START`, `VALIDATION_*`, `OTP_*`, `ACTIVATION_*`, `RENEWAL_SUCCESS`,
   `CACHE_REFRESH`, `STATUS_CHANGED`, `license.valid/invalid/offline`, `trial.*`.
4. Identify the root cause, then fix it **in the correct project** (see
   [14_FUTURE_DEVELOPMENT.md](14_FUTURE_DEVELOPMENT.md)).
5. Never guess and never duplicate logic.

Grep pattern you can use when a diagnostic is requested:

```
rg "WORKFLOW_|VALIDATION_|OTP_|ACTIVATION_|RENEWAL_|CACHE_REFRESH|STATUS_CHANGED|license\.|trial\.|hardware\." logs/ZEMmacOS_live_*.log
```

---

## 13.1 Activation failures

**Symptoms**
- "Activate License" does nothing or returns an error.
- Key flow stops at Validate step.
- Error text shown in ULC.
- Live log shows `VALIDATION_ERROR` / `ACTIVATION_STARTED` without `ACTIVATION_SUCCESS`.

**Possible causes**
- Invalid/expired/revoked license key (backend).
- License already activated on another device (device limit `max_devices`).
- Backend validation error message (server truth — Rule 5).
- Network/backend unavailable.

**Log locations**
- `logs/ZEMmacOS_live_*.log` — `VALIDATION_*`, `ACTIVATION_*`, `license.valid/invalid`.
- App log — `[ACTIVATION]`, `[SDK]` entries.

**Diagnostic steps**
- Confirm the key against the License Control Center.
- Re-run activation and capture `VALIDATION_START -> VALIDATION_SUCCESS/ERROR`.
- Check the backend endpoint `POST /api/v1/license` (validate) response for `error`.

**Correct resolution**
- Fix the license in the Websmith License Control Center, or use a valid key; backend
  errors are authoritative — do not patch around them in the SDK.

---

## 13.2 Renewal failures

**Symptoms**
- Renewal stuck at validation.
- No plans shown, or renewal errors after OTP.
- `RENEWAL_SUCCESS` missing.

**Possible causes**
- License not eligible (`verify_license_for_renewal` returns an error).
- Wrong license key passed to renew.
- OTP verification failed (see 13.3).
- Backend payment/plan configuration.

**Log locations**
- Live log: `VALIDATION_*`, `OTP_*`, `renewal.start`, `renewal.success`.
- App log: `[RENEWAL]`.

**Diagnostic steps**
- Verify `engine.renew()` receives the correct key (`get_license_key()`).
- Check `POST /api/v1/license/verify-renewal` response.
- Confirm the customer has a renewal-eligible plan in the control center.

**Correct resolution**
- Fix plan/license state in the Websmith control center; re-run the renewal flow.

---

## 13.3 OTP failures

**Symptoms**
- OTP email never arrives.
- "OTP is not valid." on verify.
- OTP send error in ULC.

**Possible causes**
- Wrong email on the license / trial.
- Email routing/SPAM on the provider.
- OTP expired or wrong code (4xx normalized to a single message).
- Backend OTP service unavailable.

**Log locations**
- Live log: `OTP_SENT`, `OTP_VERIFIED`, `WORKFLOW_ERROR`, `license.offline`.

**Diagnostic steps**
- Confirm the registered email matches the license.
- Re-send and verify a fresh code.
- Check `otp_verifications` in the Websmith DB (dev: `config/query_db.mjs`) for
  `expires_at`/`verified`.

**Correct resolution**
- Resend from the app or fix email routing / OTP service in the Websmith backend. Invalid
  OTP is intentional security behavior, not a defect.

---

## 13.4 Hardware issues

**Symptoms**
- "Hardware replacement requires administrator approval."
- Status says device changed; app re-prompts for license.
- `get_hardware_state()` returns `changed` / `blocked`.

**Possible causes**
- Machine hardware changed (CPU/motherboard/MAC/OS) so the fingerprint differs.
- Hardware binding is permanent; a mismatch invalidates only the cached status.
- Rebind not yet approved by an administrator.

**Log locations**
- Live log: `hardware.bound`, `license.invalid`, `STATUS_CHANGED`.
- App log: `[DEVICE]` category.

**Diagnostic steps**
- Compare current fingerprint vs registered `hardware_id` (`engine.view_hardware_status()`
  or settings panel Hardware ID).
- Check the Websmith device records for the license.

**Correct resolution**
- Request reactivation via the ULC (device replacement / reactivation request), have the
  administrator approve, then rebind. The backend performs the rebind after OTP
  verification; the SDK never clears/binds hardware locally.

---

## 13.5 API issues

**Symptoms**
- `ApiError` surfaced, `license.offline` logged, `ConnectionUnavailable` raised.
- Requests hang or timeout.
- 401/403 on signed requests.

**Possible causes**
- Wrong `api.url` / `public_key` in `api-config.json`.
- Clock skew beyond the 5-minute HMAC `timestamp_window`.
- API key invalid/rotated.
- Endpoint path/version mismatch between SDK and backend.
- Backend returning 429 (rate limit) or 5xx.

**Log locations**
- Live log: `license.offline`, `WORKFLOW_ERROR`.
- App log: `[SDK]`, `[NETWORK]`.

**Diagnostic steps**
- Verify `api-config.json` against the current product config.
- Confirm the machine clock is correct.
- Check the Internal API response for the status code (429/5xx/4xx).
- Confirm SDK/product/runtime/generated versions are in sync.

**Correct resolution**
- Re-inject the correct config via the Publisher; fix clock; coordinate version
  synchronization with Websmith.

---

## 13.6 Cache issues

**Symptoms**
- Stale status shown after activation/trial.
- Offline shows no license even though one exists.
- Old customer's data resurfacing.

**Possible causes**
- `cache_days` = 0 (current config) means cache entries are considered expired immediately;
  `peek()` still reads decision flags.
- Corrupt cache (`cache.corrupt`).
- Server confirmed no active license -> cache cleared (by design).

**Log locations**
- Live log: `CACHE_REFRESH`, `license.cache`, `license.invalid`.
- Files: `~/.websmith/prod_zemmacos/cache.json`, `cache.corrupt`, `license.key`.

**Diagnostic steps**
- Inspect the cache file (SDK-owned — read-only).
- Confirm whether the backend answered `licensed` or `no_license` in the live log.

**Correct resolution**
- If the backend is the truth, cache behavior is correct; do not edit the cache by hand.
- For stale *display*, trigger `refresh_license()` (the UI re-reads the same
  `LicenseStatus` object). If the engine still shows stale data, fix the engine/source in
  Websmith, regenerate, replace.

---

## 13.7 Network issues

**Symptoms**
- App locked at startup, no license resolution.
- `ConnectionUnavailable`, "Request timeout", "Connection error".
- Network dialog appears during fetch/download.

**Possible causes**
- No internet / DNS failure / proxy.
- Backend down.
- Firewall blocking `api.url`.
- Timeout too low.

**Log locations**
- Live log: `license.offline`.
- App log: `[NETWORK]`, `[SDK]`.
- Network dialog behavior is logged under `[NETWORK]`.

**Diagnostic steps**
- `ping` / DNS check; verify `https://www.websmithdigital.com` reachable.
- Check the network monitor logs (app checks `8.8.8.8:53`).
- Confirm firewall/proxy allows the API host.

**Correct resolution**
- Restore connectivity; if the backend is down, wait — the SDK falls back to cached valid
  state only. Offline messages queue and send on reconnect.

---

## 13.8 Startup issues

**Symptoms**
- App exits immediately.
- Splash stuck on "Checking license...".
- ULC opens but won't resolve; `_shutdown_app` exits (Rule 18).
- No main window.

**Possible causes**
- `api-config.json` missing or invalid (`FileNotFoundError` / config parse failure).
- Backend offline -> no cached status -> no-license decision -> ULC shown, then closed.
- Exception in `_init_license_engine` (see engine init error logged).
- Single instance lock held (`*.opencode.lock` in temp dir) -> duplicate process exit.

**Log locations**
- App log startup block (`ZEMmacOS Application Started`, `[SDK] Initializing license
  engine`, `Decision engine result`, `Opening Universal License Center`).
- Live log: `STARTUP` category.
- Console/stderr for traceback.

**Diagnostic steps**
- Verify `WSD_SDKToolkit_ZEMMACOS/config/api-config.json` exists and is valid JSON.
- Read the startup log entries in order; note the decision result.
- Check for a stale single-instance lock if a second instance exits.

**Correct resolution**
- Restore config; ensure backend reachable or valid cache; close duplicate processes.
- If the engine throws, capture the traceback and fix the SDK root cause in Websmith
  (never edit the generated SDK).

---

## 13.9 Runtime issues

**Symptoms**
- UI locked with no reason.
- License revoked while running (inactive dialog).
- Countdown/status shows wrong values.
- Downloads/fetch failures (unrelated to licensing — business logic).

**Possible causes**
- Server reported no active license (deleted/inactive/revoked/expired) -> app locks
  (`_handle_license_revoked`).
- Periodic refresh transitioned valid -> invalid.
- App bugs in catalogue/download code (out of licensing scope).

**Log locations**
- Live log: `license.invalid`, `STATUS_CHANGED`.
- App log: `[SDK] License refresh`, `[UI] UI locked`, `[DOWNLOAD]`, `[CATALOGUE]`.

**Diagnostic steps**
- Confirm the backend's current status via the control center.
- Grep `STATUS_CHANGED` history to see the transition.
- For download issues, follow the `[DOWNLOAD]` / `[NETWORK]` entries (business logic,
  not licensing).

**Correct resolution**
- Resolve license state in the Websmith control center; refresh in-app.
- For genuine application bugs, fix in ZEMmacOS business code.

---

## 13.10 Where NOT to fix

| Symptom | Wrong fix | Right fix |
|---|---|---|
| SDK bug (engine/cache/ULC/dialog) | edit `WSD_SDKToolkit_ZEMMACOS/*.py` | fix Websmith source (templates / runtime generators / Publisher / Internal API), regenerate, replace SDK |
| Wrong config values | hardcode values in `main.py` | update `api-config.json` via the Publisher |
| License state wrong | change code to fake validity | correct the record in the License Control Center |
| Display stale | refresh manually once | fix engine source-of-truth sync in Websmith, regenerate |

Never modify the generated SDK, never duplicate licensing logic in ZEMmacOS, and never
bypass the SDK to reach the backend.