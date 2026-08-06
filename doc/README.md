# ZEMmacOS — Documentation

This directory is the single source of truth for the **ZEMmacOS** application and its
integration with the **WSD Universal SDK** (`WSD_SDKToolkit_ZEMMACOS`).

## Reading order

New contributors and automated tools (including Opencode) should read these documents
**in order** before touching the project:

| # | Document | Purpose |
|---|----------|---------|
| 1 | [01_PROJECT_OVERVIEW.md](01_PROJECT_OVERVIEW.md) | What ZEMmacOS is, why it exists. |
| 2 | [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | Application architecture and layers. |
| 3 | [03_PROJECT_STRUCTURE.md](03_PROJECT_STRUCTURE.md) | Directory / file layout. |
| 4 | [04_MODULE_OVERVIEW.md](04_MODULE_OVERVIEW.md) | Responsibilities of each module. |
| 5 | [05_SDK_INTEGRATION.md](05_SDK_INTEGRATION.md) | Integration architecture, lifecycle, startup/shutdown. |
| 6 | [06_IMPORT_STRUCTURE.md](06_IMPORT_STRUCTURE.md) | Package structure, dependencies, initialization order. |
| 7 | [07_INTEGRATION_FLOW.md](07_INTEGRATION_FLOW.md) | The complete runtime flow. |
| 8 | [08_EVENT_SYSTEM.md](08_EVENT_SYSTEM.md) | Every event: source, subscriber, expected behavior. |
| 9 | [09_API.md](09_API.md) | SDK public APIs, integration methods, callbacks. |
| 10 | [10_CONFIGURATION.md](10_CONFIGURATION.md) | Config files, environment, SDK settings, logging. |
| 11 | [11_DATABASE.md](11_DATABASE.md) | Database usage and ownership (app / SDK cache / backend). |
| 12 | [12_UI_UX.md](12_UI_UX.md) | Dialog flow, screens, user workflows. |
| 13 | [13_TROUBLESHOOTING.md](13_TROUBLESHOOTING.md) | Diagnostic guide keyed off the logs. |
| 14 | [14_FUTURE_DEVELOPMENT.md](14_FUTURE_DEVELOPMENT.md) | Rules for all future work. |

## Project separation (mandatory)

ZEMmacOS and the Websmith Universal license platform are **two separate projects** that
must stay separated:

- **Websmith Universal** — license server, license engine source, SDK generator, runtime
  templates, publisher, Internal API, and License Control Center. It is the **single
  source of truth** for all license management and control.
- **ZEMmacOS** — an end-user application and **SDK consumer** only. It initializes the
  SDK, calls SDK public APIs, displays SDK UI, consumes SDK state, reacts to SDK events,
  and continues its own business workflow. It **never** implements or copies licensing
  functionality.

The generated SDK (`WSD_SDKToolkit_ZEMMACOS`) is **read-only output**. Never edit it. If
the SDK has a defect, fix the root cause in the Websmith source (templates / Publisher /
Internal API), regenerate a fresh SDK, and replace the SDK in ZEMmacOS.

Logs are the primary diagnostic source. When an issue is reported, review the logs in
`logs/` and the SDK live log before changing code. See
[13_TROUBLESHOOTING.md](13_TROUBLESHOOTING.md).