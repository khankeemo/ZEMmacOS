# ZEM MAC OS SDK
## 1.0.0

## Installation

```bash
pip install zemmacos
```

## Quick Start

```python
from zemmacos import Client, LicenseEngine

client = Client("YOUR_API_KEY", "API_URL")
engine = LicenseEngine(client)

result = engine.validate("LICENSE_KEY")
print("Valid:", engine.is_valid())
```

## License

Copyright (c) 2026 ZEM MAC OS
