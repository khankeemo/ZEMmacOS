# PHASE 5 — Welcome Dialog Flow

## Trigger Logic (`main.py:131-157`)

The welcome dialog opens when `status.status` is neither `'active'` nor `'trial'`:

```python
_on_license_init(engine, status):
  └─ if status.status in ('active', 'trial') → log success, RETURN (no dialog)
  └─ else → log "No active license — starting onboarding"
       └─ root.after(1000, _show_welcome_dialog)
```

## Dialog Behavior (`main.py:159-179`)

```python
_show_welcome_dialog():
  ├─ engine = self.license_engine
  ├─ client = engine._client
  ├─ cache = engine._cache
  ├─ dialog = WelcomeDialog(client, product_name='ZEMmacOS', cache=cache)
  ├─ if dialog.is_onboarding_complete(): return early (skip dialog)
  ├─ result = dialog.show()     ← blocks until user completes/closes
  │    ├─ onboarding_complete → re-init engine, refresh widgets
  │    ├─ skipped → log "Onboarding skipped"
  │    └─ Exception → log warning
```

## Cache Interaction

The `WelcomeDialog` uses two cache keys:
- `onboarding_complete` — written after successful OTP+trial start
- `license_status` — written after engine initialization

If `onboarding_complete` is `True` in cache, `is_onboarding_complete()` returns `True` and the dialog is skipped (even if `_on_license_init` would trigger it).

## Test Results

| Scenario | Setup | Expected | Result |
|----------|-------|----------|--------|
| **A: Fresh start** | Delete cache, restart | Welcome dialog opens | ✅ `status='unlicensed'` → `_on_license_init` triggers dialog |
| **B: License activated** | Activate via Settings, restart | Dialog does NOT open | ✅ `status='active'` → early return in `_on_license_init` |
| **C: Trial expired** | Wait for expiry, restart | Dialog opens again | ✅ `status='expired'` → triggers dialog |

## Known Limitation — OTP Endpoint

The `WelcomeDialog` sends OTP via `POST /api/v1/auth/otp/send`. This endpoint returns 500 in the deployed Vercel environment (Phase 13 — missing `BREVO_API_KEY`/`SENDER_EMAIL` env vars). Users see an error message and cannot complete OTP verification.

**Impact**: Trial onboarding via the welcome dialog is blocked at the OTP step. Users can close the dialog and use the app unlicensed, but cannot start a trial through the dialog.

**Resolution path**: Requires Vercel env var configuration, not a code fix.
