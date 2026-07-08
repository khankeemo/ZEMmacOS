"""API Client for ZEM MAC OS License API"""
import requests
from typing import Optional, Dict, Any

class Client:
    def __init__(self, api_key: str, api_url: str = "https://www.websmithdigital.com"):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
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
        return self._request('POST', '/api/v1/license/validate', {
            'license_key': license_key,
            'device_id': device_id
        })

    def activate_license(self, license_key: str, device_id: str, device_name: str) -> Dict:
        return self._request('POST', '/api/v1/license/activate', {
            'license_key': license_key,
            'device_id': device_id,
            'device_name': device_name
        })

    def deactivate_license(self, license_key: str, device_id: str) -> Dict:
        return self._request('POST', '/api/v1/license/deactivate', {
            'license_key': license_key,
            'device_id': device_id
        })

    def start_trial(self, product_id: str, email: str, device_id: str) -> Dict:
        return self._request('POST', '/api/v1/trial/start', {
            'product_id': product_id,
            'email': email,
            'device_id': device_id
        })

    def check_trial(self, trial_id: str) -> Dict:
        return self._request('GET', f'/api/v1/trial/status/{trial_id}')

    def convert_trial(self, trial_id: str, plan_id: str) -> Dict:
        return self._request('POST', f'/api/v1/trial/convert/{trial_id}', {
            'plan_id': plan_id
        })
