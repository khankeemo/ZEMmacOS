# 9. API

## 9.1 SDK public APIs

All license APIs are SDK-owned. ZEMmacOS calls the SDK; the SDK calls the Websmith
Internal API. ZEMmacOS never makes HTTP calls to the backend itself.

### Engine — `LicenseEngine(config_path=None, on_license_ready=None)`

| Method | Purpose | Returns |
|---|---|---|
| `initialize()` | decision engine (run once at startup) | `LicenseStatus` |
| `refresh()` | re-sync from backend (None when offline) | `LicenseStatus` |
| `get_hardware_id()` | machine fingerprint | `str` |
| `get_status()` | current status object | `LicenseStatus` |
| `get_license_key()` / `has_license_key()` | current key / flag | `str` / `bool` |
| `validate_license_key(key, hardware_id=None)` | one-shot validation (no state change) | result dict |
| `send_otp(email)` | OTP send (Welcome / Activation / Renewal) | result dict |
| `verify_otp(email, otp)` | OTP verify (normalizes 4xx to result) | result dict |
| `register_customer(...)` | customer registration | result dict |
| `get_countries()` | country list | result dict |
| `validate(license_key=None)` | validate + resync | result dict |
| `validate_hardware()` | hardware validation + resync | result dict |
| `activate(license_key)` | activation pipeline | result dict |
| `reactivate(license_key=None)` | reactivation (admin reset) | result dict |
| `start_trial(email, customer_name='', customer_data=None)` | trial start | result dict |
| `convert_trial(plan=None, ...)` | trial conversion | result dict |
| `get_plans()` | store products/plans | result dict |
| `renew(extra_days=None, license_key=None)` | renewal pipeline | result dict |
| `deactivate(license_key=None)` | deactivation + cache reset | result dict |
| `view_hardware_status()` | hardware binding status | result dict |
| `get_hardware_state()` | hardware state machine (`unknown/new/bound/changed/pending_otp/rebound/blocked`) | result dict |
| `bind_device(license_key=None, device_name=None)` | bind device (backend) | result dict |
| `verify_license_for_renewal(key)` | renewal eligibility + plans | result dict |
| `get_license_details(key)` | license details | result dict |
| `get_available_plans(key)` | available renewal plans | result dict |
| `send_renewal_request(...)` | renewal request | result dict |
| `send_reactivation_request(...)` | reactivation request | result dict |
| `send_support_request(...)` | support request | result dict |
| `get_request_history(email)` | request history | result dict |
| `get_trial_status()` | trial status | result dict |
| `create_communication(...)` | conversation create (queues offline) | result dict |
| `get_conversation(id)` / `reply_to_conversation(...)` / `list_conversations(email)` | conversation APIs | result dict |
| `get_notifications(email)` / `mark_notification_read(id)` / `get_unread_notification_count(email)` | notifications | result dict |
| `upload_attachment(conversation_id, file_path)` | attachment upload | result dict |
| `mark_onboarding_complete()` / `is_onboarding_complete()` | onboarding flag | void / bool |
| `set_customer_email(email)` / `get_customer_email()` | customer email cache | void / str |
| `persist_runtime_state()` / `flush_cache()` | pre-restart state | void |

### `LicenseStatus` object (consumed by the UI)

Fields: `valid`, `status`, `expiry_date`, `days_left`, `plan`, `hardware_id`, `message`,
`license_key`, `trial_active`, `customer_name`, `customer_email`, `customer_phone`,
`customer_mobile`, `product_name`, `max_devices`, `device_count`. Serialized via
`to_dict()` / `from_dict()`.

### `UniversalLicenseCenter(config_path, on_license_ready=None, log_fn=None, initial_status=None, reentry=False)`

`show()` returns a result dict `{'status': {...}}` on success or `None` when cancelled.

### `ApiClient` (internal)

`ApiError(status_code, message, data)`, `ConnectionUnavailable(message)` (a subclass of
`ApiError`). The engine translates both into friendly result dicts / statuses.

