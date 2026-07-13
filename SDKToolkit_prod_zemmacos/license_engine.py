"""License validation engine for ZEM MAC OS"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .client import ApiClient, ApiError
from .hardware import HardwareDetector
from .cache import CacheManager

logger = logging.getLogger(__name__)


class LicenseStatus:
    def __init__(self, valid: bool, status: str, **kwargs):
        self.valid = valid
        self.status = status
        self.expires_at = kwargs.get('expires_at')
        self.days_remaining = kwargs.get('days_remaining', 0)
        self.plan = kwargs.get('plan')
        self.plan_id = kwargs.get('plan_id')
        self.hardware_id = kwargs.get('hardware_id')
        self.device_name = kwargs.get('device_name')
        self.message = kwargs.get('message')
        self.trial_active = kwargs.get('trial_active', False)
        self.license_active = kwargs.get('license_active', False)
        self.product = kwargs.get('product')
        self.product_version = kwargs.get('product_version')
        self.max_devices = kwargs.get('max_devices', 0)
        self.device_count = kwargs.get('device_count', 0)
        self.license_key = kwargs.get('license_key')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'status': self.status,
            'expires_at': self.expires_at,
            'days_remaining': self.days_remaining,
            'plan': self.plan,
            'plan_id': self.plan_id,
            'hardware_id': self.hardware_id,
            'device_name': self.device_name,
            'message': self.message,
            'trial_active': self.trial_active,
            'license_active': self.license_active,
            'product': self.product,
            'product_version': self.product_version,
            'max_devices': self.max_devices,
            'device_count': self.device_count,
            'license_key': self.license_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseStatus':
        return cls(
            valid=data.get('valid', False),
            status=data.get('status', 'unlicensed'),
            expires_at=data.get('expires_at'),
            days_remaining=data.get('days_remaining', 0),
            plan=data.get('plan'),
            plan_id=data.get('plan_id'),
            hardware_id=data.get('hardware_id'),
            device_name=data.get('device_name'),
            message=data.get('message'),
            trial_active=data.get('trial_active', False),
            license_active=data.get('license_active', False),
            product=data.get('product'),
            product_version=data.get('product_version'),
            max_devices=data.get('max_devices', 0),
            device_count=data.get('device_count', 0),
            license_key=data.get('license_key'),
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
            config_path = base_dir / 'config' / 'api-config.json'
            if not config_path.exists():
                config_path = Path.cwd() / 'config' / 'api-config.json'
        else:
            config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"api-config.json not found at: {config_path}\n"
                "Please ensure the configuration file is present."
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # =========================================================================
    # Initialization / Status
    # =========================================================================

    def initialize(self) -> LicenseStatus:
        if self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                self._status = LicenseStatus.from_dict(cached)
                return self._status

        try:
            hardware_id = self._hardware.get_fingerprint()

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

            license_valid = False
            license_status = 'unlicensed'
            license_expiry = None
            license_plan = None
            license_plan_id = None
            license_days_left = 0
            license_max_devices = 0
            license_device_count = 0
            license_product = None
            license_version = None
            license_key = None

            if self._license_key:
                try:
                    lic_response = self._client.validate_license(hardware_id)
                    if lic_response.get('success'):
                        lic_data = lic_response.get('data', {})
                        license_valid = lic_data.get('valid', False)
                        license_status = lic_data.get('status', 'unlicensed')
                        license_expiry = lic_data.get('expiry_date')
                        license_plan = lic_data.get('plan')
                        license_plan_id = lic_data.get('plan_id')
                        license_days_left = lic_data.get('days_left', 0)
                        license_max_devices = lic_data.get('max_devices', 0)
                        license_device_count = lic_data.get('device_count', 0)
                        license_product = lic_data.get('product')
                        license_version = lic_data.get('product_version')
                        license_key = self._license_key
                except ApiError as e:
                    logger.error("License validation failed: %s", e.message)

            is_valid = trial_active or license_valid
            if is_valid:
                status_str = 'trial' if trial_active else license_status
                days_remaining = trial_days_left if trial_active else license_days_left
                expires_at = trial_expiry if trial_active else license_expiry
                plan = license_plan
                plan_id = license_plan_id
                max_devices = license_max_devices
                device_count = license_device_count
                product = license_product
                product_version = license_version
            else:
                status_str = 'unlicensed'
                days_remaining = 0
                expires_at = None
                plan = None
                plan_id = None
                max_devices = 0
                device_count = 0
                product = None
                product_version = None

            msg = ""
            if trial_active:
                msg = f"Trial active — {trial_days_left} day(s) remaining."
            elif license_valid:
                msg = f"License active — {license_days_left} day(s) remaining."
            else:
                msg = "No active license or trial found. Please activate or start a trial."

            self._status = LicenseStatus(
                valid=is_valid,
                status=status_str,
                expires_at=expires_at,
                days_remaining=days_remaining,
                plan=plan,
                plan_id=plan_id,
                hardware_id=hardware_id,
                message=msg,
                trial_active=trial_active,
                license_active=license_valid,
                max_devices=max_devices,
                device_count=device_count,
                product=product,
                product_version=product_version,
                license_key=license_key,
            )

            if is_valid:
                self._cache.set_license_status(self._status.to_dict())

            return self._status

        except ApiError as e:
            logger.error("License API error during initialize: %s", e.message)
            cached = self._cache.get_license_status()
            if cached:
                return LicenseStatus.from_dict(cached)
            self._status = LicenseStatus(valid=False, status='error', message=f"License validation failed: {e.message}")
            return self._status

        except Exception as e:
            logger.exception("Unexpected error during license initialization")
            cached = self._cache.get_license_status()
            if cached:
                return LicenseStatus.from_dict(cached)
            self._status = LicenseStatus(valid=False, status='error', message=f"Unexpected error: {str(e)}")
            return self._status

    def get_status(self) -> Optional[LicenseStatus]:
        return self._status

    def get_license_key(self) -> Optional[str]:
        return self._license_key

    def has_license_key(self) -> bool:
        return self._license_key is not None

    def get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

    # =========================================================================
    # Activation
    # =========================================================================

    def activate(self, license_key: str, device_name: Optional[str] = None) -> Dict[str, Any]:
        result = self._client.activate_license(license_key, device_name=device_name)
        if result.get('success'):
            self._license_key = license_key
            if self._status:
                self._status.license_key = license_key
            self.initialize()
        return result

    # =========================================================================
    # OTP
    # =========================================================================

    def send_otp(self, email: str, purpose: str = 'registration') -> Dict[str, Any]:
        return self._client.send_otp(email, purpose)

    def verify_otp(self, email: str, otp_code: str) -> Dict[str, Any]:
        return self._client.verify_otp(email, otp_code)

    # =========================================================================
    # Customer Registration
    # =========================================================================

    def store_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._client.store_customer(customer_data)

    # =========================================================================
    # Trial Management
    # =========================================================================

    def start_trial(self, email: str, name: Optional[str] = None,
                    company: Optional[str] = None,
                    mobile: Optional[str] = None,
                    country: Optional[str] = None) -> Dict[str, Any]:
        customer_data = {}
        if company:
            customer_data['company'] = company
        if mobile:
            customer_data['mobile'] = mobile
        if country:
            customer_data['country'] = country
        result = self._client.start_trial(email, customer_name=name or '',
                                           customer_data=customer_data if customer_data else None)
        if result.get('success'):
            self.initialize()
        return result

    def check_trial(self) -> Dict[str, Any]:
        hardware_id = self._hardware.get_fingerprint()
        return self._client.check_trial(hardware_id)

    def convert_trial(self, plan: Optional[str] = None,
                      license_key: Optional[str] = None) -> Dict[str, Any]:
        status = self.initialize()
        if not status or status.status != 'trial':
            raise RuntimeError("No active trial to convert. Please start a trial first.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.convert_trial(hardware_id, plan, license_key)
        if result.get('success'):
            if 'license_key' in result:
                self._license_key = result.get('license_key')
            self.initialize()
        return result

    # =========================================================================
    # License Details
    # =========================================================================

    def get_license_details(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        return self._client.get_license_details(key)

    def get_license_history(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        return self._client.get_license_history(key)

    # =========================================================================
    # Renewal
    # =========================================================================

    def renew(self, plan_id: Optional[str] = None,
              extra_days: Optional[int] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable in this session. Please activate your license again.")
        result = self._client.renew_license(self._license_key, plan_id, extra_days)
        if result.get('success'):
            self.initialize()
        return result

    # =========================================================================
    # Deactivation
    # =========================================================================

    def deactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please provide a license key or activate first.")
        result = self._client.deactivate_license(key)
        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            if license_key is None:
                self._license_key = None
        return result

    # =========================================================================
    # Device Replacement
    # =========================================================================

    def replace_hardware(self, device_name: Optional[str] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable in this session. Please activate your license again.")
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
            return {
                'success': False,
                'message': 'Old and new hardware IDs are identical. No replacement needed.'
            }
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

    # =========================================================================
    # Plans
    # =========================================================================

    def get_plans(self) -> Dict[str, Any]:
        product_id = self.config.get('product', {}).get('id', '')
        return self._client.get_plans(product_id)

    # =========================================================================
    # Countries
    # =========================================================================

    def get_countries(self) -> Dict[str, Any]:
        return self._client.get_countries()

    # =========================================================================
    # System Status
    # =========================================================================

    def get_api_status(self) -> Dict[str, Any]:
        return self._client.get_status()

    def get_notifications(self) -> Dict[str, Any]:
        return self._client.get_notifications()

    # =========================================================================
    # Device Binding
    # =========================================================================

    def bind_device(self, license_key: Optional[str] = None,
                    device_name: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please provide a license key or activate first.")
        result = self._client.bind_device(key, device_name=device_name)
        if result.get('success'):
            self.initialize()
        return result

    # =========================================================================
    # Cache Management
    # =========================================================================

    def clear_cache(self) -> None:
        self._cache.clear()

    def refresh(self) -> LicenseStatus:
        self._cache.invalidate_license_status()
        return self.initialize()
