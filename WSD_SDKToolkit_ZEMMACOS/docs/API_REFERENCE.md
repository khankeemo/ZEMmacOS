# API Reference

All endpoints are called through the `ApiClient` class. The SDK never queries the database directly.

## Authentication

Every request requires API Key + HMAC-SHA256 signature. The `ApiClient` handles all headers automatically.

## Client Methods

| Method | HTTP | API Endpoint | Description |
|--------|------|-------------|-------------|
| `send_otp()` | POST | `/api/v1/auth/otp/send` | Send OTP to email |
| `verify_otp()` | POST | `/api/v1/auth/otp/verify` | Verify OTP code |
| `store_customer()` | POST | `/api/v1/customer/register` | Register customer |
| `start_trial()` | POST | `/api/v1/trial` | Start trial |
| `get_trial_status()` | POST | `/api/v1/trial` | Check trial status (action: status) |
| `convert_trial()` | POST | `/api/v1/trial` | Convert trial to license |
| `validate_license()` | POST | `/api/v1/license` | Validate license |
| `activate_license()` | POST | `/api/v1/license` | Activate license |
| `deactivate_license()` | POST | `/api/v1/license` | Deactivate license |
| `get_license_details()` | POST | `/api/v1/license/details` | Get license info |
| `get_license_history()` | POST | `/api/v1/license/history` | Get license timeline |
| `renew_license()` | POST | `/api/v1/license/renew` | Renew license |
| `replace_device()` | POST | `/api/v1/device` | Replace device (action: replace) |
| `bind_device()` | POST | `/api/v1/device` | Bind device |
| `reset_device()` | POST | `/api/v1/device` | Reset device |
| `get_plans()` | GET | `/api/v1/plans` | List plans |
| `get_countries()` | GET | `/api/v1/countries` | List countries |
| `get_status()` | GET | `/api/v1/status` | API health status |
| `get_notifications()` | GET | `/api/v1/notifications` | User notifications |

## Engine Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Check license/trial status (cache fallback) |
| `get_status()` | Get cached `LicenseStatus` object |
| `activate(key)` | Activate license with hardware binding |
| `deactivate(key)` | Deactivate license on current device |
| `start_trial(email)` | Start trial with OTP verification flow |
| `check_trial()` | Check trial status |
| `convert_trial(plan)` | Convert active trial to paid license |
| `send_otp(email)` | Send verification OTP |
| `verify_otp(email, code)` | Verify OTP code |
| `store_customer(data)` | Register customer details |
| `get_license_details(key)` | Fetch license details |
| `get_license_history(key)` | Fetch license audit timeline |
| `renew(plan_id)` | Renew license |
| `replace_hardware()` | Move license to current (new) hardware |
| `bind_device(key)` | Bind license to current device |
| `get_plans()` | Get available plans for product |
| `get_countries()` | Get country list |
| `get_api_status()` | Get API health |
| `get_notifications()` | Get user notifications |
| `refresh()` | Force re-initialize from API |
| `clear_cache()` | Clear local license cache |

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_API_KEY` | 401 | API key not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `PRODUCT_MISMATCH` | 403 | Key belongs to different product |
| `LICENSE_NOT_FOUND` | 404 | License key doesn't exist |
| `LICENSE_EXPIRED` | 403 | License has expired |
| `LICENSE_REVOKED` | 403 | License revoked |
| `MAX_DEVICES_EXCEEDED` | 403 | Device limit reached |

## Security Rules

- The SDK **never** accesses PostgreSQL directly
- The SDK **never** executes SQL
- The SDK **never** knows database table names
- The SDK **never** contains pricing
- The SDK **never** contains plan logic

## LicenseStatus Fields

| Field | Type | Description |
|-------|------|-------------|
| `valid` | bool | License or trial is valid |
| `status` | str | Current status string |
| `expires_at` | str/None | Expiry date |
| `days_remaining` | int | Days until expiry |
| `plan` | str/None | Current plan name |
| `plan_id` | str/None | Current plan ID |
| `hardware_id` | str/None | Bound hardware ID |
| `device_name` | str/None | Bound device name |
| `trial_active` | bool | Trial in progress |
| `license_active` | bool | License active |
| `max_devices` | int | Max allowed devices |
| `device_count` | int | Current device count |
| `license_key` | str/None | Active license key |
| `message` | str | Human-readable status |
| `product` | str/None | Product name |
| `product_version` | str/None | Product version |
