# 10. Configuration

## 10.1 Config files

| File | Owner | Purpose |
|---|---|---|
| `WSD_SDKToolkit_ZEMMACOS/config/api-config.json` | SDK (injected by Publisher) | product id, API url/key, trial, license, hardware, offline, security, branding, UI, features |
| `config/config.json` | ZEMmacOS | app settings (theme, download dir, threads, catalog, notifications) |
| `config/project_manifest.json` | ZEMmacOS | product metadata (name, version, publisher URLs) |
| `Scripts/settings.json` | ZEMmacOS (gibMacOS) | gibMacOS catalogue/download settings |
| `env/.env.production` | Websmith backend deployment | server-side env (DB, JWT, admin, CORS) — not app runtime config |
| `~/.websmith/prod_zemmacos/cache.json` + `license.key` | SDK `CacheManager` | offline cache + stored license key |

## 10.2 Environment variables

- The SDK reads **no** environment variables at runtime; all settings come from
  `api-config.json`.
- `env/.env.production` is the **license server / backend** deployment environment
  (Render/Vercel). It must never be treated as ZEMmacOS runtime configuration. It is
  documented here only so its ownership is clear: **Websmith owns it**, not ZEMmacOS.

## 10.3 SDK settings (`api-config.json`)

| Section | Key settings |
|---|---|
| `product` | `id` (`prod_zemmacos`), `name`, `version` |
| `api` | `url`, `version` (`v1`), `public_key`, `timeout`, `retry_count` |
| `trial` | `enabled`, `days` (7), `require_email`, `auto_convert`, `message` |
| `license` | `hardware_binding`, `max_devices` (1), `offline_days`, `renewal_reminder_days` (7) |
| `hardware` | `fingerprint` includes cpu/motherboard/mac/os; `replacement.enabled`, `require_approval`, `max_replacements_per_year` |
| `offline` | `enabled`, `cache_days` (0), `encryption` (AES-256-GCM), `validate_on_reconnect` |
| `security` | `hmac_algorithm`, `timestamp_window` (300 s), `require_nonce`, `rate_limit` |
| `branding` | company name, logo, colors, support email, all UI labels |
| `ui` | theme, language, dialogs toggles |
| `features` | trial, license, hardware_binding, offline_mode, renewals, analytics, audit_logs |

> Rules: never hardcode SDK values in ZEMmacOS. Config is injected by the Publisher and
> must be kept in sync with the SDK version. Version mismatch (SDK / product / runtime /
> generated) fails at generation time.

## 10.4 Application settings (`config/config.json`)

| Key | Default | Meaning |
|---|---|---|
| `theme` | `light` | UI theme |
| `download_directory` | `~/Downloads/MacOS Download` | where installers are saved |
| `catalog` | `publicrelease` | Apple catalog to fetch |
| `download_threads` | 8 | segmented download threads |
| `max_concurrent_downloads` | 3 | concurrency cap |
| `retry_on_failure` / `max_retries` / `timeout_seconds` | true / 3 / 30 | download retry policy |
| `notifications_enabled` | true | in-app update notification toggle |
| `compact_mode` | false | UI mode |

Managed by `py/settings.py` (`SettingsManager`), saved with `json.dump(..., indent=2)`.

## 10.5 Logging

### Locations

| Stream | Path | Writer |
|---|---|---|
| App file log | `logs/ZEMmacOS_<timestamp>.log` | `py/logger.py` (RotatingFileHandler) |
| Live log | `logs/ZEMmacOS_live_<timestamp>.log` | `py/live_log.py` |
| SDK logs | routed into the app live log via `LiveLog.set_external_logger(...)` (ULC `log_fn`) | SDK `live_log.py` |

### Levels

- App logger: `debug`, `info`, `success` (logged as info with a checkmark), `warning`,
  `error`, `critical`.
- LiveLog levels: `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR`.

### LiveLog categories (`py/live_log.py`)

`STARTUP`, `SDK`, `WELCOME`, `ACTIVATION`, `RENEWAL`, `DEVICE`, `UI`, `AWS01`,
`VALIDATION`, `OTP`, `APP`.

### SDK log events (canonical)

`WORKFLOW_START/COMPLETE/ERROR`, `VALIDATION_START/SUCCESS/ERROR`, `OTP_SENT`,
`OTP_VERIFIED`, `ACTIVATION_STARTED/SUCCESS`, `RENEWAL_SUCCESS`, `CACHE_REFRESH`,
`STATUS_CHANGED`, plus `engine.initialize`, `license.valid/invalid/offline/cache`,
`trial.started/success`, `hardware.bound`, `ALREADY_ACTIVATED`.

### Rotation & retention

- App file log: `RotatingFileHandler(maxBytes=10 MB, backupCount=5)`.
- On startup, old `ZEMmacOS_*.log` files beyond the newest 10 are deleted
  (`_clean_old_logs`).
- Live log: one timestamped file per run; not rotated.
- Manual cleanup: `on_clean_logs` / `cleaner.clear_logs` (Settings -> Clean Logs) keeps
  the current file, deletes the rest.

### Diagnostic discipline

When diagnosing issues, **read the logs first** — the app file log (for app + SDK events)
and the live log (for categorized SDK events). Grep for the canonical SDK events and the
relevant category. Do not guess. See [13_TROUBLESHOOTING.md](13_TROUBLESHOOTING.md).
