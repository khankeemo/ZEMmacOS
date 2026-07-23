# Quick Start Guide

## 1. Copy SDK Folder

Copy `WSD_SDK_PROJECTNAME_PRODUCTID/` into your project.

## 2. Initialize

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine

engine = LicenseEngine()
status = engine.initialize()
```

## 3. Launch Universal License Center

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.universal_license_center import UniversalLicenseCenter

center = UniversalLicenseCenter(engine)
center.show()
```

## 4. Use Universal Email Dialog (any request type)

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.universal_email_dialog import UniversalEmailDialog

dialog = UniversalEmailDialog(engine._client, engine._hardware, engine._cache)
result = dialog.show("SUPPORT", customer_name="John", customer_email="john@example.com")
if result.get("sent"):
    print("Request sent to support@websmithdigital.com")
```

## 5. Run

```bash
pip install requests
python main.py
```

That is all. No additional licensing code is required.
