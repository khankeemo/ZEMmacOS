# WSD SDK — PRODUCT_NAME

## What Is WSD SDK?

WSD SDK is a complete plug-and-play license system. Copy the folder, initialize the engine, and run your application. All license operations (activation, trial, renewal, device replacement, support) go through a single Universal Email Dialog backed by `POST /api/v1/request`.

No additional licensing code is required.

## Folder Structure

```
WSD_SDK_PROJECTNAME_PRODUCTID/

├── __init__.py
├── client.py
├── cache.py
├── crypto.py
├── hardware.py
├── license_engine.py
├── universal_email_dialog.py
├── universal_license_center.py

├── config/
│   └── api-config.json

├── assets/
│   ├── logo.svg
│   └── badge.svg

└── docs/
    ├── README.md
    ├── QUICK_START.md
    ├── DEVELOPER_INTEGRATION_GUIDE.md
    ├── LICENSE_UI.md
    ├── API_REFERENCE.md
    ├── SECURITY.md
    ├── ARCHITECTURE.md
    └── TROUBLESHOOTING.md
```

## 3-Minute Integration

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine

engine = LicenseEngine()
status = engine.initialize()
print(f"Status: {status.status} — {status.message}")
```

## Universal License Center

The `UniversalLicenseCenter` provides a full-featured Tkinter GUI with one-click access to all license operations. It is the primary user-facing component.

## Detailed Documentation

| Document | Purpose |
|----------|---------|
| `QUICK_START.md` | 5-step integration |
| `DEVELOPER_INTEGRATION_GUIDE.md` | Full architecture & integration |
| `LICENSE_UI.md` | UI components reference |
| `API_REFERENCE.md` | All SDK methods & fields |
| `SECURITY.md` | Security rules & constraints |
| `ARCHITECTURE.md` | System architecture |
| `TROUBLESHOOTING.md` | Common issues & solutions |
