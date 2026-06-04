"""
ZEM License Admin API Client — all REST communication for admin_tools.

NO Google imports. NO local license authority.
"""

import json
import os
import time
from typing import Any, Callable, Dict, Optional

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "license_api_url": "http://localhost:8000",
    "license_api_timeout": 15,
}

_log_callback: Optional[Callable[[str, str], None]] = None


def set_api_log_callback(callback: Callable[[str, str], None]) -> None:
    global _log_callback
    _log_callback = callback


def _log(msg: str, level: str = "info") -> None:
    if _log_callback:
        _log_callback(msg, level)


def load_api_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for k in DEFAULT_CONFIG:
                if k in loaded:
                    cfg[k] = loaded[k]
        except (json.JSONDecodeError, OSError):
            pass

    env_url = os.environ.get("ZEM_LICENSE_API_URL")
    if env_url:
        cfg["license_api_url"] = env_url.rstrip("/")
        return cfg

    local_backend_path = os.path.join(BASE_DIR, "ZEM_API", "main.py")
    if os.path.exists(local_backend_path):
        local_url = "http://127.0.0.1:8000"
        if cfg["license_api_url"] not in ("http://127.0.0.1:8000", "http://localhost:8000"):
            cfg["license_api_url"] = local_url
    return cfg


def resolve_admin_key() -> str:
    key = os.environ.get("ZEM_ADMIN_API_KEY", "")
    key_file = os.path.join(SCRIPT_DIR, "admin_api.key")
    if not key and os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
    if not key:
        env_path = os.path.join(BASE_DIR, "ZEM_API", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("ADMIN_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    return key


class AdminAPIClient:
    """Admin REST client with retries and structured responses."""

    def __init__(self, admin_key: str = None, base_url: str = None, timeout: int = None, retries: int = 2):
        cfg = load_api_config()
        self.base_url = (base_url or cfg["license_api_url"]).rstrip("/")
        self.timeout = timeout or int(cfg.get("license_api_timeout", 15))
        self.retries = retries
        self.admin_key = admin_key if admin_key is not None else resolve_admin_key()
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "X-Admin-Key": self.admin_key,
            "User-Agent": "ZEMmacOS-Admin/2.0",
        })
        self.last_latency_ms: Optional[int] = None

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict = None,
        params: dict = None,
        use_admin_key: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {}
        if not use_admin_key:
            headers = {"Content-Type": "application/json"}

        last_error = None
        for attempt in range(self.retries + 1):
            start = time.perf_counter()
            try:
                _log(f"{method} {path}", "debug")
                resp = self._session.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    timeout=self.timeout,
                    headers=headers if not use_admin_key else None,
                )
                self.last_latency_ms = int((time.perf_counter() - start) * 1000)
                _log(f"→ {resp.status_code} ({self.last_latency_ms}ms)", "info")

                if resp.status_code >= 400:
                    try:
                        detail = resp.json().get("detail", resp.text)
                    except Exception:
                        detail = resp.text
                    return {
                        "success": False,
                        "error": str(detail),
                        "http_status": resp.status_code,
                        "latency_ms": self.last_latency_ms,
                    }
                data = resp.json()
                if isinstance(data, dict):
                    data.setdefault("success", True)
                    data["latency_ms"] = self.last_latency_ms
                return data
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                _log(f"Connection failed: {exc}", "error")
                return {
                    "success": False,
                    "error": last_error,
                    "error_type": "connection",
                    "api_available": False,
                }
        return {"success": False, "error": last_error or "Unknown error"}

    def health_check(self) -> Dict[str, Any]:
        session = requests.Session()
        start = time.perf_counter()
        try:
            resp = session.get(f"{self.base_url}/health", timeout=self.timeout)
            self.last_latency_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                data["success"] = True
                data["latency_ms"] = self.last_latency_ms
                data["api_available"] = True
                return data
            return {"success": False, "error": resp.text, "http_status": resp.status_code}
        except requests.exceptions.RequestException as exc:
            return {
                "success": False,
                "status": "offline",
                "error": str(exc),
                "error_type": "connection",
                "api_available": False,
            }

    def create_license(
        self,
        name: str,
        email: str,
        expiry_days: int = 365,
        plan: str = "Standard",
        max_devices: int = 1,
        notes: str = "",
        license_key: str = None,
    ) -> Dict[str, Any]:
        body = {
            "name": name,
            "email": email,
            "expiry_days": expiry_days,
            "plan": plan,
            "max_devices": max_devices,
            "notes": notes,
        }
        if license_key:
            body["license_key"] = license_key
        return self._request("POST", "/admin/create-license", body)

    def create_test_license(self) -> Dict[str, Any]:
        result = self._request("POST", "/admin/create-test-license", {})
        if result.get("http_status") == 404 or "Not Found" in str(result.get("error", "")):
            _log("create-test-license not found — using create-license fallback", "warning")
            return self.create_license(
                name="Test User",
                email="test@example.com",
                expiry_days=365,
                plan="Professional",
                max_devices=1,
                notes="Test license (fallback)",
            )
        return result

    def validate_license(
        self,
        license_key: str,
        name: str = "",
        email: str = "admin@example.com",
        hardware_id: str = "ADMIN-CHECK-00000000",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/admin/validate-license",
            {
                "license_key": license_key,
                "name": name,
                "email": email,
                "hardware_id": hardware_id,
            },
        )

    def search_by_email(self, email: str) -> Dict[str, Any]:
        return self._request("GET", "/admin/search/email", params={"email": email})

    def search_by_license(self, license_key: str) -> Dict[str, Any]:
        return self._request("GET", "/admin/search/license", params={"license_key": license_key})

    def search_customer(self, email: str) -> Dict[str, Any]:
        return self.search_by_email(email)

    def reset_hardware(self, license_key: str, hardware_id: str = None) -> Dict[str, Any]:
        body = {"license_key": license_key}
        if hardware_id:
            body["hardware_id"] = hardware_id
        return self._request("POST", "/admin/reset-device", body)

    def revoke_license(self, license_key: str) -> Dict[str, Any]:
        return self._request("POST", "/admin/revoke-license", {"license_key": license_key})

    def extend_license(self, license_key: str, extra_days: int) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/admin/extend-license",
            {"license_key": license_key, "extra_days": extra_days},
        )

    def get_dashboard_stats(self) -> Dict[str, Any]:
        return self._request("GET", "/admin/dashboard")

    def get_activation_history(self, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", "/admin/activations", params={"limit": limit})

    def get_logs(self, limit: int = 200) -> Dict[str, Any]:
        return self._request("GET", "/admin/logs", params={"limit": limit})

    def get_trials(self, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", "/admin/trials", params={"limit": limit})

    def reset_device(self, license_key: str, hardware_id: str = None) -> Dict[str, Any]:
        return self.reset_hardware(license_key, hardware_id)
