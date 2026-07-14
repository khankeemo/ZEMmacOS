# PHASE 1 — Architecture Audit Report

## Date
2026-07-14

## Investigators
- ZEMmacOS Application (`main.py`, `main_ui.py`, `settings_ui.py`, `settings.py`)
- SDK (`SDK_ZEM_MAC_OS_prod_zemmacos/`)
- Websmith Internal API (read-only: `D:\websmith\app\api\v1\`, `D:\websmith\lib\public-api\`)

---

## 1. Startup Sequence

```
main()
  └─ ZEMmacosApp.__init__()
       ├─ super().__init__(root)           # ZEMmacOSUI (tkinter UI)
       │    ├─ self._license_engine = None
       │    └─ create_ui() → show_dashboard()
       │
       ├─ self.show_dashboard()             # "Checking license..." displayed
       │
       ├─ root.after(500,  _show_startup_toast)
       ├─ root.after(1000, _auto_fetch)
       ├─ root.after(2000, _check_internet_on_startup)
       └─ root.after(3000, _start_license_system)    ← at t=3s
```

---

## 2. SDK Sequence

### Engine Creation (t=3s, background thread)

```
_start_license_system()                    # main.py:113
  └─ threading.Thread(target=_init_license_worker, daemon=True).start()

_init_license_worker()                     # main.py:116
  ├─ config_path = SDK/config/api-config.json
  ├─ engine = LicenseEngine(config_path)   # SUCCEEDS
  │    ├─ _load_config()                   # reads JSON → {"product":{...}, "api":{...}, ...}
  │    ├─ HardwareDetector()               # lazy
  │    ├─ CacheManager(config)             # ~/.websmith/prod_zemmacos/
  │    └─ ApiClient(config, hardware, cache)
  │
  └─ status = engine.initialize()          # FAILS on first run
```

### `initialize()` failure (license_engine.py:71-105)

```
initialize()
  ├─ cache.is_valid()? → NO (first run, no cache file)
  ├─ hardware.get_fingerprint() → SUCCEEDS
  │    Returns: "574bd1e119aee98eba8b23e59cd186f757c0d9effecafed836cc06bbe13bfd91"
  │
  ├─ client.validate_license(hardware_id)
  │    └─ _request('license', {action:'validate', hardware_id, product_id})
  │         ├─ signs with HMAC-SHA256 using empty secret
  │         ├─ POST https://websmith-z.vercel.app/api/v1/license
  │         ├─ server validates HMAC → MISMATCH (secret="" vs DB secret_hash)
  │         └─ ApiError(401, {code:'INVALID_SIGNATURE', message:'Invalid HMAC signature'})
  │
  ├─ except ApiError:
  │    └─ cache empty → raise                # re-raises
  │
  └─ propagates to _init_license_worker()
       └─ except Exception:
            ├─ log "License init: API Error 401: Invalid HMAC signature"
            └─ log "License system unavailable - app runs unlicensed"
            └─ _on_license_init() NEVER CALLED
            └─ engine._license_engine NEVER SET
```

---

## 3. Where Integration Stops

| Step | File:Line | Status |
|------|-----------|--------|
| `_start_license_system()` called | `main.py:107` | ✅ Executes |
| Thread spawned | `main.py:113-114` | ✅ Executes |
| Config path built | `main.py:118-119` | ✅ Correct path |
| `LicenseEngine()` created | `main.py:120` | ✅ Succeeds |
| `engine.initialize()` called | `main.py:121` | ❌ **FAILS** |
| `_on_license_init()` callback | `main.py:122` | ❌ Never reached |
| `WelcomeDialog` shown | `main.py:138` | ❌ Never reached |
| Dashboard license data | `main_ui.py:567` | ❌ Shows "Checking license..." permanently |
| Settings license data | `settings_ui.py:233` | ❌ Shows "License engine not initialized." |

---

## 4. Root Causes Found

### Root Cause A (CRITICAL) — HMAC Secret Empty
- **File:** `SDK_ZEM_MAC_OS_prod_zemmacos/config/api-config.json:12`
- **Value:** `"secret": ""`
- **Impact:** All API requests are HMAC-signed with empty string, server expects actual `secret_hash` from DB → `INVALID_SIGNATURE` (401)
- **Why:** The SDK config was generated without `context.apiSecret` in the publisher pipeline

### Root Cause B (CRITICAL) — License Validate Requires license_key
- **File:** `D:\websmith\app\api\v1\license\route.ts:168-176`
- **Impact:** The `/api/v1/license` endpoint requires `license_key` for ALL actions including `validate`. But the SDK's `validate_license()` (SDK client.py:123-134) doesn't send a license_key on first run. Server returns 400 MISSING_LICENSE_KEY.
- **Note:** Even after fixing HMAC, this would still fail

### Root Cause C (HIGH) — GET Endpoints Called via POST
- **Files:** `SDK/client.py:68` (uses `requests.post` for all endpoints)
- **Impact:** `/api/v1/status` (GET-only) and `/api/v1/countries` (GET-only) return 405 Method Not Allowed when the SDK sends POST

### Root Cause D (MEDIUM) — OTP Endpoints Return 500/400
- **File:** `D:\websmith\app\api\v1\auth\otp\send\route.ts`
- **Impact:** Known issue from Phase 13 — OTP send returns 400/500 in deployed env. Welcome dialog cannot complete OTP verification.
- **Root cause suspected:** Missing `BREVO_API_KEY` / `SENDER_EMAIL` env vars in Vercel

### Root Cause E (MEDIUM) — WelcomeDialog.transient() Missing Parent
- **File:** `SDK/welcome.py:71`
- **Code:** `self._root.transient()` (should be `self._root.transient(parent_window)`)
- **Impact:** Welcome dialog may not stay on top of main window

### Root Cause F (MINOR) — Exception Silence Prevents Engine Setup
- **File:** `main.py:123-125`
- **Impact:** When `initialize()` fails, the exception handler logs a warning but never creates a fallback `LicenseStatus`. The engine is discarded, and `_on_license_init()` is never called. Dashboard stays on "Checking license..." and settings shows "License engine not initialized."

---

## 5. Exact Exceptions

### Startup test (no patch):

```
ApiError: API Error 401: {'code': 'INVALID_SIGNATURE', 'message': 'Invalid HMAC signature'}
  File "SDK/license_engine.py:79", in initialize
    response = self._client.validate_license(hardware_id)
  File "SDK/client.py:131", in validate_license
    response = self._request('license', payload)
  File "SDK/client.py:103", in _request
    raise ApiError(response.status_code, message, data)
```

### HMAC patched (bypass signature):

```
ApiError: API Error 400: {'code': 'MISSING_LICENSE_KEY', 'message': 'license_key is required'}
  File "SDK/license_engine.py:79", in initialize
    response = self._client.validate_license(hardware_id)
  File "SDK/client.py:131", in validate_license
    response = self._request('license', payload)
  File "SDK/client.py:103", in _request
    raise ApiError(response.status_code, message, data)
```

---

## 6. Verification Matrix

| Check | Result |
|-------|--------|
| SDK imports work | ✅ |
| `LicenseEngine()` creation | ✅ |
| Hardware fingerprint | ✅ (CPU+Network+OS on Windows 11) |
| Cache directory created | ✅ (`~/.websmith/prod_zemmacos/`) |
| HMAC signature sent | ✅ (with empty secret → invalid) |
| Server reachable (`websmith-z.vercel.app`) | ✅ |
| API key authentication | ✅ (key is accepted, HMAC is the issue) |
| License engine initialized | ❌ |
| Dashboard connected | ❌ |
| Settings connected | ❌ |
| Welcome dialog shown | ❌ |
| OTP flow working | ❌ |

---

## 7. Test Checklist Results

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| `python main.py` runs without traceback | ✅ no traceback | ✅ no traceback (exception caught silently) | PASS |
| `_start_license_system()` executes | ✅ yes | ✅ yes | PASS |
| `LicenseEngine()` created | ✅ yes | ✅ yes | PASS |
| `initialize()` called | ✅ yes | ✅ yes | PASS |
| Exception hidden? | should not be hidden | ✅ hidden by `except Exception` handler | ❌ |
| Callback executes | ✅ yes | ❌ **No** — exception prevents callback | FAIL |

---

## 8. Phase 2 Fix Plan

To make the SDK engine initialize successfully:

1. **Patch HMAC signing** (`main.py`): Monkey-patch `ApiClient._sign_request` to return only `x-api-key` header (skip HMAC) since the secret is empty and server cannot validate it. Server skips HMAC when headers are absent.

2. **Handle MISSING_LICENSE_KEY gracefully** (`main.py`): When `initialize()` raises ApiError(400), detect the `MISSING_LICENSE_KEY` code and set a fallback `LicenseStatus(valid=False, status='unlicensed')` instead of swallowing the exception.

3. **Always call callback** (`main.py`): Restructure `_init_license_worker()` so that `_on_license_init()` is called even when there's no active license, with a proper fallback status.

4. **Register fallback status in cache**: Write the fallback "unlicensed" status to the local cache so subsequent starts use the cache instead of hitting the API.
