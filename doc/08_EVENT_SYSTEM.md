# 8. Event System

The event system is provided by the SDK's `EventBus` (`WSD_SDKToolkit_ZEMMACOS/event_bus.py`).
The **engine is the only emitter** of state-changing events. Screens subscribe and
re-render from event payloads; they never refresh each other and never poll.

## 8.1 Canonical events

### `LicenseStatusChanged` (LICENSE_STATUS_CHANGED)

| Property | Value |
|---|---|
| Constant | `LICENSE_STATUS_CHANGED = "LicenseStatusChanged"` |
| Emitter | `LicenseEngine._publish_status()` — engine only |
| Payload | the current `LicenseStatus` object |
| When | once per state mutation: after `initialize()`, `refresh()`, activation, renewal, trial, reactivation, bind, deactivation, revocation |

**Subscribe:**

```python
from WSD_SDKToolkit_ZEMMACOS import EventBus
EventBus.subscribe_status_changed(callback)      # callback(new_status)
EventBus.unsubscribe_status_changed(callback)
EventBus.get_last_status()                       # cached last status
```

**Subscribers / expected behavior:**

| Subscriber | Expected behavior |
|---|---|
| Dashboard license card (`_update_dashboard_license`) | re-render status/plan/key/validity |
| Header badge (`_update_header_license_badge`) | update badge text/color |
| Settings license panel (`_update_license_panel`) | re-render panel |
| Any SDK screen | re-render from the event payload |

### `on_license_ready` callback

| Property | Value |
|---|---|
| Emitter | `LicenseEngine._notify_ready(valid)` |
| Registered | `LicenseEngine(config_path, on_license_ready=cb)` and ULC |
| Payload | `bool valid` |
| When | after every `initialize()` and every state-changing workflow |

### Generic events (`EventBus.subscribe(event, cb)` / `emit`)

Auxiliary channel used for progress stages, connectivity, and workflow state. Screens can
subscribe by name; the engine emits `WorkflowProgress.stage(...)` messages through the
shared `WorkflowProgress` and the generic channel.

## 8.2 Workflow progress stages (`WorkflowProgress`)

Used by the engine to report the current step of a workflow:

| Stage | Meaning |
|---|---|
| `CHECKING_SERVER` | refresh — contacting backend |
| `CHECKING_LICENSE` | validating license key |
| `CHECKING_HARDWARE` | hardware validation |
| `CHECKING_CUSTOMER` | customer lookup |
| `SENDING_OTP` / `OTP_SENT` / `WAITING_OTP` / `OTP_VERIFIED` | OTP lifecycle |
| `UPDATING_LICENSE` | applying new state |
| `SAVING_CACHE` | persisting to cache |
| `REFRESHING_SDK` / `REFRESHING_DASHBOARD` | refresh phase |
| `COMPLETED` | workflow complete |

## 8.3 SDK canonical log events (one per stage)

Defined in `license_engine.py` and written to `LiveLog`:

```
WORKFLOW_START      workflow entered (guard __enter__)
WORKFLOW_COMPLETE   workflow succeeded (guard __exit__)
WORKFLOW_ERROR      workflow raised
VALIDATION_START    validate_license_key called
VALIDATION_SUCCESS  license validated
VALIDATION_ERROR    validation failed
OTP_SENT            send_otp succeeded
OTP_VERIFIED        verify_otp succeeded
ACTIVATION_STARTED  activation/reactivation started
ACTIVATION_SUCCESS  activation succeeded
RENEWAL_SUCCESS     renewal succeeded
CACHE_REFRESH       cache refreshed from backend
STATUS_CHANGED      LicenseStatusChanged emitted
```

Additional categories: `engine.initialize`, `license.valid`, `license.invalid`,
`license.offline`, `license.cache`, `trial.started`, `trial.success`, `hardware.bound`,
`ALREADY_ACTIVATED`, `Runtime state saved`, `Cache flushed to disk`, etc.

## 8.4 Event flow diagram

```
User Click -> Workflow Lock -> Validation -> OTP -> API -> Cache Refresh
    -> Status Refresh -> Event (LicenseStatusChanged) -> Entire UI Refresh
    -> Success -> Unlock Workflow
```

## 8.5 How the app reacts

- `main.py` holds `self.license_status`; UI methods read it directly and also receive the
  `LicenseStatusChanged` event through the engine's `_publish_status()` (the engine holds
  the same object, so both paths see identical state).
- `on_license_ready` is used by the ULC to unlock the app once a license resolves
  (`_open_ulc` passes `on_license_ready=on_ready` which calls `_launch_main_app`).
