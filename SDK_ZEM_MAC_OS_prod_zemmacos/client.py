"""API Client for ZEM MAC OS License API"""
import requests
from typing import Optional, Dict, Any, List

SDK_VERSION = "1.0.0"
RUNTIME_TYPE = "python"

class Client:
    def __init__(self, api_key: str, api_url: str = "https://websmith-z.vercel.app"):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.sdk_version = SDK_VERSION
        self.runtime_type = RUNTIME_TYPE
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = f"{self.api_url}{endpoint}"
        resp = self.session.request(method, url, json=data)
        resp.raise_for_status()
        return resp.json()

    def validate_license(self, license_key: str, device_id: str) -> Dict:
        return self._request('POST', '/api/v1/license', {
            'action': 'validate',
            'license_key': license_key,
            'hardware_id': device_id
        })

    def activate_license(self, license_key: str, device_id: str, device_name: str) -> Dict:
        return self._request('POST', '/api/v1/license', {
            'action': 'activate',
            'license_key': license_key,
            'hardware_id': device_id,
            'device_name': device_name
        })

    def deactivate_license(self, license_key: str, device_id: str) -> Dict:
        return self._request('POST', '/api/v1/license', {
            'action': 'deactivate',
            'license_key': license_key,
            'hardware_id': device_id
        })

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict] = None) -> Dict:
        from .hardware import HardwareFingerprint
        hw = HardwareFingerprint.generate_fingerprint()
        payload = {
            'action': 'start',
            'customer_email': email,
            'customer_name': customer_name,
            'hardware_id': hw['fingerprint'],
            'sdk_version': self.sdk_version,
            'runtime_type': self.runtime_type
        }
        if customer_data:
            payload.update(customer_data)
        return self._request('POST', '/api/v1/trial', payload)

    def check_trial(self, hardware_id: str) -> Dict:
        return self._request('POST', '/api/v1/trial', {
            'action': 'status',
            'hardware_id': hardware_id
        })

    def convert_trial(self, hardware_id: str, plan: str, name: str, email: str) -> Dict:
        return self._request('POST', '/api/v1/trial', {
            'action': 'convert',
            'hardware_id': hardware_id,
            'plan': plan,
            'customer_name': name,
            'customer_email': email
        })

    def send_otp(self, email: str) -> Dict:
        return self._request('POST', '/api/v1/auth/otp/send', {
            'email': email
        })

    def verify_otp(self, email: str, otp: str) -> Dict:
        return self._request('POST', '/api/v1/auth/otp/verify', {
            'email': email,
            'otp': otp
        })

    def store_customer(self, name: str, email: str, mobile: str,
                       country_code: str, company_name: str,
                       hardware_id: str) -> Dict:
        return self._request('POST', '/api/v1/customer/register', {
            'name': name,
            'email': email,
            'mobile': mobile,
            'country_code': country_code,
            'company_name': company_name,
            'hardware_id': hardware_id
        })

    def get_countries(self) -> Dict:
        return self._request('GET', '/api/v1/countries')

    def get_status(self) -> Dict:
        return self._request('GET', '/api/v1/status')
