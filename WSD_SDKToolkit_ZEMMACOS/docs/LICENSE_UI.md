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

## Request Types (via Universal License Center)

All requests use the `UniversalLicenseCenter` interface, which internally uses the email dialog.

**Request Types:**
`BUY`, `RENEW`, `SUPPORT`, `ACTIVATION`, `DEVICE_REPLACEMENT`, `HARDWARE`, `GENERAL`

**API:** All types use `POST /api/v1/request`

## Import Pattern

```python
from WSD_SDK_PROJECTNAME_PRODUCTID import UniversalLicenseCenter
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine

engine = LicenseEngine()
status = engine.initialize()

# Full license center GUI
center = UniversalLicenseCenter()
result = center.show()
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
