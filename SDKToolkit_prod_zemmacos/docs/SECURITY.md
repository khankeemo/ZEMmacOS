# Security Guide

## Core Principle

The SDK must never access the database. All data flows through the Websmith Internal API.

```
SDK
    ↓
Websmith Internal API
    ↓
PostgreSQL
```

## What the SDK Must Never Do

- Execute SQL
- Know database table names
- Access PostgreSQL directly
- Contain pricing or plan logic
- Store API secrets in plain text
- Bypass hardware validation
- Cache license keys permanently
- Expose OTP codes

## Startup Security Flow

```
Application start
        ↓
Load cache
        ↓
Check onboarding
        ↓
Check trial
        ↓
Check license
        ↓
Validate hardware
        ↓
Allow access
```

The application must block at any failed step.

## Hardware Security

- No hardware fingerprint → activation and trial buttons disabled
- Hardware mismatch → license invalid, application blocks
- Hardware fingerprint is generated locally and never stored on disk in plain text
- Device replacement requires API verification

## OTP Security

- OTP codes expire after 10 minutes
- OTP codes are single-use (verified = true prevents reuse)
- Wrong OTP codes are rejected with `"Invalid OTP code"`
- Already-used OTP codes return `"OTP code already used"`
- Rate limiting applies to both send and verify endpoints

## Trial Security

- One trial per email address
- Trial expiry is enforced server-side
- Closing the Welcome dialog must close the application
- Failed OTP verification blocks trial start

## License Security

- License validation requires internet connectivity
- Hardware binding is enforced on every validation
- Expired licenses are rejected server-side
- Revoked licenses are rejected server-side
- License key reuse across devices is prevented

## Cache Security

- Cache is stored locally for offline status display
- Cache must never contain secrets or raw API keys
- Cache corruption forces re-validation from server

## Enforcement

All security rules are enforced by the Websmith Internal API. The SDK is a client — it requests, the API enforces.
