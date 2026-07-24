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

## 4. Use Universal License Center (all-in-one)

```python
from WSD_SDK_PROJECTNAME_PRODUCTID import UniversalLicenseCenter

center = UniversalLicenseCenter()
result = center.show()
if result.get("status"):
    print("License status:", result["status"]["status"])
```

## 5. Run

```bash
pip install requests
python main.py
```

That is all. No additional licensing code is required.
