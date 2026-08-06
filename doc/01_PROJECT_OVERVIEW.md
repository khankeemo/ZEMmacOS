# 1. Project Overview

## What is ZEMmacOS

ZEMmacOS is a **macOS Download Manager** for Windows / macOS / Linux. It downloads macOS
installer packages directly from Apple's public software catalog (`gibMacOS` engine) using
a segmented, resumable downloader, and presents a modern Tkinter desktop UI.

- **Product name:** ZEMmacOS
- **Version:** 3.0.0 (see `config/project_manifest.json`)
- **Publisher:** WebSmithDigital
- **License enforcement:** Websmith Digital Universal License Platform (via the generated
  WSD Universal SDK)

## What ZEMmacOS is NOT

- ZEMmacOS is **not** a license server and does **not** contain license logic.
- ZEMmacOS does **not** compute or store authoritative license state.
- ZEMmacOS does **not** implement activation, renewal, trial, hardware binding, or OTP
  flows itself. All of those are owned by the SDK and the Websmith backend.

## Licensing model

Licensing is enforced by the **WSD Universal SDK** (`WSD_SDKToolkit_ZEMMACOS`), a
per-product generated Python SDK that talks to the Websmith Digital Internal API. ZEMmacOS
only:

1. **Initializes** the SDK at startup (`LicenseEngine.initialize()`).
2. **Calls SDK public APIs** (activation, renewal, trial, refresh, request flows).
3. **Displays SDK UI** (Universal License Center, Welcome, Success, Restart dialogs).
4. **Consumes SDK state** (the `LicenseStatus` object).
5. **React** to SDK events (`EventBus.LicenseStatusChanged`, callbacks).

## Application entry point

`main.py` is the single entry point. It builds a Tk root, runs the SDK startup sequence,
and then either launches the main application or shows the Universal License Center
(depending on the license decision).

## Key concepts

| Concept | Owner | Notes |
|---|---|---|
| `LicenseEngine` | SDK | Decision engine; runs once at startup; server-first state. |
| `LicenseStatus` | SDK | Immutable view of current license state consumed by the UI. |
| `UniversalLicenseCenter` (ULC) | SDK | Customer-facing license UI; all licensing workflows. |
| `EventBus` | SDK | Single channel for `LicenseStatusChanged` and workflow events. |
| `CacheManager` | SDK | Local offline cache at `~/.websmith/prod_zemmacos/`. |
| `HardwareDetector` | SDK | Machine fingerprint used for hardware binding. |
| App settings / business logic | ZEMmacOS | Catalogue, downloads, themes, logs. |

## Reference documents

- Generated SDK integration guide: `WSD_SDKToolkit_ZEMMACOS/Integrations.md`
- Generated SDK docs: `WSD_SDKToolkit_ZEMMACOS/docs/` (API, architecture, UI, security,
  troubleshooting)
- App documentation: this `doc/` directory.
