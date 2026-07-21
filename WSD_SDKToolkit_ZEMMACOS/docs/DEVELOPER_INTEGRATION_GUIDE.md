# WSD Universal License Control System — Developer Integration Guide

## Purpose

The SDK is a complete plug-and-play license system. The host application must never implement OTP UI, activation forms, trial logic, hardware binding, renewal, device replacement, database access, or license validation.

The SDK owns everything.

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
├── welcome.py
├── activation.py
├── renewal.py
├── renew_license_dialog.py
├── device_replace.py
├── license_engine.py
├── client.py
├── hardware.py
├── cache.py
├── widgets/
│   ├── dashboard_widget.py
│   ├── settings_widget.py
│   ├── status_widget.py
│   └── activation_button.py
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
Check onboarding
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

## Welcome Dialog

**File:** `welcome.py`

**Purpose:** First-time onboarding for trial users.

**UI:**

```
Name:      [_______________]
Email:     [_______________]
Mobile:    [_______________]
Country:   [_______________]
Company:   [_______________]

[Send OTP]
[Verify OTP]
```

**API Flow:**

```
POST /api/v1/auth/otp/send
        ↓
POST /api/v1/auth/otp/verify
        ↓
POST /api/v1/customer/register
        ↓
POST /api/v1/trial
```

**Security Rule:** Closing the Welcome dialog must close the entire application.

**Important:** Developers must never open `welcome.py` manually. It is triggered automatically by `engine.initialize()` when no customer or trial exists.

## Dashboard Integration

**Placement:** Top-right corner of your dashboard.

```
┌──────────────────────────────────────────┐
│ Dashboard                                │
│                                          │
│                         ┌─────────────┐  │
│                         │ License     │  │
│                         │ Active      │  │
│                         │ 7 days left │  │
│                         └─────────────┘  │
└──────────────────────────────────────────┘
```

**Import:**

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.dashboard_widget import LicenseWidget
```

**Usage:**

```python
LicenseWidget(parent)
```

**Contents:**
- Trial active / Licensed indicator
- Remaining days
- Expiry date
- Hardware status

**Auto-refresh:** Every 60 seconds.

## Settings Integration

**Placement:** `Settings > License`

```
┌────────────────────────────┐
│ License                    │
├────────────────────────────┤
│ Product                    │
│ SDK Version                │
│ Runtime                    │
│ Hardware ID                │
│ Status                     │
│ Expiry                     │
│ Remaining Days             │
│                            │
│ [Activate]                 │
│ [Renew]                    │
│ [Replace Device]           │
│ [Refresh]                  │
│ [Open Welcome]             │
└────────────────────────────┘
```

**Import:**

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.settings_widget import SettingsWidget
```

## Activation Flow

**File:** `activation.py`

**Import:**

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.activation import ActivationDialog
```

**Usage:**

```python
ActivationDialog().show()
```

**Workflow:**

```
User opens activation dialog
        ↓
Generate hardware fingerprint
        ↓
Enable license textbox
        ↓
Enter license key
        ↓
Fetch license details
        ↓
Show:
  • Plan
  • Expiry
  • Devices
  • Remaining days
        ↓
Activate
        ↓
Bind hardware
        ↓
Refresh cache
```

**UI:**

```
┌──────────────────────────────────┐
│ Activate License                 │
├──────────────────────────────────┤
│ Product                          │
│ Version                          │
│                                  │
│ Hardware ID                      │
│ Device name                      │
│                                  │
│ License key                      │
│                                  │
│ Plan                             │
│ Expiry                           │
│ Devices                          │
│                                  │
│ [Activate]                       │
│ [Renew]                          │
│ [Replace Device]                 │
└──────────────────────────────────┘
```

## Renewal

**File:** `renewal.py`

**APIs:**
- `GET  /api/v1/plans` — fetch available plans
- `POST /api/v1/license/renew` — renew license

**Rules:**
- SDK only displays plans and pricing.
- Backend owns pricing, plans, and business rules.

## Device Replacement

**File:** `device_replace.py`

**API:** `POST /api/v1/license/replace-device`

**Workflow:**

```
Old hardware
        ↓
Generate new hardware
        ↓
Confirm replacement
        ↓
Refresh status
```

## Widgets

| Widget | Import | Placement |
|--------|--------|-----------|
| `LicenseWidget` | `widgets.dashboard_widget` | Dashboard top-right |
| `SettingsWidget` | `widgets.settings_widget` | Settings > License |
| `ActivationButton` | `widgets.activation_button` | Any toolbar |
| `StatusWidget` | `widgets.status_widget` | Status bar |

## Backend APIs

### OTP
- `POST /api/v1/auth/otp/send`
- `POST /api/v1/auth/otp/verify`

### Trial
- `POST /api/v1/trial`
- `POST /api/v1/trial/status`

### Customer
- `POST /api/v1/customer/register`

### License
- `POST /api/v1/license`
- `GET  /api/v1/license/details`
- `POST /api/v1/license/renew`
- `POST /api/v1/license/replace-device`

### Plans
- `GET /api/v1/plans`

### Countries
- `GET /api/v1/countries`

### Status
- `GET /api/v1/status`

## Security Rules

The SDK must never:
- Access PostgreSQL directly
- Execute SQL
- Know table names
- Contain pricing
- Contain plan logic
- Bypass hardware validation

Everything flows through:

```
SDK
    ↓
Websmith Internal API
    ↓
PostgreSQL
```

## Integration Checklist

- [ ] Copy SDK folder into project
- [ ] Import dashboard widget
- [ ] Import activation dialog
- [ ] Add settings page
- [ ] Run application

No other licensing code should be required.
