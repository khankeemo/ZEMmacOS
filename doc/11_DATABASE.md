# 11. Database

ZEMmacOS involves **three** distinct data stores. Ownership is strict and must not blur.

## 11.1 Ownership summary

| Store | Owner | What lives there | Who writes | Who reads |
|---|---|---|---|---|
| **Local application database** | ZEMmacOS | app settings, gibMacOS settings, download state, logs | ZEMmacOS (`py/settings.py`, `gibMacOS.py`, `idm_downloader.py`, loggers) | ZEMmacOS |
| **SDK cache** | SDK (`CacheManager`) | cached license status, license key, onboarding flags, offline message queue | SDK engine only | SDK engine; UI never touches it |
| **Websmith Internal API database** | Websmith Universal | customers, licenses, plans, trials, devices, OTPs, requests, communications, notifications, renewal history | Websmith backend only | SDK (`ApiClient`) via the Internal API |

## 11.2 Local application database (ZEMmacOS)

| File / location | Format | Content | Reader/Writer |
|---|---|---|---|
| `config/config.json` | JSON | app settings (theme, download dir, threads, catalog, notifications) | `py/settings.py` |
| `Scripts/settings.json` | JSON | gibMacOS catalogue/download settings | `py/gibMacOS.py` |
| `logs/ZEMmacOS_<ts>.log`, `logs/ZEMmacOS_live_<ts>.log` | text | logs (see 10.5) | `py/logger.py`, `py/live_log.py` |
| download resume files (`.json`) | JSON | segmented download state | `py/idm_downloader.py` |
| `config/project_manifest.json` | JSON | product/version metadata | `py/update.py` |

**Rules:**

- ZEMmacOS persists **only application/business data**. It never persists license state,
  license decisions, or derived validity.
- The local app store is per-machine configuration, not a license store.

## 11.3 SDK cache (`~/.websmith/prod_zemmacos/`)

| File | Purpose |
|---|---|
| `cache.json` | TTL-based cache: `license_status` (LicenseStatus dict), `customer_email`, `onboarding_complete`, `has_ever_activated_paid_license`, `message_queue`, `pending_otp` |
| `license.key` | stored license key (plain text) |
| `cache.tmp` | atomic write temp (replaced into `cache.json`) |
| `cache.corrupt` | corrupt cache preserved on parse failure |

**Ownership:** the SDK `CacheManager` + `LicenseEngine` are the **only** writers. The UI
and the app never read or write the cache directly. Key behaviors:

- TTL via `offline.cache_days`; expired entries are treated as absent (`get()`), while
  `peek()` reads flags without expiry (used for decision flags).
- `invalidate_license_status()` and `clear_license_key()` run when the server confirms no
  active license.
- `reset_on_fresh_activation()` clears stale license/customer business keys (preserves
  hardware + message queue).
- Offline, only a cached **valid** status is trusted; otherwise the no-license decision
  applies.

## 11.4 Websmith Internal API database

- Owned exclusively by **Websmith Universal** (PostgreSQL on the backend).
- Tables include customers, licenses, plans, trials, devices, otp_verifications,
  requests, communications, notifications, renewal history.
- The SDK **never** touches this database directly — it reaches it only through the
  Internal API endpoints listed in [09_API.md](09_API.md).
- `config/query_db.mjs` is a **developer-only** SQL probe script used against the
  Websmith database for testing — it is not part of the runtime application and requires
  the Websmith `.env.local`.

## 11.5 Source of truth & caching rules

1. **The backend database is the single source of truth** for license validity, plan,
   days remaining, expiry, customer, hardware binding, and activation state.
2. The SDK cache exists only for **offline grace** and decision flags; it is never a
   business source of truth.
3. ZEMmacOS has no license database at all — it only displays the `LicenseStatus` object
   it received from the engine.
4. On any contradiction, the backend wins; the SDK clears stale cache and re-syncs.
