"""License validation engine"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from .client import Client
from .hardware import HardwareFingerprint

class LicenseEngine:
    def __init__(self, client: Client):
        self.client = client
        self._license_data: Optional[Dict] = None
        self._fingerprint = HardwareFingerprint.generate_fingerprint()

    def validate(self, license_key: str) -> Dict:
        device_id = self._fingerprint['fingerprint']
        result = self.client.validate_license(license_key, device_id)
        self._license_data = result.get('license', {})
        return result

    def activate(self, license_key: str, device_name: str) -> Dict:
        device_id = self._fingerprint['fingerprint']
        result = self.client.activate_license(license_key, device_id, device_name)
        self._license_data = result.get('license', {})
        return result

    def deactivate(self, license_key: str) -> Dict:
        device_id = self._fingerprint['fingerprint']
        return self.client.deactivate_license(license_key, device_id)

    def is_valid(self) -> bool:
        if not self._license_data:
            return False
        if self._license_data.get('status') != 'active':
            return False
        expires_at = self._license_data.get('expires_at')
        if expires_at:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expiry < datetime.now(expiry.tzinfo):
                return False
        return True

    def get_hardware_fingerprint(self) -> Dict:
        return self._fingerprint
