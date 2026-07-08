import os
import sys
import json
import base64
import hashlib
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "ZEMmacOS"))

from wsd_sdk import Client, LicenseEngine, HardwareFingerprint

CONFIG_PATH = os.path.join(BASE_DIR, "ZEMmacOS", "wsd_sdk", "config", "api-config.json")
CACHE_DIR_NAME = ".zemmacos_wsd"
LICENSE_CACHE_FILE = "license_cache.json"
TRIAL_CACHE_FILE = "trial_cache.json"

_log_callback: Optional[Callable[[str, str], None]] = None


def set_license_log_callback(callback: Callable[[str, str], None]) -> None:
    global _log_callback
    _log_callback = callback


def _log(message: str, level: str = "info") -> None:
    if _log_callback:
        _log_callback(message, level)
    else:
        print(f"[WSD_License][{level}] {message}")


def _get_cache_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        app_dir = os.path.join(base, "ZEMmacOS")
    else:
        app_dir = os.path.expanduser("~/.zemmacos")
    cache_dir = Path(app_dir) / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


class WSDLicenseService:
    def __init__(self):
        config = _load_config()
        api_config = config.get("api", {})
        product_config = config.get("product", {})

        api_key = api_config.get("public_key", "")
        api_url = api_config.get("url", "https://www.websmithdigital.com")
        self.product_id = product_config.get("id", "prod_zemmacos")
        self.trial_config = config.get("trial", {})

        self._client = Client(api_key=api_key, api_url=api_url)
        self._engine = LicenseEngine(client=self._client)
        self._fingerprint = HardwareFingerprint.generate_fingerprint()
        self._device_id = self._fingerprint["fingerprint"]
        self._console = None
        self._config = config

        self._license_cache = None
        self._trial_cache = None

    def attach_console(self, safe_console) -> None:
        self._console = safe_console
        def log_cb(msg: str, level: str = "info"):
            if safe_console and safe_console.is_valid():
                safe_console.append(f"[License] {msg}", level)
        set_license_log_callback(log_cb)

    def _cache_path(self, name: str) -> Path:
        return _get_cache_dir() / name

    def _save_json_cache(self, name: str, data: dict) -> None:
        path = self._cache_path(name)
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            _log(f"Failed to write cache {name}: {exc}", "error")

    def _load_json_cache(self, name: str) -> dict:
        path = self._cache_path(name)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _clear_json_cache(self, name: str) -> None:
        path = self._cache_path(name)
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                _log(f"Failed to clear cache {name}: {exc}", "error")

    def get_hardware_id(self) -> str:
        return self._device_id

    def get_hardware_info(self) -> dict:
        return self._fingerprint

    def check_license(self) -> dict:
        _log("Checking license status...", "debug")

        hwid = self.get_hardware_id()
        cache = self._load_json_cache(LICENSE_CACHE_FILE)
        trial = self._load_json_cache(TRIAL_CACHE_FILE)

        license_key = cache.get("license_key", "")

        if license_key:
            try:
                result = self._engine.validate(license_key)
                if result.get("valid", False) or result.get("success", False):
                    license_data = result.get("license", result)
                    status = license_data.get("status", "active")
                    expires_at = license_data.get("expires_at")
                    days_left = 0
                    if expires_at:
                        try:
                            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                            now = datetime.now(expiry.tzinfo if expiry.tzinfo else timezone.utc)
                            diff = expiry - now
                            days_left = max(0, diff.days)
                        except ValueError:
                            pass

                    if status == "active":
                        _log(f"License valid - {days_left} days remaining", "success")
                        return {
                            "is_valid": True,
                            "is_trial": False,
                            "license_type": "paid",
                            "status": "licensed",
                            "days_left": days_left,
                            "customer_name": cache.get("customer_name", ""),
                            "customer_email": cache.get("customer_email", ""),
                            "source": "api",
                            "message": "License is active",
                        }

                error_type = result.get("error_type", "")
                if error_type in ("hardware_mismatch", "expired", "inactive", "revoked", "device_limit"):
                    _log(f"License invalid: {result.get('error', 'unknown error')}", "error")
                    self._clear_json_cache(LICENSE_CACHE_FILE)
                    return {
                        "is_valid": False,
                        "is_trial": False,
                        "license_type": "none",
                        "status": "blocked",
                        "days_left": 0,
                        "message": result.get("error", "License is invalid"),
                        "error_type": error_type,
                    }
            except Exception as exc:
                _log(f"License validation error: {exc}", "warning")

        trial_id = trial.get("trial_id", "")
        trial_email = trial.get("email", "")
        if trial_id:
            try:
                trial_result = self._client.check_trial(trial_id)
                if trial_result.get("valid", False) or trial_result.get("success", False):
                    trial_data = trial_result.get("trial", trial_result)
                    days_left = trial_data.get("days_remaining", trial_data.get("days_left", 0))
                    if days_left > 0:
                        _log(f"Trial active - {days_left} days remaining", "info")
                        return {
                            "is_valid": True,
                            "is_trial": True,
                            "license_type": "trial",
                            "status": "trial",
                            "days_left": days_left,
                            "message": f"Trial active. {days_left} days remaining.",
                            "source": "api",
                        }

                _log(f"Trial expired or invalid", "warning")
                self._clear_json_cache(TRIAL_CACHE_FILE)
                return {
                    "is_valid": False,
                    "is_trial": True,
                    "license_type": "none",
                    "status": "expired",
                    "days_left": 0,
                    "message": "Trial has expired",
                    "error_type": "trial_expired",
                }
            except Exception as exc:
                _log(f"Trial check error: {exc}", "warning")

        if cache.get("offline_data"):
            offline = cache["offline_data"]
            expires = offline.get("expires_at", "")
            if expires:
                try:
                    expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    now = datetime.now(expiry.tzinfo if expiry.tzinfo else timezone.utc)
                    if now < expiry:
                        days_left = max(0, (expiry - now).days)
                        _log(f"Offline grace - {days_left} days remaining", "warning")
                        return {
                            "is_valid": True,
                            "is_trial": False,
                            "license_type": "paid",
                            "status": "licensed",
                            "days_left": days_left,
                            "customer_name": cache.get("customer_name", ""),
                            "customer_email": cache.get("customer_email", ""),
                            "source": "cache_offline_grace",
                            "message": f"Offline grace mode. {days_left} days remaining.",
                        }
                except ValueError:
                    pass

        return {
            "is_valid": False,
            "is_trial": False,
            "license_type": "none",
            "status": "blocked",
            "days_left": 0,
            "message": "No valid license. Activate online or start trial.",
        }

    def get_badge_info(self) -> dict:
        status = self.check_license()
        if status.get("license_type") == "paid" and status.get("is_valid"):
            days = status.get("days_left", 0)
            if days <= 7:
                return {"text": f"\u26a0 License expires in {days} days", "color_key": "warning"}
            return {"text": "\u2713 Licensed", "color_key": "success"}
        if status.get("license_type") == "trial" and status.get("is_valid"):
            days = status.get("days_left", 0)
            return {"text": f"Trial \u2022 {days} days left", "color_key": "warning"}
        if status.get("status") == "expired":
            return {"text": "\u26a0 Trial Expired", "color_key": "error"}
        return {"text": "License Required", "color_key": "error"}

    def activate_license(self, name: str, email: str, license_key: str) -> dict:
        _log("Activating license via WSD SDK...", "info")
        try:
            result = self._engine.activate(license_key, device_name="ZEMmacOS")
            if result.get("success", False) or result.get("valid", False):
                license_data = result.get("license", result)
                self._save_json_cache(LICENSE_CACHE_FILE, {
                    "license_key": license_key,
                    "customer_name": name.strip(),
                    "customer_email": email.strip().lower(),
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                    "offline_data": license_data,
                })
                self._clear_json_cache(TRIAL_CACHE_FILE)
                days_left = license_data.get("days_left", 0)
                _log("Activation successful", "success")
                return {
                    "success": True,
                    "message": result.get("message", "License activated"),
                    "days_left": days_left,
                    "expiry_date": license_data.get("expires_at"),
                }
            _log(f"Activation failed: {result.get('error', 'unknown error')}", "error")
            return {
                "success": False,
                "error": result.get("error", "Activation failed"),
                "error_type": result.get("error_type", "unknown"),
            }
        except Exception as exc:
            _log(f"Activation error: {exc}", "error")
            return {
                "success": False,
                "error": str(exc),
                "error_type": "internal",
            }

    def start_trial(self) -> dict:
        _log("Starting trial via WSD SDK...", "info")
        try:
            result = self._client.start_trial(
                product_id=self.product_id,
                email="",
                device_id=self._device_id,
            )
            if result.get("success", False) or result.get("valid", False):
                trial_data = result.get("trial", result)
                trial_id = trial_data.get("trial_id", result.get("trial_id", ""))
                if not trial_id:
                    trial_id = hashlib.sha256(
                        f"{self._device_id}_{datetime.now(timezone.utc).isoformat()}".encode()
                    ).hexdigest()[:16]
                self._save_json_cache(TRIAL_CACHE_FILE, {
                    "trial_id": trial_id,
                    "email": "",
                    "device_id": self._device_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                })
                days = trial_data.get("days_remaining", trial_data.get("days_left", self.trial_config.get("days", 7)))
                _log(f"Trial started - {days} days", "success")
                return {
                    "success": True,
                    "message": result.get("message", f"Trial started - {days} days"),
                    "days_remaining": days,
                }
            _log(f"Trial start failed: {result.get('error', 'unknown error')}", "error")
            return {
                "success": False,
                "message": result.get("error", "Trial unavailable"),
                "error_type": result.get("error_type", "api_error"),
            }
        except Exception as exc:
            _log(f"Trial start error: {exc}", "error")
            return {"success": False, "error": str(exc), "error_type": "connection"}

    def has_valid_license_for_download(self) -> bool:
        status = self.check_license()
        return status.get("is_valid", False) and status.get("days_left", 0) > 0

    def clear_cache(self) -> dict:
        _log("Clearing local license cache", "info")
        self._clear_json_cache(LICENSE_CACHE_FILE)
        self._clear_json_cache(TRIAL_CACHE_FILE)
        self._license_cache = None
        self._trial_cache = None
        return {"success": True, "message": "Cache cleared"}

    def reload(self):
        self._license_cache = None
        self._trial_cache = None

    def get_device_id(self) -> str:
        return self._device_id


_service: Optional[WSDLicenseService] = None


def get_license_service() -> WSDLicenseService:
    global _service
    if _service is None:
        _service = WSDLicenseService()
    return _service


def reload_license_service() -> None:
    global _service
    if _service is not None:
        _service.reload()
    else:
        _service = WSDLicenseService()


def check_license_status() -> dict:
    return get_license_service().check_license()


def activate_license(name: str, email: str, license_key: str) -> dict:
    return get_license_service().activate_license(name, email, license_key)


def clear_license_cache() -> dict:
    return get_license_service().clear_cache()


def can_start_download() -> bool:
    return get_license_service().has_valid_license_for_download()


def get_license_badge_info() -> dict:
    return get_license_service().get_badge_info()


def start_trial() -> dict:
    return get_license_service().start_trial()
