# ZEM MAC OS SDK
## 1.0.0

## Installation

```bash
pip install SDK_ZEM_MAC_OS_prod_zemmacos
```

## Quick Start

```python
from SDK_ZEM_MAC_OS_prod_zemmacos import Client, LicenseEngine, LicenseStatus

client = Client("YOUR_API_KEY", "API_URL")
engine = LicenseEngine(client)

# Initialize and check status
status = engine.initialize()
if status.valid:
    print(f"License valid: {status.status}")
else:
    print(f"Status: {status.status} - {status.message}")

# Activate a license
result = engine.activate("LICENSE_KEY_HERE")
print(result)
```

## License

Copyright (c) 2026 ZEM MAC OS
