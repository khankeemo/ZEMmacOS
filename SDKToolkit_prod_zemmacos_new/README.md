# Python SDK for ZEM MAC OS

This directory contains the Python language template for the Universal License Platform.

## Mandatory Modules

- `license_engine.py` — Startup decision engine, license validation, state management
- `hardware.py` — Hardware fingerprint detection
- `cache.py` — Local persistence, offline support, message queue
- `client.py` — HMAC-signed API client
- `crypto.py` — Cryptographic utilities
- `activation.py` — License activation workflow
- `renewal.py` — License renewal workflow
- `reactivation.py` — License reactivation workflow
- `trial.py` — Trial management workflow
- `communication.py` — Universal conversation engine
- `notifications.py` — System notifications
- `support.py` — Support request workflow
- `sales.py` — Sales enquiry workflow
- `config.py` — Configuration loading, branding
- `universal_license_center.py` — Main customer-facing GUI
- `welcome.py` — Onboarding workflow
- `__init__.py` — Package initialisation

## Placeholder Standard

All templates use `DOUBLE-BRACE-PLACEHOLDER` tokens (e.g., `ZEM MAC OS`) replaced at generation time.

| Placeholder | Source |
|-------------|--------|
| `ZEM MAC OS` | `product.name` from api-config.json |
| `prod_zemmacos` | `product.id` from api-config.json |
| `` | `api.url` from api-config.json |
| `1.0.0` | `SDK_VERSION` environment variable |
| `python` | Runtime identifier |
| `` | `branding.support_email` from config |
| `` | `branding.sales_email` from config |
| `` | `branding.company_name` from config |
| `` | `branding.website_url` from config |
| `` | `branding.primary_color` from config |
| `` | `product.trial_days` from config |
| `` | `plan.max_devices` from config |
| `` | `branding.sender_name` from config |

## Template Validation

Generation fails if:
- Any mandatory module is missing
- Any placeholder remains unreplaced
- Any hardcoded company name, URL, or email address exists
- Duplicate implementation exists in both template and runtime generator

## Architecture

```
Language Template (this directory)
  ↓
Runtime Generator (orchestration only)
  ↓
Generated SDK (output only)
```
