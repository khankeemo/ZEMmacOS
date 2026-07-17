# License UI Components

## Welcome Dialog

**File:** `welcome.py`

Handles trial onboarding on first launch.

**Fields:** Name, Email, Mobile, Country, Company

**Buttons:** Send OTP, Verify OTP

**Flow:**
1. Collect customer information
2. Send OTP to email
3. Verify OTP code
4. Register customer
5. Start trial automatically
6. Bind hardware automatically

**Security:** Closing the Welcome dialog closes the entire application.

## Activation Dialog

**File:** `activation.py`

Handles license key activation for purchased licenses.

**Displays:**
- Product name and version
- Hardware ID and device name
- License key text field
- Plan name, expiry date, remaining days, device count

**Buttons:** Activate, Renew, Replace Device

**Flow:**
1. Generate hardware fingerprint automatically
2. Enable license textbox (disabled until hardware is ready)
3. Enter license key
4. Fetch license details automatically
5. Click Activate
6. Hardware binds automatically
7. Cache refreshes

## Renewal Dialog

**File:** `renewal.py`

Handles license renewal.

**Displays:**
- Current plan and expiry
- Available plans from API

**API:**
- `GET /api/v1/plans`
- `POST /api/v1/license/renew`

## Device Replacement Dialog

**File:** `device_replace.py`

Handles transferring a license to another machine.

**Displays:**
- Old hardware ID
- New hardware ID (auto-generated)
- Device name field

**API:** `POST /api/v1/license/replace-device`

## Widgets

### LicenseWidget
- **File:** `widgets/dashboard_widget.py`
- **Placement:** Dashboard top-right corner
- **Contents:** License status, remaining days, expiry, hardware status
- **Auto-refresh:** Every 60 seconds

### SettingsWidget
- **File:** `widgets/settings_widget.py`
- **Placement:** Settings > License
- **Contents:** Full license details panel with action buttons

### StatusWidget
- **File:** `widgets/status_widget.py`
- **Placement:** Status bar
- **Contents:** Compact status indicator with colored icon

### ActivationButton
- **File:** `widgets/activation_button.py`
- **Placement:** Any toolbar
- **Contents:** One-click activation button

## Recommended UI Structure

```
Settings
  └── License
       ├── Status
       ├── Product
       ├── SDK Version
       ├── Runtime
       ├── Hardware ID
       ├── Expiry
       ├── Remaining Days
       ├── [Activate]
       ├── [Renew]
       ├── [Replace Device]
       ├── [Refresh]
       └── [Open Welcome]
```
