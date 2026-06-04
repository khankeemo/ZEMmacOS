# ZEMmacOS Licensing Migration

## Architecture

```
Desktop App  →  HTTPS REST (ZEM_API)  →  PostgreSQL
```

The desktop client is **non-authoritative**. It only:

- Collects hardware fingerprint
- Calls `/license/*` and `/trial/*`
- Stores a **temporary encrypted cache** (hardware-derived key, no `master.key`)
- Uses **offline grace** until `offline_grace_until` from the server expires

## Removed from client distribution

- `zem_license/google_service.json`
- `admin_tools/master.key`
- `admin_tools/` (admin panel is separate)
- `google_license_backend` (import raises error)

## Setup

1. Start PostgreSQL database `zemmacos`.
2. Configure and run `ZEM_API` (see `ZEM_API/README.md`).
3. Set `license_api_url` in `config.json`.
4. For admin: set `ZEM_ADMIN_API_KEY` or `admin_tools/admin_api.key`.

## Phases

| Phase | Status |
|-------|--------|
| 1 — FastAPI + PostgreSQL + endpoints | Done |
| 2 — Desktop uses REST API | Done |
| 3 — Migrate Sheets → PostgreSQL | Use `ZEM_API/services/legacy_google_sheets.py` on server |
| 4 — Advanced security / analytics | Extend audit_logs + rate limits |
