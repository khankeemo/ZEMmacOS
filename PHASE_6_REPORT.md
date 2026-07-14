# PHASE 6 — Internal API Validation

## SDK-to-API Route Mapping

### License Endpoints

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `validate_license(hw_id)` | POST `/api/v1/license` `{action:'validate'}` | POST `/api/v1/license` `{action:'validate'}` → queries licenses table | ✅ URL & method match |
| `activate_license(key, hw_id)` | POST `/api/v1/license` `{action:'activate'}` | POST `/api/v1/license` `{action:'activate'}` → inserts activation | ✅ URL & method match |
| `deactivate_license(key, hw_id)` | POST `/api/v1/license` `{action:'deactivate'}` | POST `/api/v1/license` `{action:'deactivate'}` → soft-deletes activation | ✅ URL & method match |
| `renew_license(key)` | POST `/api/v1/license` `{action:'renew'}` | ❌ **No `case 'renew'` in server route** | ❌ **Missing** |

### Trial Endpoints

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `start_trial(email, name)` | POST `/api/v1/trial` `{action:'start'}` | POST `/api/v1/trial` `{action:'start'}` → validates & inserts trial | ✅ URL & method match |
| `get_trial_status(hw_id)` | POST `/api/v1/trial` `{action:'status'}` | POST `/api/v1/trial` `{action:'status'}` → queries trials table | ✅ URL & method match |
| `convert_trial(hw_id, plan)` | POST `/api/v1/trial` `{action:'convert'}` | POST `/api/v1/trial` `{action:'convert'}` → generates license key | ✅ URL & method match |

### Device Endpoints

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `bind_device(key, hw_id)` | POST `/api/v1/device` `{action:'bind'}` | POST `/api/v1/device` `{action:'bind'}` → creates activation | ✅ URL & method match |
| `replace_device(key, old_hw, new_hw)` | POST `/api/v1/device` `{action:'replace'}` | POST `/api/v1/device` `{action:'replace'}` → swaps hardware | ✅ URL & method match |

### OTP Endpoints

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `_request('auth/otp/send', {email})` | POST `/api/v1/auth/otp/send` | POST `/api/v1/auth/otp/send` → generates OTP, sends via Brevo | ✅ URL & method match (returns 500 — missing env vars) |
| `_request('auth/otp/verify', {email, otp})` | POST `/api/v1/auth/otp/verify` | POST `/api/v1/auth/otp/verify` → validates OTP code | ✅ URL & method match |

### Customer Endpoints

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `_request('customer/register', {...})` | POST `/api/v1/customer/register` | POST `/api/v1/customer/register` → inserts customer | ✅ URL & method match |

### GET Endpoints Called as POST (MISMATCHES)

| SDK Method | SDK Call | Public API Route | Match |
|-----------|----------|-----------------|-------|
| `_request('countries', ...)` | POST `/api/v1/countries` | **GET** `/api/v1/countries` | ❌ **405 Method Not Allowed** |
| `_request('status', ...)` | POST `/api/v1/status` | **GET** `/api/v1/status` | ❌ **405 Method Not Allowed** |

## Mismatch Analysis

### 1. Renew Action Missing (HIGH)
- **File:** `D:\websmith\app\api\v1\license\route.ts:188` — switch statement handles `validate`, `activate`, `deactivate` only
- **No `case 'renew':`** — The SDK's `renew_license()` sends `{action:'renew'}` which will return an unknown action error
- **Workaround**: Renewal must go through the internal API `/internal/backend/licenses/renew` (admin-only)

### 2. Countries + Status GET-Only (MEDIUM)
- **File:** `D:\websmith\app\api\v1\countries\route.ts` — only handles GET
- **File:** `D:\websmith\app\api\v1\status\route.ts:6` — `export async function GET`
- **Root cause:** `ApiClient._request()` always uses `requests.post()` (SDK `client.py:79`)
- **Impact:** `WelcomeDialog._load_countries()` fails silently (countries dropdown empty), status health check fails
- **Verified by test:** Both return HTTP 405

### 3. Validate Requires license_key (MEDIUM)
- **File:** `D:\websmith\app\api\v1\license\route.ts:168-176`
- **Server requires:** `license_key` for ALL actions including `validate`
- **SDK sends:** `{action:'validate', hardware_id}` without `license_key`
- **Impact:** `initialize()` cannot determine license state on first run (handled by Phase 2 fallback)

### 4. OTP Returns 500 (MEDIUM)
- **File:** `D:\websmith\app\api\v1\auth\otp\send\route.ts`
- **Known issue** from Phase 13 — missing `BREVO_API_KEY`/`SENDER_EMAIL` in Vercel env
- **Impact:** Welcome dialog OTP verification fails

## Authentication Match

| Component | SDK Sends | Server Validates | Match |
|-----------|-----------|-----------------|-------|
| API key | `x-api-key` header from `api.public_key` | Queries `developer_api_keys` table | ✅ |
| HMAC signature | HMAC-SHA256 with `api.secret` (empty string) | HMAC-SHA256 with `secret_hash` from DB | ❌ (bypassed via monkey-patch) |
| Product isolation | `product_id` in request body | `validateProductMatch()` | ✅ (when product_id is correct) |

## Summary

11 of 14 SDK calls match their API routes. The 3 mismatches are:
1. **Renew action** — not yet implemented on public API
2. **Countries + Status** — SDK sends POST but server requires GET
3. **HMAC signing** — empty secret in config; bypassed in integration code
