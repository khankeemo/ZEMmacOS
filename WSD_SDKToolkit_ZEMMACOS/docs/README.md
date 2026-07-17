# WSD SDK — PRODUCT_NAME

## What Is WSD SDK?

WSD SDK is a complete plug-and-play license system. Copy the folder, add a dashboard widget, add an activation button, and run your application.

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
├── welcome.py
├── activation.py
├── renewal.py
├── device_replace.py
├── manifest.json

├── widgets/
│   ├── dashboard_widget.py
│   ├── settings_widget.py
│   ├── status_widget.py
│   └── activation_button.py

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
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.dashboard_widget import LicenseWidget
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.activation_button import ActivationButton

engine = LicenseEngine()
LicenseWidget(parent).build()
ActivationButton(parent, engine).build()
engine.initialize()
```

## Dashboard

Import:

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.dashboard_widget import LicenseWidget
```

Place in top-right corner.

## Settings

Import:

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.settings_widget import SettingsWidget
```

Place under: `Settings > License`

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
