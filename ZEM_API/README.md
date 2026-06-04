# ZEM License API

Cloud-authoritative licensing server for ZEMmacOS (PostgreSQL + FastAPI).

## Quick start

1. Create PostgreSQL database `zemmacos` and user `Keemo`.
2. Copy `.env.example` to `.env` and set `DB_PASSWORD`, `JWT_SECRET`, `ADMIN_API_KEY`.
3. Install dependencies:

```bash
cd ZEM_API
pip install -r requirements.txt
```

4. Initialize tables and run:

```bash
python -c "from database import init_db; init_db()"
uvicorn main:app --host 0.0.0.0 --port 8000
```

5. Point the desktop app `config.json` at `license_api_url` (default `http://localhost:8000`).

## Admin tools

Set `ZEM_ADMIN_API_KEY` or create `admin_tools/admin_api.key` with the same value as `ADMIN_API_KEY` in `.env`.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/license/validate` | Public |
| POST | `/license/activate` | Public |
| POST | `/license/reset` | Public |
| GET | `/license/info` | Public |
| POST | `/trial/start` | Public |
| POST | `/trial/status` | Public |
| POST | `/admin/create-license` | X-Admin-Key |
| POST | `/admin/revoke-license` | X-Admin-Key |
| POST | `/admin/extend-license` | X-Admin-Key |
| POST | `/admin/reset-device` | X-Admin-Key |

## Security

- Never ship `google_service.json`, `master.key`, or `admin_tools/` in end-user builds.
- Use HTTPS in production (reverse proxy / TLS termination).
- Rotate `JWT_SECRET` and `ADMIN_API_KEY` regularly.
