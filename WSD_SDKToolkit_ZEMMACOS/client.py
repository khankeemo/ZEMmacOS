"""API Client for Universal License Platform — transport layer only.

Responsibility matrix (SDK V2):
- HTTP requests, HMAC authentication, retry, response parsing.
- NEVER touches UI, refresh, cache, status, or dialogs.
- All orchestration (validation order, cache writes, events) lives in
  LicenseEngine; the engine is the only module that may call state changes.
"""
import os
import time
from typing import Any, Dict, Optional

import requests

from .crypto import generate_timestamp, generate_nonce, sign_request
from .hardware import HardwareDetector

SDK_VERSION = "1.0.0"
RUNTIME_TYPE = "python"
RETRYABLE_STATUSES = {500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.message = message
        self.data = data or {}
        super().__init__(f"API Error {status_code}: {message}")


class ConnectionUnavailable(ApiError):
    """Backend is genuinely unreachable (network error / timeout)."""
    def __init__(self, message: str):
        super().__init__(503, message)


class ApiClient:
    def __init__(
        self,
        config: Dict[str, Any],
        hardware: Optional[HardwareDetector] = None,
        cache: Optional[Any] = None
    ):
        # ``cache`` is accepted for backward compatibility only — the client is
        # transport-only and never reads or writes cache state.
        self.config = config
        self.api_config = config.get('api', {})
        self.base_url = self.api_config.get('url', '').rstrip('/')
        app_url = self.api_config.get('app_url', '').rstrip('/')
        self.app_url = app_url or self.base_url
        self.api_version = self.api_config.get('version', 'v1')
        self.api_key = self.api_config.get('public_key', '')
        self.api_secret = self.api_config.get('secret', '')
        self.timeout = float(self.api_config.get('timeout', 30000)) / 1000
        self.retry_count = self.api_config.get('retry_count', 3)
        self.product_id = config.get('product', {}).get('id', '')
        self.product_name = config.get('product', {}).get('name', '')
        self._hardware = hardware or HardwareDetector()

    def _get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

    def _sign_request(self, payload: Dict[str, Any],
                       method: str = 'POST',
                       path: str = '',
                       query: str = '') -> Dict[str, str]:
        timestamp = generate_timestamp()
        nonce = generate_nonce()
        signature = sign_request(payload, self.api_key, timestamp, nonce,
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
                    url, json=request_payload,
                    headers=headers, timeout=self.timeout
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
                        time.sleep((attempt + 1) * 2)
                        continue
                    raise ApiError(response.status_code, 'Server error', data)
                message = data.get('message', data.get('error', f'HTTP {response.status_code}'))
                raise ApiError(response.status_code, message, data)
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ConnectionUnavailable(f'Request timeout after {self.timeout}s')
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ConnectionUnavailable(f'Connection error: {str(e)}')
            except ApiError:
                raise
            except Exception as e:
                if attempt < max_retries:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise ApiError(500, f'Request failed: {str(e)}')
        raise ApiError(500, f'Failed after {max_retries} retries')

    def send_request(self, request_type: str, customer_name: str, customer_email: str,
                     subject: str = '', message: str = '',
                     license_key: str = '', hardware_id: str = '',
                     plan_name: str = '', product_name: str = '',
                     customer_mobile: str = '', current_plan_id: str = '',
                     current_plan_name: str = '', requested_plan_id: str = '',
                     requested_plan_name: str = '') -> Dict[str, Any]:
        payload = {
            'request_type': request_type,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_mobile': customer_mobile,
            'product_name': product_name or self.product_name,
            'plan_name': plan_name,
            'license_key': license_key,
            'hardware_id': hardware_id or self._get_hardware_id(),
            'sdk_version': SDK_VERSION,
            'runtime_type': RUNTIME_TYPE,
            'subject': subject or f'{request_type} Request',
            'message': message or f'{request_type} request from SDK',
            'current_plan_id': current_plan_id,
            'current_plan_name': current_plan_name,
            'requested_plan_id': requested_plan_id,
            'requested_plan_name': requested_plan_name,
        }
        return self._request('request', payload)

    def send_otp(self, email: str) -> Dict[str, Any]:
        endpoint = 'auth/otp/send'
        payload = {'email': email, 'product_id': self.product_id}
        return self._request(endpoint, payload)

    def verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        endpoint = 'auth/otp/verify'
        payload = {'email': email, 'otp': otp, 'product_id': self.product_id}
        return self._request(endpoint, payload)

    def register_customer(self, name: str, email: str, mobile: str,
                           country_code: str, hardware_id: str,
                           company_name: str = '') -> Dict[str, Any]:
        endpoint = 'customer/register'
        payload = {
            'name': name, 'email': email, 'mobile': mobile,
            'country_code': country_code, 'hardware_id': hardware_id,
            'company_name': company_name, 'product_id': self.product_id,
        }
        return self._request(endpoint, payload)

    def get_countries(self) -> Dict[str, Any]:
        endpoint = 'countries'
        payload = {'action': 'list'}
        return self._request(endpoint, payload)

    def validate_license(self, license_key: str, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        payload = {'action': 'validate', 'license_key': license_key, 'hardware_id': hardware_id}
        response = self._request('license', payload)
        return response

    def activate_license(self, license_key: str, hardware_id: Optional[str] = None,
                         idempotency: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        payload = {'action': 'activate', 'license_key': license_key, 'hardware_id': hardware_id,
                   'product_id': self.product_id}
        if idempotency:
            payload.update(idempotency)
        response = self._request('license', payload)
        return response

    def deactivate_license(self, license_key: str, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        payload = {'license_key': license_key, 'hardware_id': hardware_id}
        response = self._request('license/deactivate', payload)
        return response

    def renew_license(self, license_key: str, extra_days: Optional[int] = None,
                      idempotency: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        payload = {'action': 'renew', 'license_key': license_key}
        if extra_days is not None:
            payload['extra_days'] = extra_days
        if idempotency:
            payload.update(idempotency)
        response = self._request('license', payload)
        return response

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None,
                    idempotency: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        hardware_id = self._get_hardware_id()
        payload: Dict[str, Any] = {
            'action': 'start', 'customer_email': email,
            'customer_name': customer_name, 'hardware_id': hardware_id
        }
        if customer_data:
            payload['customer_data'] = customer_data
        if idempotency:
            payload.update(idempotency)
        return self._request('trial', payload)

    def get_license_status(self, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        url = f"{self.base_url}/internal/backend/license/status?hardware_id={hardware_id}"
        api_path = f"/internal/backend/license/status"
        headers = self._sign_request({}, method='GET', path=api_path, query=f"hardware_id={hardware_id}")
        headers['Content-Type'] = 'application/json'
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            data = {}
            try:
                data = resp.json()
            except Exception:
                if resp.text:
                    data = {'message': resp.text}
            # Return the backend response exactly as-is, including its
            # universal status on 4xx/5xx. The SDK renders the backend verdict;
            # it never substitutes a locally-inferred status.
            data['http_status'] = resp.status_code
            data['success'] = bool(data.get('success', 200 <= resp.status_code < 300))
            return data
        except requests.exceptions.Timeout:
            raise ConnectionUnavailable(f'Request timeout after {self.timeout}s')
        except requests.exceptions.ConnectionError as e:
            raise ConnectionUnavailable(f'Connection error: {str(e)}')
        except Exception as e:
            raise ConnectionUnavailable(f'License status request failed: {str(e)}')

    def get_health(self) -> Dict[str, Any]:
        """Non-mutating health/version probe (SECTION 0D §15/§17)."""
        url = f"{self.base_url}/api/{self.api_version}/health"
        api_path = f"/api/{self.api_version}/health"
        headers = self._sign_request({}, method='GET', path=api_path, query='')
        headers['Content-Type'] = 'application/json'
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code in (200, 503):
                return resp.json()
            return {'status': 'error', 'http_status': resp.status_code, 'tests': {}}
        except requests.exceptions.Timeout:
            return {'status': 'error', 'error': 'timeout', 'tests': {}}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'error', 'error': str(e), 'tests': {}}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'tests': {}}

    def get_trial_status(self, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        return self._request('trial', {'action': 'status', 'hardware_id': hardware_id})

    def convert_trial(
        self,
        hardware_id: Optional[str] = None,
        plan: Optional[str] = None,
        customer_name: str = '',
        customer_email: str = '',
        idempotency: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        payload: Dict[str, Any] = {
            'action': 'convert',
            'hardware_id': hardware_id,
            'plan': plan or '',
            'customer_name': customer_name or 'SDK User',
            'customer_email': customer_email or '',
        }
        if idempotency:
            payload.update(idempotency)
        response = self._request('trial', payload)
        return response

    def bind_device(
        self,
        license_key: str,
        hardware_id: Optional[str] = None,
        device_name: Optional[str] = None,
        idempotency: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if hardware_id is None:
            hardware_id = self._get_hardware_id()
        payload: Dict[str, Any] = {'action': 'bind', 'license_key': license_key, 'hardware_id': hardware_id}
        if device_name:
            payload['device_name'] = device_name
        if idempotency:
            payload.update(idempotency)
        return self._request('device', payload)

    def verify_license_for_renewal(self, license_key: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {'license_key': license_key}
        return self._request('license/verify-renewal', payload)

    def get_license_details(self, license_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/license/details/{license_key}"
        api_path = f"/api/{self.api_version}/license/details/{license_key}"
        headers = self._sign_request({}, method='GET', path=api_path)
        headers['Content-Type'] = 'application/json'
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'error': resp.json().get('message', f'HTTP {resp.status_code}')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_available_plans(self, license_key: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {'license_key': license_key}
        api_path = f"/api/{self.api_version}/license/verify-renewal"
        headers = self._sign_request(payload, method='POST', path=api_path, query='')
        headers['Content-Type'] = 'application/json'
        url = f"{self.base_url}{api_path}"
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                plans = data.get('available_plans', [])
                return {
                    'success': True,
                    'product': {'id': data.get('product_id', ''), 'name': data.get('product_name', '')},
                    'current_plan': {'id': data.get('plan_id', ''), 'name': data.get('plan', '')},
                    'plans': plans,
                }
            return {'success': False, 'plans': []}
        except Exception:
            return {'success': False, 'plans': []}

    def get_products(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/store/products"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'products': []}
        except Exception:
            return {'success': False, 'products': []}

    def get_request_history(self, email: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/request?email={email}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'requests': []}
        except Exception:
            return {'success': False, 'requests': []}

    def send_reactivation_request(self, license_key: str, customer_name: str = '',
                                  customer_email: str = '', message: str = '') -> Dict[str, Any]:
        payload = {
            'license_key': license_key,
            'customer_name': customer_name or 'SDK User',
            'customer_email': customer_email or '',
            'hardware_id': self._get_hardware_id(),
            'message': message or 'Reactivation request from SDK',
        }
        return self._request('reactivations', payload)

    def send_support_request(self, license_key: str = '', customer_name: str = '',
                             customer_email: str = '', subject: str = '',
                             message: str = '') -> Dict[str, Any]:
        payload = {
            'request_type': 'SUPPORT',
            'license_key': license_key or '',
            'customer_name': customer_name or 'SDK User',
            'customer_email': customer_email or '',
            'hardware_id': self._get_hardware_id(),
            'subject': subject or 'Support Request',
            'message': message or 'Support request from SDK',
        }
        return self._request('support', payload)

    def send_renewal_request(self, license_key: str, customer_name: str = '',
                           customer_email: str = '', customer_mobile: str = '',
                           message: str = '', request_type: str = 'renew',
                           current_plan_id: str = '', current_plan_name: str = '',
                           requested_plan_id: str = '', requested_plan_name: str = '') -> Dict[str, Any]:
        return self._request(
            'requests',
            {
                'request_type': request_type,
                'license_key': license_key,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_mobile': customer_mobile,
                'message': message,
                'current_plan_id': current_plan_id,
                'current_plan_name': current_plan_name,
                'requested_plan_id': requested_plan_id,
                'requested_plan_name': requested_plan_name,
            },
        )

    def create_communication(self, category: str = 'general',
                             customer_email: str = '',
                             customer_name: str = '',
                             subject: str = '', message: str = '',
                             product_id: str = '', license_key: str = '',
                             hardware_id: str = '', sdk_version: str = '',
                             runtime_type: str = '') -> Dict[str, Any]:
        payload = {
            'category': category,
            'customer_email': customer_email,
            'customer_name': customer_name or 'SDK User',
            'subject': subject or f'{category} request',
            'message': message or f'{category} request from SDK',
            'product_id': product_id,
            'license_key': license_key or '',
            'hardware_id': hardware_id or self._get_hardware_id(),
            'sdk_version': sdk_version or SDK_VERSION,
            'runtime_type': runtime_type or RUNTIME_TYPE,
        }
        return self._request('communication/create', payload)

    def upload_attachment(self, conversation_id: str, file_path: str) -> Dict[str, Any]:
        """Upload a file to an existing conversation (multipart).

        Uses the same HMAC-signed headers as every other request; the payload
        is the conversation id (files are sent as multipart form data).
        """
        endpoint = f"communication/{conversation_id}/attach"
        url = f"{self.base_url}/api/{self.api_version}/{endpoint}"
        payload = {'conversation_id': conversation_id}
        headers = self._sign_request(payload, method='POST',
                                     path=f"/api/{self.api_version}/{endpoint}",
                                     query='')
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    url, files={'file': (os.path.basename(file_path), f)},
                    headers=headers, timeout=self.timeout
                )
        except FileNotFoundError:
            return {'success': False, 'message': 'Attachment file not found'}
        except OSError as e:
            return {'success': False, 'message': f'Failed to read attachment: {e}'}
        data = {}
        try:
            data = response.json()
        except Exception:
            if response.text:
                data = {'message': response.text}
        if 200 <= response.status_code < 300:
            return data
        message = data.get('message', data.get('error', f'HTTP {response.status_code}'))
        return {'success': False, 'message': message, 'error': data}

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/communication/{conversation_id}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'conversation': None}
        except Exception:
            return {'success': False, 'conversation': None}

    def reply_to_conversation(self, conversation_id: str, message: str,
                               customer_name: str = '',
                               customer_email: str = '') -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/communication/{conversation_id}/reply"
        payload = {
            'message': message,
            'customer_name': customer_name or 'SDK User',
            'customer_email': customer_email or '',
        }
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'message': 'Failed to send reply'}
        except Exception:
            return {'success': False, 'message': 'Failed to send reply'}

    def list_conversations(self, email: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/communication/list?email={email}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'conversations': []}
        except Exception:
            return {'success': False, 'conversations': []}

    def get_notifications(self, email: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/notifications?email={email}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'notifications': []}
        except Exception:
            return {'success': False, 'notifications': []}

    def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/notifications/read"
        try:
            resp = requests.post(url, json={'id': notification_id}, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False}
        except Exception:
            return {'success': False}

    def get_unread_notification_count(self, email: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{self.api_version}/notifications/unread-count?email={email}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'success': False, 'count': 0}
        except Exception:
            return {'success': False, 'count': 0}
