"""License validation and management engine"""
from typing import Optional, Dict, Any
from datetime import datetime
from .client import Client
from .hardware import HardwareFingerprint


class LicenseStatus:
    def __init__(self, valid: bool, status: str, **kwargs):
        self.valid = valid
        self.status = status
        self.expires_at = kwargs.get('expires_at')
        self.days_remaining = kwargs.get('days_remaining', 0)
        self.plan = kwargs.get('plan')
        self.hardware_id = kwargs.get('hardware_id')
        self.message = kwargs.get('message')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'status': self.status,
            'expires_at': self.expires_at,
            'days_remaining': self.days_remaining,
            'plan': self.plan,
            'hardware_id': self.hardware_id,
            'message': self.message
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
            message=data.get('message')
        )


class LicenseEngine:
    def __init__(self, client: Client):
        self.client = client
        self._status: Optional[LicenseStatus] = None
        self._license_key: Optional[str] = None
        self._fingerprint = HardwareFingerprint.generate_fingerprint()

    def initialize(self) -> LicenseStatus:
        device_id = self._fingerprint['fingerprint']
        if self._license_key:
            try:
                result = self.client.validate_license(self._license_key, device_id)
                if result.get('success') and result.get('data', {}).get('valid'):
                    data = result['data']
                    self._status = LicenseStatus(
                        valid=True,
                        status=data.get('status', 'active'),
                        expires_at=data.get('expiry_date'),
                        days_remaining=data.get('days_left', 0),
                        plan=data.get('plan'),
                        hardware_id=device_id,
                        message='License valid'
                    )
                    return self._status
            except Exception:
                pass
        try:
            trial_result = self.client.check_trial(device_id)
            if trial_result.get('success') and trial_result.get('data', {}).get('has_trial'):
                data = trial_result['data']
                self._status = LicenseStatus(
                    valid=data.get('status') == 'active',
                    status=data.get('status', 'trial'),
                    expires_at=data.get('expiry_date'),
                    days_remaining=data.get('days_left', 0),
                    hardware_id=device_id,
                    message='Trial active' if data.get('status') == 'active' else 'Trial expired'
                )
                return self._status
        except Exception:
            pass
        self._status = LicenseStatus(
            valid=False,
            status='unlicensed',
            hardware_id=device_id,
            message='No valid license or trial found'
        )
        return self._status

    def validate(self, license_key: str) -> Dict:
        device_id = self._fingerprint['fingerprint']
        result = self.client.validate_license(license_key, device_id)
        if result.get('success') and result.get('data', {}).get('valid'):
            self._license_key = license_key
            self.initialize()
        return result

    def activate(self, license_key: str, device_name: str = '') -> Dict:
        device_id = self._fingerprint['fingerprint']
        result = self.client.activate_license(license_key, device_id, device_name)
        if result.get('success'):
            self._license_key = license_key
            self.initialize()
        return result

    def deactivate(self, license_key: Optional[str] = None) -> Dict:
        key = license_key or self._license_key
        if not key:
            return {'success': False, 'message': 'No license key provided'}
        device_id = self._fingerprint['fingerprint']
        result = self.client.deactivate_license(key, device_id)
        if result.get('success'):
            self._status = None
            if license_key is None:
                self._license_key = None
        return result

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict] = None) -> Dict:
        result = self.client.start_trial(email, customer_name, customer_data)
        if result.get('success'):
            self.initialize()
        return result

    def renew(self, extra_days: Optional[int] = None) -> Dict:
        if not self._license_key:
            return {'success': False, 'message': 'No license key in session'}
        return self.client._request('POST', '/api/v1/license/renew', {
            'license_key': self._license_key,
            'extra_days': extra_days
        })

    def replace_device(self, new_hardware_id: Optional[str] = None) -> Dict:
        if not self._license_key:
            return {'success': False, 'message': 'No license key in session'}
        device_id = new_hardware_id or self._fingerprint['fingerprint']
        return self.client._request('POST', '/api/v1/license/replace', {
            'license_key': self._license_key,
            'new_hardware_id': device_id
        })

    def get_status(self) -> Optional[LicenseStatus]:
        return self._status

    def is_valid(self) -> bool:
        if not self._status:
            return False
        return self._status.valid

    def get_hardware_fingerprint(self) -> Dict:
        return self._fingerprint

    def get_license_key(self) -> Optional[str]:
        return self._license_key
