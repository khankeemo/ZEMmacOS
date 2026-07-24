# WSD Universal License Control System — Developer Integration Guide

## Purpose

The SDK is a complete plug-and-play license system. The host application must never implement OTP UI, activation forms, trial logic, hardware binding, renewal, device replacement, database access, or license validation.

The SDK owns everything. All user-facing requests (activation, renewal, device replacement, support, hardware issues, purchases) are routed through the `UniversalLicenseCenter` backed by `POST /api/v1/request`.

## Architecture

```
Application
├── main.py
├── dashboard.py
├── settings.py
├── sidebar.py
└── screens/
        │
        ▼
WSD_SDK_PROJECTNAME_PRODUCTID/
├── universal_license_center.py   ← Full-featured license GUI
├── universal_email_dialog.py     ← Internal email form (used by ULC)
├── license_engine.py             ← Orchestrates license ops
├── client.py                     ← HMAC-signed HTTP client
├── hardware.py                   ← Machine fingerprint
├── cache.py                      ← Local status cache
├── crypto.py                     ← HMAC-SHA256 signing
        │
        ▼
Websmith Internal API
        │
        ▼
PostgreSQL
```

## Startup Workflow

Developers only do:

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine

engine = LicenseEngine()
status = engine.initialize()
```

The SDK internally performs:

```
Application start
        ↓
Load cache
        ↓
Check trial
        ↓
Check license
        ↓
Validate hardware
        ↓
Open application
```

If any step fails, the application blocks.

## Universal License Center

**File:** `universal_license_center.py`

**Purpose:** Primary user-facing Tkinter GUI for all license management.

**UI Buttons:**
- View License Status
- Start Free Trial
- Activate License
- Buy License
- Renew License
- Replace Device
- Hardware Issue
- Contact Support
- Request History

**Behavior:**
- Status display at the top (plan, expiry, days remaining, hardware ID)
- Each button opens the appropriate dialog within the Universal License Center
- All requests are sent via `POST /api/v1/request` to the Websmith Internal API
- The Internal API forwards to `support@websmithdigital.com`

## License Center Workflow

The Universal License Center handles all customer workflows through a single interface:
- Welcome / Trial onboarding (new customers)
- License activation
- License renewal
- License reactivation
- Support requests
- Request history

All requests are sent via `POST /api/v1/request` — SDK never sends email directly.

## Backend APIs

### Request (primary)
- `POST /api/v1/request` — Send a request of any type (BUY, RENEW, SUPPORT, ACTIVATION, DEVICE_REPLACEMENT, HARDWARE, GENERAL)
- `GET /api/v1/request?email=<email>` — Get request history

### License
- `POST /api/v1/license` — Validate, activate, renew
- `POST /api/v1/license/deactivate` — Deactivate
- `GET /api/v1/license/details/<key>` — Details
- `POST /api/v1/license/verify-renewal` — Renewal verification

### Trial
- `POST /api/v1/trial` — Start, status, convert

### Device
- `POST /api/v1/device` — Bind, replace, reset

### Store
- `GET /api/v1/store/products` — Available products/plans

## Email Flow

All SDK email requests follow this path:

```
UniversalLicenseCenter → Support Form
        ↓
POST /api/v1/request    ← SDK calls API
        ↓
Websmith Internal API receives request
        ↓
Email Service sends to support@websmithdigital.com
```

SDK never sends SMTP directly.

## Security Rules

The SDK must never:
- Access PostgreSQL directly
- Execute SQL
- Know table names
- Contain pricing
- Contain plan logic
- Bypass hardware validation
- Send SMTP email directly

Everything flows through:

```
SDK
    ↓
Websmith Internal API
    ↓
PostgreSQL / Email Service
```

## Integration Checklist

- [ ] Copy SDK folder into project
- [ ] Import LicenseEngine and call `initialize()`
- [ ] Launch UniversalLicenseCenter for full GUI
- [ ] Run application

No other licensing code should be required.
