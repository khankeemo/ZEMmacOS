"""API Client for ZEM MAC OS License API"""
import time
from typing import Any, Dict, Optional

import requests

from .crypto import generate_timestamp, generate_nonce, sign_request
from .hardware import HardwareDetector
from .cache import CacheManager


LICENSE_ENDPOINT = 'license'
TRIAL_ENDPOINT = 'trial'
DEVICE_ENDPOINT = 'device'

RETRYABLE_STATUSES = {500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.message = message
        self.data = data or {}
        super().__init__(f"API Error {status_code}: {message}")


class ApiClient:
    def __init__(
        self,
        config: Dict[str, Any],
        hardware: Optional[HardwareDetector] = None,
        cache: Optional[CacheManager] = None
    ):
        self.config = config
        self.api_config = config.get('api', {})
        self.base_url = self.api_config.get('url', '').rstrip('/')
        self.api_version = self.api_config.get('version', 'v1')
        self.api_key = self.api_config.get('public_key', '')
        self.api_secret = self.api_config.get('secret', '')
        self.timeout = float(self.api_config.get('timeout', 30000)) / 1000
        self.retry_count = self.api_config.get('retry_count', 3)
        self.product_id = config.get('product', {}).get('id', '')

        self._hardware = hardware or HardwareDetector()
        self._cache = cache

    def _get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

    def _sign_request(self, payload: Dict[str, Any],
                       method: str = 'POST',
                       path: str = '',
                       query: str = '') -> Dict[str, str]:
        timestamp = generate_timestamp()
        nonce = generate_nonce()
        signature = sign_request(payload, self.api_secret, timestamp, nonce,
                                  method=method, path=path, query=query)
        return {
            'x-api-key': self.api_key,
            'x-timestamp': timestamp,
            'x-nonce': nonce,
            'x-signature': signature
        }

    def _request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/{endpoint}"
        max_retries = retries if retries is not None else self.retry_count

        request_payload = payload.copy()
        if self.product_id:
            request_payload.setdefault('product_id', self.product_id)

        for attempt in range(max_retries + 1):
            api_path = f"/api/{self.api_version}/{endpoint}"
            headers = self._sign_request(request_payload, method='POST',
                                          path=api_path, query='')
            headers['Content-Type'] = 'application/json'

            try:
                response = requests.post(
                    url,
                    json=request_payload,
                    headers=headers,
                    timeout=self.timeout
                )

                data = {}
                try:
                    data = response.json()
                except Exception:
                    if response.text:
                        data = {'message': response.text}

                if 200 <= response.status_code < 300:
                    return data

                if response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = int(response.headers.get('Retry-After', 5))
                        time.sleep(retry_after)
                        continue
                    raise ApiError(response.status_code, 'Rate limit exceeded', data)

                if response.status_code in RETRYABLE_STATUSES:
                    if attempt < max_retries:
                        wait = (attempt + 1) * 2
                        time.sleep(wait)
                        continue
                    raise ApiError(response.status_code, 'Server error', data)

                message = data.get('message', data.get('error', f'HTTP {response.status_code}'))
                raise ApiError(response.status_code, message, data)

            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(504, f'Request timeout after {self.timeout}s') from e

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(503, f'Connection error: {str(e)}') from e

            except ApiError:
                raise

            except Exception as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(500, f'Request failed: {str(e)}') from e

        raise ApiError(500, f'Failed after {max_retries} retries')

    def _request_get(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/{endpoint}"
        max_retries = retries if retries is not None else self.retry_count

        for attempt in range(max_retries + 1):
            api_path = f"/api/{self.api_version}/{endpoint}"
            query_string = '&'.join(f"{k}={v}" for k, v in (params or {}).items())
            headers = self._sign_request({}, method='GET', path=api_path, query=query_string)
            headers['Content-Type'] = 'application/json'

            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                data = {}
                try:
                    data = response.json()
                except Exception:
                    if response.text:
                        data = {'message': response.text}

                if 200 <= response.status_code < 300:
                    return data

                if response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = int(response.headers.get('Retry-After', 5))
                        time.sleep(retry_after)
                        continue
                    raise ApiError(response.status_code, 'Rate limit exceeded', data)

                if response.status_code in RETRYABLE_STATUSES:
                    if attempt < max_retries:
                        wait = (attempt + 1) * 2
                        time.sleep(wait)
                        continue
                    raise ApiError(response.status_code, 'Server error', data)

                message = data.get('message', data.get('error', f'HTTP {response.status_code}'))
                raise ApiError(response.status_code, message, data)

            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(504, f'Request timeout after {self.timeout}s') from e

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(503, f'Connection error: {str(e)}') from e

            except ApiError:
                raise

            except Exception as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(500, f'Request failed: {str(e)}') from e

        raise ApiError(500, f'Failed after {max_retries} retries')

    # =========================================================================
    # OTP Endpoints
    # =========================================================================

    def send_otp(self, email: str, purpose: str = 'registration') -> Dict[str, Any]:
        payload = {
            'action': 'send',
            'email': email,
            'purpose': purpose
        }
        return self._request('auth/otp/send', payload)

    def verify_otp(self, email: str, otp_code: str) -> Dict[str, Any]:
        payload = {
            'action': 'verify',
            'email': email,
            'otp': otp_code
        }
        return self._request('auth/otp/verify', payload)

    # =========================================================================
    # Customer Endpoints
    # =========================================================================

    def store_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('customer/register', customer_data)

    # =========================================================================
    # License Endpoints
    # =========================================================================

    def validate_license(self, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'validate',
            'hardware_id': hardware_id
        }

        if self._cache and self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                return cached

        response = self._request(LICENSE_ENDPOINT, payload)

        if self._cache and response.get('success') and response.get('data', {}).get('valid'):
            self._cache.set_license_status(response)

        return response

    def activate_license(self, license_key: str, hardware_id: Optional[str] = None,
                         device_name: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'activate',
            'license_key': license_key,
            'hardware_id': hardware_id
        }
        if device_name:
            payload['device_name'] = device_name

        response = self._request(LICENSE_ENDPOINT, payload)

        if self._cache:
            self._cache.invalidate_license_status()

        return response

    def deactivate_license(self, license_key: str, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'deactivate',
            'license_key': license_key,
            'hardware_id': hardware_id
        }

        response = self._request(LICENSE_ENDPOINT, payload)

        if self._cache:
            self._cache.invalidate_license_status()

        return response

    def get_license_details(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if license_key:
            payload['license_key'] = license_key
        return self._request('license/details', payload)

    def renew_license(self, license_key: str, plan_id: Optional[str] = None,
                      extra_days: Optional[int] = None) -> Dict[str, Any]:
        payload = {
            'action': 'renew',
            'license_key': license_key
        }
        if plan_id is not None:
            payload['plan_id'] = plan_id
        if extra_days is not None:
            payload['extra_days'] = extra_days

        response = self._request(LICENSE_ENDPOINT, payload)

        if self._cache:
            self._cache.invalidate_license_status()

        return response

    def get_license_history(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if license_key:
            payload['license_key'] = license_key
        return self._request('license/history', payload)

    # =========================================================================
    # Trial Endpoints
    # =========================================================================

    def start_trial(
        self,
        email: str,
        customer_name: str = '',
        customer_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        hardware_id = self._get_hardware_id()

        payload: Dict[str, Any] = {
            'action': 'start',
            'customer_email': email,
            'customer_name': customer_name,
            'hardware_id': hardware_id
        }
        if customer_data:
            payload['customer_data'] = customer_data

        return self._request(TRIAL_ENDPOINT, payload)

    def get_trial_status(self, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'status',
            'hardware_id': hardware_id
        }

        return self._request(TRIAL_ENDPOINT, payload)

    def check_trial(self, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        return self.get_trial_status(hardware_id)

    def convert_trial(self, hardware_id: Optional[str] = None,
                      plan: Optional[str] = None,
                      license_key: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'convert',
            'hardware_id': hardware_id
        }
        if plan:
            payload['plan'] = plan
        if license_key:
            payload['license_key'] = license_key

        response = self._request(TRIAL_ENDPOINT, payload)

        if self._cache:
            self._cache.invalidate_license_status()

        return response

    # =========================================================================
    # Device Endpoints
    # =========================================================================

    def bind_device(self, license_key: str, hardware_id: Optional[str] = None,
                    device_name: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'bind',
            'license_key': license_key,
            'hardware_id': hardware_id
        }
        if device_name:
            payload['device_name'] = device_name

        return self._request(DEVICE_ENDPOINT, payload)

    def reset_device(self, license_key: str, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()

        payload = {
            'action': 'reset',
            'license_key': license_key,
            'hardware_id': hardware_id
        }

        return self._request(DEVICE_ENDPOINT, payload)

    def replace_device(self, license_key: str, new_hardware_id: Optional[str] = None,
                       old_hardware_id: Optional[str] = None,
                       device_name: Optional[str] = None) -> Dict[str, Any]:
        if new_hardware_id is None:
            new_hardware_id = self._get_hardware_id()

        if old_hardware_id is None:
            raise ValueError("old_hardware_id is required for device replacement")

        payload = {
            'action': 'replace',
            'license_key': license_key,
            'old_hardware_id': old_hardware_id,
            'new_hardware_id': new_hardware_id
        }
        if device_name:
            payload['device_name'] = device_name

        response = self._request(DEVICE_ENDPOINT, payload)

        if self._cache:
            self._cache.invalidate_license_status()

        return response

    # =========================================================================
    # Plans Endpoints
    # =========================================================================

    def get_plans(self, product_id: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if product_id:
            params['product_id'] = product_id
        return self._request_get('plans', params)

    # =========================================================================
    # Countries Endpoint
    # =========================================================================

    def get_countries(self) -> Dict[str, Any]:
        return self._request_get('countries')

    # =========================================================================
    # Status Endpoint
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        return self._request_get('status')

    # =========================================================================
    # Notifications Endpoint
    # =========================================================================

    def get_notifications(self) -> Dict[str, Any]:
        return self._request_get('notifications')
