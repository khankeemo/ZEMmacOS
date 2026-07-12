# SDKToolkit Migration Audit — ZEMmacOS

## 1. Old SDK Imports (7 occurrences across 2 files)

### `main.py` (4 occurrences)

| Line | Import | New SDK Equivalent |
|------|--------|-------------------|
| 21 | `from SDK_ZEM_MAC_OS_prod_zemmacos.client import Client` | `from SDKToolkit_prod_zemmacos.client import ApiClient` |
| 22 | `from SDK_ZEM_MAC_OS_prod_zemmacos.license_engine import LicenseEngine` | `from SDKToolkit_prod_zemmacos import LicenseEngine` (same class) |
| 23 | `from SDK_ZEM_MAC_OS_prod_zemmacos.welcome import WelcomeDialog` | `from SDKToolkit_prod_zemmacos import WelcomeDialog` (same class) |
| 28 | `SDK_ZEM_MAC_OS_prod_zemmacos/config/api-config.json` path | `SDKToolkit_prod_zemmacos/config/api-config.json` path |

### `settings_ui.py` (3 occurrences)

| Line | Import | New SDK Equivalent |
|------|--------|-------------------|
| 278 | `SDK_ZEM_MAC_OS_prod_zemmacos/config/api-config.json` path | `SDKToolkit_prod_zemmacos/config/api-config.json` path |
| 282 | `from SDK_ZEM_MAC_OS_prod_zemmacos.client import Client` | `from SDKToolkit_prod_zemmacos.client import ApiClient` |
| 283 | `from SDK_ZEM_MAC_OS_prod_zemmacos.welcome import WelcomeDialog` | `from SDKToolkit_prod_zemmacos import WelcomeDialog` |

## 2. API Surface Changes

### Old SDK → New SDK Key Differences

| Aspect | Old SDK | New SDK |
|--------|---------|---------|
| Client class | `Client(api_key, api_url)` | `ApiClient(config, hardware, cache)` — no direct construction |
| Constructor pattern | Manual `Client + LicenseEngine(client)` | Auto: `LicenseEngine(config_path)` creates ApiClient internally |
| validate_license | `client.validate_license(key, device_id)` | `engine.initialize()` handles internally, or `client.validate_license(hardware_id)` |
| activate_license | `client.activate_license(key, device_id, device_name)` | `engine.activate(key, device_name)` |
| deactivate | `client.deactivate_license(key, device_id)` | `engine.deactivate(key)` |
| Hardware | `HardwareFingerprint.generate_fingerprint()` → dict | `HardwareDetector.get_fingerprint()` → string |
| WelcomeDialog | `WelcomeDialog(client, product_name, cache)` | `WelcomeDialog(engine, support_email)` |
| OTP | `client.send_otp(email)` / `client.verify_otp(email, otp)` | `engine.send_otp(email, purpose)` / `engine.verify_otp(email, otp_code)` |
| Store customer | `client.store_customer(name, email, mobile, ...)` | `engine.store_customer(customer_data_dict)` |
| Trial | `client.start_trial(email, name, data)` | `engine.start_trial(email, name, company, ...)` |
| Status | `LicenseStatus` has `valid, status, expires_at, days_remaining, plan, hardware_id, message` | Same fields + `plan_id, device_name, trial_active, license_active, product, product_version, max_devices, device_count, license_key` |
| is_valid() | `engine.is_valid()` | `status.valid` directly |
| get_hardware_fingerprint | Returns dict: `{fingerprint, mac_addresses, cpu, os, platform}` | Use `engine.get_hardware_id()` → returns string only |

### Imports in `__init__.py`

| Old SDK `__all__` | New SDK `__all__` (additions in bold) |
|-------------------|--------------------------------------|
| `Client, LicenseEngine, LicenseStatus, HardwareFingerprint, CacheManager, WelcomeDialog` | `LicenseEngine, LicenseStatus, ApiClient, ApiError, HardwareDetector, CacheManager, WelcomeDialog, **ActivationDialog, RenewalDialog, DeviceReplaceDialog, DashboardWidget, SettingsWidget, StatusWidget, ActivationButton**` |

## 3. Startup Sequence (`_init_sdk` in main.py)

**Current (old SDK):**
```python
def _init_sdk():
    sdk_config_path = os.path.join(BASE_DIR, 'SDK_ZEM_MAC_OS_prod_zemmacos', 'config', 'api-config.json')
    with open(sdk_config_path) as f:
        sdk_config = json.load(f)
    client = Client(api_key=sdk_config['api']['public_key'], api_url=sdk_config['api']['url'])
    engine = LicenseEngine(client)
    engine.initialize()
    welcome = WelcomeDialog(client)
    if not welcome.is_onboarding_complete():
        result = welcome.show()
        if not result.get('onboarding_complete'):
            sys.exit(1)
        engine.initialize()
    return engine
```

**Required (new SDK):**
```python
def _init_sdk():
    sdk_config_path = os.path.join(BASE_DIR, 'SDKToolkit_prod_zemmacos', 'config', 'api-config.json')
    engine = LicenseEngine(config_path=sdk_config_path)  # Auto-loads config, creates ApiClient + CacheManager internally
    engine.initialize()
    welcome = WelcomeDialog(engine)  # Now takes engine, not client
    if not welcome.is_onboarding_complete():
        result = welcome.show()
        if not result:  # Returns bool now (True=onboarding complete), not dict
            sys.exit(1)
        engine.initialize()
    return engine
```