## 9.2 Backend endpoints used by the SDK

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/backend/license/status` | live license status (single source of truth) |
| POST | `/api/v1/license` | `validate` / `activate` / `renew` / `deactivate` |
| POST | `/api/v1/license/deactivate` | deactivation |
| POST | `/api/v1/license/verify-renewal` | renewal eligibility |
| GET | `/api/v1/license/details/{key}` | license details |
| POST | `/api/v1/trial` | `start` / `status` / `convert` |
| POST | `/api/v1/device` | `bind` / `reset` / `replace` |
| POST | `/api/v1/auth/otp/send`, `/api/v1/auth/otp/verify` | OTP |
| POST | `/api/v1/customer/register`, GET `/api/v1/countries` | customer |
| POST | `/api/v1/reactivations` | reactivation request |
| POST | `/api/v1/request` | universal request |
| POST | `/api/v1/requests` | renewal request |
| POST | `/api/v1/support` | support request |
| POST | `/api/v1/communication/create` + `/{id}/reply` + `/{id}/attach` | communication |
| GET | `/api/v1/communication/{id}`, `/api/v1/communication/list` | conversation read |
| GET | `/api/v1/notifications`, `/api/v1/notifications/unread-count` | notifications |
| POST | `/api/v1/notifications/read` | mark read |
| GET | `/api/v1/store/products` | products/plans |

Auth: `X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature` (HMAC-SHA256, 5-minute window,
nonce replay protection). Handled entirely by `client.py`.

## 9.3 Integration methods (app -> SDK)

| App method | SDK call | Called from |
|---|---|---|
| `_init_license_engine` | `LicenseEngine(...)`, `get_hardware_id()`, `initialize()` | startup |
| `open_activation` | `UniversalLicenseCenter(...).show()` | dashboard, settings, inactive dialog |
| `open_renew_license` | `UniversalLicenseCenter(...).show()` | dashboard, settings |
| `refresh_license` | `engine.initialize()` / `engine.refresh()` | dashboard refresh, periodic |
| `_open_ulc` | `UniversalLicenseCenter(...).show()` with `on_license_ready` | startup when invalid |
| `_on_contact_support` | `center._show_request_dialog("Support", "support")` | support |
| `_on_generate_request` | `center._show_request_dialog("Generate Request", "request")` | inactive dialog |
| `_on_about_clicked` / `_show_about_dialog` | `UniversalLicenseCenter(reentry=True).show()` | About |

## 9.4 Callback flow

```
ULC.show()
   on_license_ready(valid)      # called by the engine when a license resolves
   result = show()              # final result dict
```

`main.py` uses both: the callback (`on_ready`) launches the main app, and the return
value is cross-checked (`result['status']['valid']`) before launching.

## 9.5 Event flow

See [08_EVENT_SYSTEM.md](08_EVENT_SYSTEM.md). The engine emits exactly one
`LicenseStatusChanged` per mutation through `EventBus.emit_status_changed(status)`, and
one `on_license_ready(valid)` per `initialize()` / workflow completion.

## 9.6 Response handling

- **Engine methods** return normalized result dicts:
  `{'success': bool, 'message': str, 'license': {...}, 'customer': {...}, 'error': {...}}`.
- **Transport errors** are converted:
  - `ApiError` (4xx) → result with the backend's exact `message` (Rule 5 — never
    substitute a generic local string).
  - `ConnectionUnavailable` → engine falls back to cached state; communication APIs queue
    the message for offline retry.
- **Invalid OTP (4xx)** → normalized to `{'success': False, 'message': 'OTP is not
  valid.'}` so every flow shows the same message.
- **UI never reads the client directly** — it consumes `LicenseStatus` and result dicts
  from the engine.
- **User-friendly errors:** SDK dialogs show what happened, why, and the next step; no
  technical details are exposed to the customer.

## 9.7 Example integration snippet (ZEMmacOS `main.py`)

```python
engine = LicenseEngine(config_path=_get_sdk_config_path())
engine.get_hardware_id()
status = engine.initialize()                # decision engine (server-first)
if status.valid:
    self.license_status = status
    self._launch_main_app()
else:
    center = UniversalLicenseCenter(
        config_path=_get_sdk_config_path(),
        on_license_ready=self._on_license_resolved,
        log_fn=self.log_live,
        initial_status=status,
    )
    result = center.show()
```
