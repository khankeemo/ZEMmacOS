"""License validation engine for ZEM MAC OS"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .client import ApiClient, ApiError
from .hardware import HardwareDetector
from .cache import CacheManager


class LicenseStatus:
    """License status object returned by the engine."""

    def __init__(self, valid: bool, status: str, **kwargs):
        self.valid = valid
        self.status = status
        self.expires_at = kwargs.get('expires_at')
        self.days_remaining = kwargs.get('days_remaining', 0)
        self.plan = kwargs.get('plan')
        self.hardware_id = kwargs.get('hardware_id')
        self.message = kwargs.get('message')
        self.trial_active = kwargs.get('trial_active', False)
        self.license_active = kwargs.get('license_active', False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'status': self.status,
            'expires_at': self.expires_at,
            'days_remaining': self.days_remaining,
            'plan': self.plan,
            'hardware_id': self.hardware_id,
            'message': self.message,
            'trial_active': self.trial_active,
            'license_active': self.license_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseStatus':
        return cls(
            valid=data.get('valid', False),
            status=data.get('status', 'unlicensed'),
            expires_at=data.get('expires_at'),
            days_remaining=data.get('days_remaining', 0),
            plan=data.get('plan'),
            hardware_id=data.get('hardware_id'),
            message=data.get('message'),
            trial_active=data.get('trial_active', False),
            license_active=data.get('license_active', False)
        )


class LicenseEngine:
    """
    Universal License Engine.
    Main entry point for partner applications. Handles license validation,
    activation, trial management, renewal, conversion, and hardware replacement.

    LICENSE KEY POLICY:
    - License key is stored in memory ONLY (self._license_key)
    - NOT persisted to disk (for security)
    - After application restart, user must re-enter key for renewal/replacement
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._hardware = HardwareDetector()
        self._cache = CacheManager(self.config)
        self._client = ApiClient(
            config=self.config,
            hardware=self._hardware,
            cache=self._cache
        )
        self._status: Optional[LicenseStatus] = None
        self._license_key: Optional[str] = None

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if config_path is None:
            base_dir = Path(__file__).parent
            config_path = base_dir / 'config' / 'api-config.json'
        else:
            config_path = Path(config_path)
        if not config_path.exists():
            config_path = Path.cwd() / 'config' / 'api-config.json'
        if not config_path.exists():
            raise FileNotFoundError(
                f"api-config.json not found at: {config_path}\n"
                "Please ensure the configuration file is present."
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def initialize(self) -> LicenseStatus:
        """
        Initialize the license engine - called once on app startup.

        Flow:
        1. Check cache for valid status (offline support)
        2. Check trial status with API
        3. If license key available, validate with API
        4. Cache result

        Returns:
            LicenseStatus object
        """
        # 1. Check cache first (offline support)
        if self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                self._status = LicenseStatus.from_dict(cached)
                return self._status

        try:
            hardware_id = self._hardware.get_fingerprint()

            # 2. Check trial status
            trial_response = self._client.get_trial_status(hardware_id)
            trial_active = False
            trial_days_left = 0
            trial_expiry = None

            if trial_response.get('success'):
                trial_data = trial_response.get('data', {})
                if trial_data.get('has_trial') and trial_data.get('status') == 'active':
                    trial_active = True
                    trial_days_left = trial_data.get('days_left', 0)
                    trial_expiry = trial_data.get('expiry_date')

            # 3. Try license validation if key is available
            license_valid = False
            license_status = 'unlicensed'
            license_expiry = None
            license_plan = None
            license_days_left = 0

            if self._license_key:
                try:
                    lic_response = self._client.validate_license(hardware_id)
                    if lic_response.get('success'):
                        lic_data = lic_response.get('data', {})
                        license_valid = lic_data.get('valid', False)
                        license_status = lic_data.get('status', 'unlicensed')
                        license_expiry = lic_data.get('expiry_date')
                        license_plan = lic_data.get('plan')
                        license_days_left = lic_data.get('days_left', 0)
                except ApiError:
                    pass

            # 4. Determine overall validity
            is_valid = trial_active or license_valid
            if is_valid:
                status_str = 'trial' if trial_active else license_status
                days_remaining = trial_days_left if trial_active else license_days_left
                expires_at = trial_expiry if trial_active else license_expiry
                plan = license_plan
            else:
                status_str = 'unlicensed'
                days_remaining = 0
                expires_at = None
                plan = None

            self._status = LicenseStatus(
                valid=is_valid,
                status=status_str,
                expires_at=expires_at,
                days_remaining=days_remaining,
                plan=plan,
                hardware_id=hardware_id,
                message=self._build_message(is_valid, trial_active, license_valid, days_remaining),
                trial_active=trial_active,
                license_active=license_valid
            )

            if is_valid:
                self._cache.set_license_status(self._status.to_dict())

            return self._status

        except ApiError as e:
            cached = self._cache.get_license_status()
            if cached:
                return LicenseStatus.from_dict(cached)

            self._status = LicenseStatus(
                valid=False,
                status='error',
                message=f"License validation failed: {e.message}"
            )
            return self._status

        except Exception as e:
            cached = self._cache.get_license_status()
            if cached:
                return LicenseStatus.from_dict(cached)

            self._status = LicenseStatus(
                valid=False,
                status='error',
                message=f"Unexpected error: {str(e)}"
            )
            return self._status

    def _build_message(self, is_valid: bool, trial_active: bool, license_valid: bool, days_remaining: int) -> str:
        if not is_valid:
            return "No active license or trial found. Please activate or start a trial."
        if trial_active:
            return f"Trial active — {days_remaining} day(s) remaining."
        if license_valid:
            return f"License active — {days_remaining} day(s) remaining."
        return ""

    def get_status(self) -> Optional[LicenseStatus]:
        """Get current license status (without re-validating)."""
        return self._status

    def get_license_key(self) -> Optional[str]:
        return self._license_key

    def has_license_key(self) -> bool:
        return self._license_key is not None

    def activate(self, license_key: str) -> Dict[str, Any]:
        """Activate a license with the provided key."""
        result = self._client.activate_license(license_key)
        if result.get('success'):
            self._license_key = license_key
            self.initialize()
        return result

    def start_trial(self, email: str, company: Optional[str] = None) -> Dict[str, Any]:
        """Start a free trial."""
        result = self._client.start_trial(email, customer_name=company)
        if result.get('success'):
            self.initialize()
        return result

    def convert_trial(self, plan: Optional[str] = None) -> Dict[str, Any]:
        """Convert an active trial into a licensed installation."""
        status = self.initialize()

        if not status or status.status != 'trial':
            raise RuntimeError(
                "No active trial to convert. "
                "Please start a trial first."
            )

        hardware_id = self._hardware.get_fingerprint()
        result = self._client.convert_trial(hardware_id, plan)

        if result.get('success'):
            if 'license_key' in result:
                self._license_key = result.get('license_key')
            self.initialize()

        return result

    def renew(self, extra_days: Optional[int] = None) -> Dict[str, Any]:
        """Renew the current license."""
        if not self._license_key:
            raise ValueError(
                "License key unavailable in this session. "
                "Please activate your license again."
            )

        result = self._client.renew_license(self._license_key, extra_days)
        if result.get('success'):
            self.initialize()
        return result

    def deactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        """Deactivate a license on the current hardware device."""
        key = license_key or self._license_key
        if not key:
            raise ValueError(
                "License key unavailable. "
                "Please provide a license key or activate first."
            )

        result = self._client.deactivate_license(key)
        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            if license_key is None:
                self._license_key = None
        return result

    def replace_hardware(self) -> Dict[str, Any]:
        """Replace hardware for the current license."""
        if not self._license_key:
            raise ValueError(
                "License key unavailable in this session. "
                "Please activate your license again."
            )

        new_hardware_id = self._hardware.get_fingerprint()

        old_hardware_id = None
        if self._status and self._status.hardware_id:
            old_hardware_id = self._status.hardware_id

        if not old_hardware_id:
            cached = self._cache.get_license_status()
            if cached and cached.get('hardware_id'):
                old_hardware_id = cached.get('hardware_id')

        if not old_hardware_id:
            raise RuntimeError(
                "Current hardware_id unavailable. Cannot replace device. "
                "Please ensure the license has been validated at least once."
            )

        if old_hardware_id == new_hardware_id:
            return {
                'success': False,
                'message': 'Old and new hardware IDs are identical. No replacement needed.'
            }

        result = self._client.replace_device(
            license_key=self._license_key,
            new_hardware_id=new_hardware_id,
            old_hardware_id=old_hardware_id
        )

        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            self.initialize()

        return result

    def bind_device(self, license_key: Optional[str] = None, device_name: Optional[str] = None) -> Dict[str, Any]:
        """Bind a hardware device to a license."""
        key = license_key or self._license_key
        if not key:
            raise ValueError(
                "License key unavailable. "
                "Please provide a license key or activate first."
            )

        result = self._client.bind_device(key, device_name=device_name)
        if result.get('success'):
            self.initialize()
        return result
