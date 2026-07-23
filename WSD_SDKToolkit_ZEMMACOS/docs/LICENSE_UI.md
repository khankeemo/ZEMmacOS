# License UI Components

## Universal License Center

**File:** `universal_license_center.py`

**Purpose:** Primary Tkinter GUI for all license management operations.

**Status Display:**
- License status (Active / Trial / Unlicensed)
- Plan name
- Expiry date
- Days remaining
- Hardware ID
- Customer name and email

**Buttons:**
| Button | Opens | Request Type |
|--------|-------|-------------|
| View License Status | Status panel | — |
| Start Free Trial | Email dialog | TRIAL |
| Activate License | Email dialog | ACTIVATION |
| Buy License | Email dialog | BUY |
| Renew License | Email dialog | RENEW |
| Replace Device | Email dialog | DEVICE_REPLACEMENT |
| Hardware Issue | Email dialog | HARDWARE |
| Contact Support | Email dialog | SUPPORT |
| Request History | History view | — |

## Universal Email Dialog

**File:** `universal_email_dialog.py`

**Purpose:** Single reusable email form for all request types.

**Fields:**
- Your Name (required)
- Your Email (required)
- License Key (auto-populated if available)
- Plan (auto-populated if available)
- Subject (auto-generated from request type)
- Message (required)

**Request Types:**
`BUY`, `RENEW`, `SUPPORT`, `ACTIVATION`, `DEVICE_REPLACEMENT`, `HARDWARE`, `GENERAL`

**API:** All types use `POST /api/v1/request`

## Import Pattern

```python
from WSD_SDK_PROJECTNAME_PRODUCTID import UniversalLicenseCenter, UniversalEmailDialog
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine

engine = LicenseEngine()
status = engine.initialize()

# Full GUI
center = UniversalLicenseCenter(engine)
center.show()

# Direct email dialog
dialog = UniversalEmailDialog(engine._config, engine._client, engine._hardware, engine._cache)
result = dialog.show("SUPPORT", customer_name="User")
```

## Recommended UI Structure

```
Settings
  └── License
       ├── Status
       ├── Product
       ├── SDK Version
       ├── Runtime
       ├── Hardware ID
       ├── Expiry
       ├── Remaining Days
       ├── [Launch License Center]
       └── [Refresh]
```
