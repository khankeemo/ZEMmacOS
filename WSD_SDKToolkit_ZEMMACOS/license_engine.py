"""License validation and management engine"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .client import ApiClient, ApiError
from .hardware import HardwareDetector
from .cache import CacheManager

logger = logging.getLogger(__name__)


class LicenseStatus:
    def __init__(self, valid: bool, status: str, **kwargs):
        self.valid = valid
        self.status = status
        self.expiry_date = kwargs.get('expiry_date')
        self.days_left = kwargs.get('days_left', 0)
        self.plan = kwargs.get('plan')
        self.hardware_id = kwargs.get('hardware_id')
        self.message = kwargs.get('message')
        self.license_key = kwargs.get('license_key')
        self.trial_active = kwargs.get('trial_active', status == 'trial')
        self.customer_name = kwargs.get('customer_name')
        self.customer_email = kwargs.get('customer_email')
        self.customer_phone = kwargs.get('customer_phone')
        self.customer_mobile = kwargs.get('customer_mobile')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'status': self.status,
            'expiry_date': self.expiry_date,
            'days_left': self.days_left,
            'plan': self.plan,
            'hardware_id': self.hardware_id,
            'message': self.message,
            'license_key': self.license_key,
            'trial_active': self.trial_active,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_mobile': self.customer_mobile
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseStatus':
        return cls(
            valid=data.get('valid', False),
            status=data.get('status', 'unlicensed'),
            expiry_date=data.get('expiry_date'),
            days_left=data.get('days_left', 0),
            plan=data.get('plan'),
            hardware_id=data.get('hardware_id'),
            message=data.get('message'),
            license_key=data.get('license_key'),
            trial_active=data.get('trial_active', data.get('status') == 'trial'),
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email'),
            customer_phone=data.get('customer_phone'),
            customer_mobile=data.get('customer_mobile')
        )


class LicenseEngine:
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
            base_dir = Path(__file__).parent.parent
            config_path = str(base_dir / 'config' / 'api-config.json')
            if not Path(config_path).exists():
                config_path = str(Path.cwd() / 'config' / 'api-config.json')
        if not Path(config_path).exists():
            raise FileNotFoundError(
                f"api-config.json not found at: {config_path}"
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def initialize(self) -> LicenseStatus:
        if self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                self._status = LicenseStatus.from_dict(cached)
                return self._status
        try:
            hardware_id = self._hardware.get_fingerprint()
            # Check for existing trial first (works without license key)
            trial_response = self._client.get_trial_status(hardware_id)
            trial_data = trial_response.get('data', {})
            if trial_data.get('has_trial'):
                status_str = trial_data.get('status', 'trial')
                self._status = LicenseStatus(
                    valid=status_str == 'active',
                    status=status_str,
                    expiry_date=trial_data.get('expiry_date'),
                    days_left=trial_data.get('days_left', 0),
                    plan=trial_data.get('plan'),
                    hardware_id=hardware_id,
                    message=f"Trial is {status_str}",
                    customer_name=trial_data.get('customer_name'),
                    customer_email=trial_data.get('customer_email'),
                    customer_phone=trial_data.get('customer_phone'),
                    customer_mobile=trial_data.get('customer_mobile')
                )
                if self._status.valid:
                    self._cache.set_license_status(self._status.to_dict())
                return self._status
            # No trial - return unlicensed
            self._status = LicenseStatus(
                valid=False, status='unlicensed',
                hardware_id=hardware_id,
                message='No license or trial found'
            )
            return self._status
        except Exception as e:
            logger.exception("Unexpected error during license initialization")
            cached = self._cache.get_license_status()
            if cached:
                return LicenseStatus.from_dict(cached)
            self._status = LicenseStatus(
                valid=False, status='error',
                message=f"Unexpected error: {str(e)}"
            )
            return self._status

    def get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

    def get_status(self) -> Optional[LicenseStatus]:
        return self._status

    def get_license_key(self) -> Optional[str]:
        return self._license_key

    def has_license_key(self) -> bool:
        return self._license_key is not None

    def validate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.validate_license(key, hardware_id)
        data = result.get('data', result)
        if data.get('valid'):
            if data.get('license_key'):
                self._license_key = data['license_key']
            # Create LicenseStatus from validation response which has all customer fields
            self._status = LicenseStatus(
                valid=data.get('valid', True),
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=data.get('license_key'),
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def activate(self, license_key: str) -> Dict[str, Any]:
        result = self._client.activate_license(license_key)
        if result.get('success'):
            self._license_key = license_key
            data = result.get('data', result)
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=self._hardware.get_fingerprint(),
                license_key=license_key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = self._client.start_trial(email, customer_name=customer_name, customer_data=customer_data)
        if result.get('success'):
            data = result.get('data', result)
            self._status = LicenseStatus(
                valid=True,
                status='trial',
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', data.get('duration_days', 7)),
                plan=data.get('plan', 'Trial'),
                hardware_id=self._hardware.get_fingerprint(),
                customer_name=data.get('customer_name') or customer_name,
                customer_email=data.get('customer_email') or email,
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def convert_trial(self, plan: Optional[str] = None, customer_name: str = '', customer_email: str = '') -> Dict[str, Any]:
        status = self.initialize()
        if not status or status.status != 'trial':
            raise RuntimeError("No active trial to convert.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.convert_trial(hardware_id, plan, customer_name, customer_email)
        if result.get('success'):
            data = result.get('data', result)
            if 'license_key' in data:
                self._license_key = data.get('license_key')
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=data.get('license_key'),
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def get_plans(self) -> Dict[str, Any]:
        return self._client.get_products()

    def renew(self, extra_days: Optional[int] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable. Please activate first.")
        result = self._client.renew_license(self._license_key, extra_days)
        if result.get('success'):
            data = result.get('data', result)
            hardware_id = self._hardware.get_fingerprint()
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('new_expiry_date') or data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=self._license_key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def deactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please provide a key.")
        result = self._client.deactivate_license(key)
        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            if license_key is None:
                self._license_key = None
        return result

    def replace_hardware(self, device_name: Optional[str] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable. Please activate first.")
        new_hardware_id = self._hardware.get_fingerprint()
        old_hardware_id = None
        if self._status and self._status.hardware_id:
            old_hardware_id = self._status.hardware_id
        if not old_hardware_id:
            cached = self._cache.get_license_status()
            if cached and cached.get('hardware_id'):
                old_hardware_id = cached.get('hardware_id')
        if not old_hardware_id:
            raise RuntimeError("Current hardware_id unavailable. Cannot replace device.")
        if old_hardware_id == new_hardware_id:
            return {'success': False, 'message': 'Old and new hardware IDs are identical.'}
        result = self._client.replace_device(
            license_key=self._license_key,
            new_hardware_id=new_hardware_id,
            old_hardware_id=old_hardware_id,
            device_name=device_name
        )
        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            self.initialize()
        return result

    def bind_device(self, license_key: Optional[str] = None, device_name: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable.")
        result = self._client.bind_device(key, device_name=device_name)
        if result.get('success'):
            self.initialize()
        return result
