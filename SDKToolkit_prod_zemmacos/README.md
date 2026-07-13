# ZEM MAC OS SDK
## 1.0.0

## Installation

```bash
pip install WSD_SDK_ZEM_MAC_OS_prod_zemmacos
```

## Quick Start

```python
from WSD_SDK_ZEM_MAC_OS_prod_zemmacos import LicenseEngine, LicenseStatus

engine = LicenseEngine()
status = engine.initialize()

if status.valid:
    print(f"License {status.status} — {status.days_remaining} day(s) remaining")
else:
    print(f"Status: {status.status} — {status.message}")
    # Activate: engine.activate("LICENSE_KEY")
    # Trial:    engine.start_trial(email="user@example.com")
```

## License

Copyright (c) 2026 ZEM MAC OS
