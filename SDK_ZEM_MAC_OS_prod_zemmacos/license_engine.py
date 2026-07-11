"""License engine — orchestrates Client, Cache, Hardware for ZEM MAC OS licensing."""
import json
from .client import Client
from .cache import CacheManager
from .hardware import HardwareFingerprint


class LicenseStatus:
    """Immutable view of a license-status API response dict."""
    def __init__(self, data: dict = None):
        self._data = data or {}

    @property
    def valid(self) -> bool:
        return bool(self._data.get('valid', False))

    @property
    def trial_active(self) -> bool:
        return bool(self._data.get('trial_active', False))

    @property
    def days_remaining(self) -> int:
        return self._data.get('days_remaining', 0) or 0

    @property
    def expires_at(self) -> str:
        return self._data.get('expires_at', '') or ''

    @property
    def plan(self) -> str:
        return self._data.get('plan', '') or ''

    @property
    def message(self) -> str:
        return self._data.get('message', '') or ''

    @property
    def status(self) -> str:
        return self._data.get('status', 'inactive') or 'inactive'

    @property
    def raw(self) -> dict:
        return dict(self._data)


class LicenseEngine:
    """Single orchestrator for all license operations.

    Owns Client, CacheManager, and hardware fingerprint.
    ZEMmacOS must use this class exclusively — never call Client/Cache/HW directly.
    """

    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        api_cfg = self.config['api']
        self._client = Client(api_key=api_cfg['public_key'], api_url=api_cfg['url'])
        product = self.config['product']
        self._product_name = product['name']
        self._cache = CacheManager(product_name=self._product_name)
        hw = HardwareFingerprint.generate_fingerprint()
        self._device_id = hw['fingerprint']
        self._license_key = ''
        self._status = LicenseStatus()

    @property
    def client(self):
        return self._client

    @property
    def cache(self):
        return self._cache

    @property
    def device_id(self) -> str:
        return self._device_id

    def initialize(self) -> LicenseStatus:
        """Check stored license, then trial, and return current status."""
        stored_key = self._cache.get('license_key', '')
        self._license_key = stored_key

        if stored_key:
            try:
                result = self._client.validate_license(stored_key, self._device_id)
                if result.get('valid'):
                    self._status = LicenseStatus(result)
                    return self._status
            except Exception:
                pass

        try:
            trial = self._client.check_trial(self._device_id)
            if trial.get('trial_active'):
                self._status = LicenseStatus(trial)
                return self._status
        except Exception:
            pass

        self._status = LicenseStatus({'status': 'inactive', 'message': 'No active license or trial found.'})
        return self._status

    def get_status(self) -> LicenseStatus:
        return self._status

    def refresh(self) -> LicenseStatus:
        """Re-validate license and trial, returns updated status."""
        return self.initialize()

    def activate(self, license_key: str) -> dict:
        """Activate a license key. On success, caches key and updates status."""
        result = self._client.activate_license(
            license_key,
            self._device_id,
            'ZEM MAC OS'
        )
        if result.get('success'):
            self._license_key = license_key
            self._cache.set('license_key', license_key)
            try:
                vr = self._client.validate_license(license_key, self._device_id)
                if vr.get('valid'):
                    self._status = LicenseStatus(vr)
            except Exception:
                self._status = LicenseStatus(result)
        return result
