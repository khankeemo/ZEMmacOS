"""
ZEM License API Client — desktop app talks ONLY to backend over HTTPS/HTTP.

No Google credentials, no database access, no local license authority.
"""

import time
from typing import Any, Callable, Dict, Optional

import requests

from zem_license.api_config import load_api_config

# Optional real-time logging hook (set by LicenseService)
_log_callback: Optional[Callable[[str, str], None]] = None


def set_license_log_callback(callback: Callable[[str, str], None]) -> None:
    """Register callback(message, level) for safe_console integration."""
    global _log_callback
    _log_callback = callback


def _log(message: str, level: str = "info") -> None:
    if _log_callback:
        _log_callback(message, level)
    else:
        print(f"[LicenseAPI][{level}] {message}")


class LicenseAPIClient:
    """REST client for ZEM License API."""

    def __init__(self):
        cfg = load_api_config()
        self.base_url = cfg["license_api_url"].rstrip("/")
        self.timeout = int(cfg.get("license_api_timeout", 15))
        self._session = requests.Session()
        self._session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "ZEMmacOS/3.0"}
        )

    def _request(self, method: str, path: str, json_body: dict = None, params: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        start = time.perf_counter()
        try:
            _log(f"Connecting to {url}", "debug")
            resp = self._session.request(
                method,
                url,
                json=json_body,
                params=params,
                timeout=self.timeout,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            _log(f"API {method} {path} → {resp.status_code} ({elapsed_ms}ms)", "info")

            if resp.status_code >= 400:
                detail = resp.text[:200]
                try:
                    detail = resp.json().get("detail", detail)
                except ValueError:
                    pass
                return {
                    "success": False,
                    "valid": False,
                    "error": str(detail),
                    "error_type": "api_error",
                    "http_status": resp.status_code,
                    "latency_ms": elapsed_ms,
                }

            try:
                data = resp.json()
            except ValueError:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid JSON response from license server",
                    "error_type": "api_error",
                    "http_status": resp.status_code,
                    "latency_ms": elapsed_ms,
                }
            data["latency_ms"] = elapsed_ms
            data["api_available"] = True
            return data

        except requests.exceptions.Timeout:
            _log(f"Timeout after {self.timeout}s: {path}", "warning")
            return {
                "success": False,
                "valid": False,
                "error": "License server timeout",
                "error_type": "timeout",
                "api_available": False,
            }
        except requests.exceptions.ConnectionError as exc:
            _log(f"Connection error: {exc}", "error")
            _log(
                "License server not reachable at the configured API URL.",
                "error",
            )
            return {
                "success": False,
                "valid": False,
                "error": (
                    f"License server is not reachable at {self.base_url}. "
                    "Please check your internet connection or contact support."
                ),
                "error_type": "connection",
                "api_available": False,
            }
        except Exception as exc:
            _log(f"Request error: {exc}", "error")
            return {
                "success": False,
                "valid": False,
                "error": str(exc),
                "error_type": "internal",
                "api_available": False,
            }

    def health_check(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def validate_license(self, name: str, email: str, license_key: str, hardware_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/license/validate",
            {
                "name": name,
                "email": email,
                "license_key": license_key,
                "hardware_id": hardware_id,
            },
        )

    def activate_license(
        self,
        name: str,
        email: str,
        license_key: str,
        hardware_id: str,
        device_name: str = "ZEMmacOS",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/license/activate",
            {
                "name": name,
                "email": email,
                "license_key": license_key,
                "hardware_id": hardware_id,
                "device_name": device_name,
            },
        )

    def get_license_info(self, license_key: str) -> Dict[str, Any]:
        return self._request("GET", "/license/info", params={"license_key": license_key})

    def reset_hardware(self, license_key: str, hardware_id: str = None) -> Dict[str, Any]:
        body = {"license_key": license_key}
        if hardware_id:
            body["hardware_id"] = hardware_id
        return self._request("POST", "/license/reset", body)

    def start_trial(self, hardware_id: str) -> Dict[str, Any]:
        return self._request("POST", "/trial/start", {"hardware_id": hardware_id})

    def trial_status(self, hardware_id: str) -> Dict[str, Any]:
        return self._request("POST", "/trial/status", {"hardware_id": hardware_id})


_client: Optional[LicenseAPIClient] = None


def get_api_client() -> LicenseAPIClient:
    global _client
    if _client is None:
        _client = LicenseAPIClient()
    return _client