**Key behavioral differences in WelcomeDialog:**
- Old: `is_onboarding_complete()` checks cache, `show()` returns `Dict` with `onboarding_complete` key
- New: `is_onboarding_complete()` — same concept via cache. `show()` returns `bool` (True = trial started / onboarding done)
- New WelcomeDialog also supports `support_email` parameter (optional)

## 4. Dashboard License Status Card (`main_ui.py:518-552`)

- Already uses `self.engine.get_status()` and `status.to_dict()` — compatible with new SDK's LicenseStatus
- Displayed keys: `status`, `plan`, `days_remaining`, `expires_at`, `hardware_id` — all exist in new SDK
- **No change needed** for the existing dashboard card

### DashboardWidget (new SDK addition)
- `DashboardWidget(parent, engine)` — can be placed beside the theme toggle in `right_h` frame (line 482-489)
- Shows: Status, Remaining days, Expiry, Plan — with a Refresh button
- Implementation: `widget = DashboardWidget(right_h, engine); widget.build()`

## 5. Settings License Section (`settings_ui.py:244-315`)

### Current behavior:
- `_build_license()` at line 244: displays license status fields + hardware fingerprint details
- Line 266: calls `engine.get_hardware_fingerprint()` — **old SDK only**, returns dict
- Line 277-287: `_open_welcome()` — manually loads config, creates Client, creates WelcomeDialog from old SDK
- Line 289-302: `_refresh()` and `_recheck()` — calls `engine.initialize()` which is compatible

### Required changes:
- Line 266: `engine.get_hardware_fingerprint()` → `engine.get_hardware_id()` (returns string, not dict)
- Lines 277-287: `_open_welcome()` — change to use new SDK pattern:
  ```python
  from SDKToolkit_prod_zemmacos import WelcomeDialog
  WelcomeDialog(engine).show()
  engine.initialize()
  ```
- Lines 289-293: `_refresh()` — compatible, no change needed
- Lines 295-303: `_recheck()` — compatible, no change needed

### SettingsWidget (new SDK addition)
- `SettingsWidget(parent, engine)` — a Notebook-based tab with License info + Activate/Renew/Replace/Refresh/Welcome buttons
- Can replace or supplement the existing license section
- Implementation in `_build_license` or as an additional UI element

## 6. New UI Components Available

### DashboardWidget
- File: `SDKToolkit_prod_zemmacos\widgets\dashboard_widget.py`
- Placement: beside theme toggle in `right_h` frame (main_ui.py:482-489)
- Shows: status, days remaining, expiry, plan, refresh button
- Status colors: green (licensed), red (unlicensed)
- Handles trial vs licensed display

### SettingsWidget
- File: `SDKToolkit_prod_zemmacos\widgets\settings_widget.py`
- Placement: within settings view, either replacing `_build_license` or in addition to it
- Has a ttk.Notebook with License tab
- Shows: status, product, expiry, plan, hardware ID, runtime, SDK version
- Buttons: Activate, Renew, Replace Device, Refresh, Open Welcome
- Each button opens the corresponding SDK dialog

### StatusWidget
- File: `SDKToolkit_prod_zemmacos\widgets\status_widget.py`
- A compact status bar showing colored dot + "Licensed: Xd" / "Trial: Xd" / "No license"
- Could be placed in sidebar footer or header area

### ActivationButton
- File: `SDKToolkit_prod_zemmacos\widgets\activation_button.py`
- Simple "Activate License" button that opens ActivationDialog
- After activation, changes to "Licensed" with green background

**Allowed additions per rules:**
- ✅ DashboardWidget (top-right, beside theme toggle)
- ✅ SettingsWidget (Settings → License section)
- ❌ Custom activation UI, OTP UI, renewal UI, hardware UI, cache, validation logic, localhost/HTML pages, wrappers — SDK must own all licensing

## 7. Complete Migration Checklist

### Phase 1 — Audit (this document) ✅
### Phase 2 — SDK Swap (main.py)
- [ ] Change import: `Client` → `ApiClient` (or just import `LicenseEngine` and let it create internally)
- [ ] Change `_init_sdk()` to construct `LicenseEngine(config_path=...)` instead of manual Client + LicenseEngine
- [ ] Change `WelcomeDialog(client)` → `WelcomeDialog(engine)`
- [ ] Change `result.get('onboarding_complete')` → `result` (bool check)
- [ ] Update SDK path from `SDK_ZEM_MAC_OS_prod_zemmacos` to `SDKToolkit_prod_zemmacos`

### Phase 3 — Settings Update (settings_ui.py)
- [ ] Change import: old `Client` + `WelcomeDialog` → new SDK imports
- [ ] Replace `engine.get_hardware_fingerprint()` → `engine.get_hardware_id()` (string vs dict)
- [ ] Update `_open_welcome()` to use `WelcomeDialog(engine)` pattern
- [ ] Add `SettingsWidget` to license section

### Phase 4 — Dashboard Widget (main_ui.py)
- [ ] Add `DashboardWidget` beside theme toggle in `right_h` frame

### Phase 5 — Shutdown old SDK
### Phase 6 — Validation and testing

## 8. Shutdown behavior

- Current: no license-specific cleanup on shutdown (main.py:915 `on_closing`)
- New SDK's engine has `clear_cache()` if needed — not required for basic migration
- No special shutdown needed for LicenseEngine
