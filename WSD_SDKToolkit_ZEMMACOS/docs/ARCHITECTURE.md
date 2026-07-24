# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────┐
│ Developer Application                               │
│  ┌───────────────────────────────────────────────┐  │
│  │ WSD SDK                                       │  │
│  │  ┌─────────────────────────────────────┐     │  │
│  │  │ Universal License Center (Tkinter)  │     │  │
│  │  │  • Status Panel                     │     │  │
│  │  │  • Action Buttons (9)               │     │  │
│  │  └──────────────┬──────────────────────┘     │  │
│  │                 │ opens                      │  │
│  │  ┌──────────────▼──────────────────────┐     │  │
│  │  │ Universal Email Dialog              │     │  │
│  │  │ (single form — all request types)   │     │  │
│  │  └──────────────┬──────────────────────┘     │  │
│  │  ┌─────────┐ ┌───────┐ ┌──────────────┐     │  │
│  │  │License  │ │Cache  │ │Hardware      │     │  │
│  │  │Engine   │ │Manager│ │Detector      │     │  │
│  │  └────┬────┘ └───────┘ └──────────────┘     │  │
│  │  ┌────▼────┐                               │  │
│  │  │ApiClient│ (HMAC-SHA256)                  │  │
│  │  └────┬────┘                               │  │
│  └───────┼───────────────────────────────────┘  │
└──────────┼──────────────────────────────────────┘
           │ HTTPS + HMAC
           ▼
┌─────────────────────────────────────────────────────┐
│ Websmith Internal API                                │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ /api/v1/  │ │ License  │ │ Trial             │  │
│  │ request   │ │ (CRUD)   │ │ (Management)      │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐   │
│  │ Customer │ │ Plans    │ │ Admin             │   │
│  │ (Store)  │ │ (Pricing)│ │ (Dashboard)       │   │
│  └──────────┘ └──────────┘ └───────────────────┘   │
└──────────────────────┬──────────────────────────────┘
           │ SQL + Email Service
           ▼
┌─────────────────────────────────────────────────────┐
│ PostgreSQL (Neon) + Email Service                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐   │
│  │ customers│ │ licenses │ │ email_queue       │   │
│  ├──────────┤ ├──────────┤ ├───────────────────┤   │
│  │ products │ │ plans    │ │ support@          │   │
│  │          │ │          │ │ websmithdigital   │   │
│  └──────────┘ └──────────┘ └───────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## SDK Components

| Component | File | Responsibility |
|-----------|------|----------------|
| License Engine | `license_engine.py` | Orchestrates all license operations |
| API Client | `client.py` | HTTP client with HMAC signing |
| Cache Manager | `cache.py` | Local status cache |
| Hardware Detector | `hardware.py` | Machine fingerprint |
| Crypto Utils | `crypto.py` | HMAC signature generation |
| Universal License Center | `universal_license_center.py` | Full Tkinter license GUI (single customer workflow) |

## Data Flows

### Email Request (all types)
```
UniversalLicenseCenter → Support / Renewal / Reactivation Form
        ↓
POST /api/v1/request (BUY|RENEW|SUPPORT|ACTIVATION|DEVICE_REPLACEMENT|HARDWARE|GENERAL)
        ↓
Websmith Internal API validates and queues
        ↓
Email Service sends to support@websmithdigital.com
```

### License Activation
```
User clicks "Activate License" in UniversalLicenseCenter
        ↓
Activation dialog opens (hardware ID auto-filled)
        ↓
User enters license key → POST /api/v1/license (activate)
        ↓
Cache refresh → Application unlocks
```

### Startup
```
Load cache → Check trial → Check license → Validate hardware → Open app
```

### Trial Start
```
User clicks "Start Free Trial" → Email dialog → POST /api/v1/trial → Bind hardware
```

## Technology Stack

- **Client SDK:** Python 3.8+
- **API:** Next.js serverless (Vercel)
- **Database:** PostgreSQL (Neon)
- **Email:** Internal Email Service → support@websmithdigital.com
- **Auth:** HMAC-SHA256 request signing
- **Cache:** Local JSON file
- **Hardware ID:** CPU + machine fingerprint
- **UI:** Tkinter (built-in)
