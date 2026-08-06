# 14. Future Development Rules

## 14.1 Mandatory workflow

All future work on ZEMmacOS and its licensing integration **must** follow this order:

1. **Read the documentation** in `D:\ZEMmacOS\doc`.
2. **Review the latest logs** (`logs/`) — app file log + live log; grep the canonical SDK
   events before changing anything.
3. **Identify the root cause**.
4. **Fix the root cause in the correct project** (see 14.3).
5. **Never guess.** Every change must be traceable to logs or documented behavior.
6. **Never duplicate logic.** If the SDK (or Websmith) already owns a behavior, use it.
7. **Update the documentation** if behavior changes.

## 14.2 Project separation (mandatory)

| Project | May do | Must never do |
|---|---|---|
| **Websmith Universal** | License server; engine source; SDK generator; runtime templates; Publisher; Internal API; License Control Center | — |
| **ZEMmacOS** | Initialize SDK; call SDK public APIs; display SDK UI; consume SDK state; react to SDK events; continue its own application workflow | Implement or copy licensing functionality; bypass the SDK to the backend; edit the generated SDK |

Websmith remains the **single source of truth** for license management and control.
All licensing behavior must come from the SDK.

## 14.3 Where to fix what

| Symptom / change | Fix here |
|---|---|
| SDK behavior, UI, API, database logic, license/trial/renewal/activation/hardware logic, internal SDK workflow | **Websmith Universal** source (templates, runtime generators, Publisher, Internal API) — then **regenerate a fresh SDK** and replace it in ZEMmacOS |
| Application UI, catalogue, downloads, settings, theming, logs, build scripts | **ZEMmacOS** |
| License *record* is wrong (customer, plan, expiry, activation count) | **Websmith License Control Center** (no code change) |
| `api-config.json` values | Websmith Publisher injection — never hardcode in ZEMmacOS |

## 14.4 SDK immutability

- `WSD_SDKToolkit_ZEMMACOS/` is **read-only**.
- Never modify its UI, UX, API, database logic, license logic, trial/renewal/activation
  logic, hardware logic, or internal workflow.
- If an issue is discovered: **do not** fix it inside the generated SDK. Fix it in the
  Websmith Universal source, regenerate a fresh SDK, then replace the SDK in ZEMmacOS.

## 14.5 Integration rules

- Initialize the decision engine **once** at startup; let the ULC consume the result.
- Treat the backend as the single source of truth; never derive validity locally.
- Keep `api-config.json` injected and version-synchronized (SDK / product / runtime /
  generated versions must match).
- All app UI reads the same `LicenseStatus` instance; on state change, the engine emits
  one `LicenseStatusChanged` event and every screen re-renders from the payload.
- Keep the offline cache and message-queue behavior SDK-owned.

## 14.6 Documentation rules

- Keep `doc/` in sync with the code. If a behavior changes, update the corresponding
  document in the same change.
- When diagnosing, refer to [13_TROUBLESHOOTING.md](13_TROUBLESHOOTING.md) and quote the
  log evidence in any report.
- Do not regenerate or hand-write SDK docs inside `WSD_SDKToolkit_ZEMMACOS/docs/` — those
  are generated output and stay in sync with the Websmith templates.

## 14.7 Definition of done

A change is done only when:

- Root cause confirmed via logs, not guessed.
- Fixed in the correct project (ZEMmacOS business code, or Websmith source + SDK
  regeneration).
- No logic duplicated.
- `doc/` updated if behavior changed.
- Application still compiles (`python -m py_compile main.py py/*.py`) and SDK imports
  cleanly.
