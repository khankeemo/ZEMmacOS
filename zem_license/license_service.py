# zem_license/license_service.py
"""
License Service — API client only (non-authoritative desktop controller).

Priority:
1. Backend API validation (AUTHORITATIVE when reachable)
2. Signed encrypted cache (temporary offline grace ONLY)
3. Trial via backend API
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from hardware_id import HardwareID
from zem_license.api_client import get_api_client, set_license_log_callback
from zem_license.license_manager import (
    get_cached_license,
    remove_cached_license,
    save_signed_cache,
)
from zem_license.trial_manager import get_trial_manager


class LicenseService:
    """Desktop license controller — delegates all decisions to ZEM API."""

    def __init__(self):
        self.trial_manager = get_trial_manager()
        self.hardware_id = HardwareID.generate_stable_id()
        self.api = get_api_client()
        self._api_available = None
        self._console = None

    def attach_console(self, safe_console) -> None:
        """Wire real-time license logs to safe_console."""
        self._console = safe_console

        def _log(msg: str, level: str = "info"):
            if safe_console and safe_console.is_valid():
                safe_console.append(f"[License] {msg}", level)

        set_license_log_callback(_log)

    def _log(self, message: str, level: str = "info") -> None:
        if self._console and self._console.is_valid():
            self._console.append(f"[License] {message}", level)

    def _check_api_health(self) -> bool:
        if self._api_available is not None:
            return self._api_available
        result = self.api.health_check()
        self._api_available = result.get("status") == "ok" or result.get("api_available")
        if self._api_available:
            self._log("Backend connection OK", "success")
        else:
            self._log(f"Backend unavailable: {result.get('error', 'unknown')}", "warning")
        return self._api_available

    def _invalidate_cache(self) -> None:
        remove_cached_license()
        self._log("Cache invalidated (server rejection or revocation)", "warning")

    def _status_from_api(self, api_result: dict, license_type: str = "paid") -> dict:
        valid = api_result.get("valid", False) or api_result.get("success", False)
        days_left = api_result.get("days_left", 0)

        if valid and license_type == "paid":
            save_signed_cache(api_result)
            self._log("Token/cache refreshed from server", "success")

        return {
            "is_valid": valid,
            "is_trial": license_type == "trial",
            "license_type": license_type if valid else "none",
            "status": api_result.get("status") or ("licensed" if valid else "blocked"),
            "days_left": days_left,
            "customer_name": api_result.get("customer_name", ""),
            "customer_email": api_result.get("customer_email", ""),
            "source": "api",
            "message": api_result.get("message") or api_result.get("error", ""),
            "error_type": api_result.get("error_type", ""),
            "latency_ms": api_result.get("latency_ms"),
        }

    def _offline_grace_status(self) -> dict:
        cached = get_cached_license()
        if not cached.get("valid"):
            self._log(f"Cache fallback failed: {cached.get('error')}", "warning")
            return None

        data = cached.get("data", {})
        sp = data.get("server_payload", data)
        self._log(
            f"Offline grace active until {cached.get('offline_grace_until', 'unknown')}",
            "warning",
        )
        return {
            "is_valid": True,
            "is_trial": sp.get("license_type") == "trial",
            "license_type": sp.get("license_type", "paid"),
            "status": "licensed" if sp.get("license_type") == "paid" else "trial",
            "days_left": cached.get("days_left", sp.get("days_left", 0)),
            "customer_name": sp.get("customer_name", ""),
            "customer_email": sp.get("customer_email", ""),
            "source": "cache_offline_grace",
            "message": f"Offline grace mode. {cached.get('days_left', 0)} days remaining.",
        }

    def get_hardware_id(self) -> str:
        return self.hardware_id

    def check_license(self) -> dict:
        """Internet-first license check."""
        self._check_api_health()

        # Trial first when no paid credentials in cache
        trial_api = self.trial_manager.check_via_api()
        if trial_api and trial_api.get("is_valid"):
            return trial_api

        cached = get_cached_license()
        license_key = None
        name = None
        email = None

        if cached.get("valid"):
            sp = cached.get("data", {}).get("server_payload", cached.get("data", {}))
            license_key = sp.get("license_key")
            name = sp.get("customer_name")
            email = sp.get("customer_email")

        if license_key and name and email:
            api_result = self.api.validate_license(name, email, license_key, self.hardware_id)
            if api_result.get("api_available", True) and "connection" not in api_result.get("error_type", ""):
                if api_result.get("valid"):
                    return self._status_from_api(api_result, "paid")
                error_type = api_result.get("error_type", "")
                if error_type in ("hardware_mismatch", "expired", "inactive", "revoked", "device_limit"):
                    self._invalidate_cache()
                    self._log(f"Revocation/invalid detected: {api_result.get('error')}", "error")
                    return self._status_from_api(api_result, "paid") | {"is_valid": False, "status": "blocked"}

        offline = self._offline_grace_status()
        if offline:
            return offline

        trial_local = self.trial_manager.get_local_fallback_status()
        if trial_local:
            return trial_local

        health = self.api.health_check()
        if health.get("error_type") == "connection":
            return {
                "is_valid": False,
                "is_trial": False,
                "license_type": "none",
                "status": "blocked",
                "days_left": 0,
                "message": health.get("error", "License server is not running"),
                "error_type": "connection",
            }

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
                return {"text": f"⚠️ License expires in {days} days", "color_key": "warning"}
            return {"text": "✓ Licensed", "color_key": "success"}
        if status.get("license_type") == "trial" and status.get("is_valid"):
            days = status.get("days_left", 0)
            return {"text": f"🧪 Trial • {days} days left", "color_key": "warning"}
        if status.get("status") == "expired":
            return {"text": "⚠️ Trial Expired", "color_key": "error"}
        return {"text": "✗ License Required", "color_key": "error"}

    def start_trial(self) -> dict:
        return self.trial_manager.start_trial()

    def activate_license(self, name: str, email: str, license_key: str) -> dict:
        normalized_name = name.strip()
        normalized_email = email.strip().lower()
        normalized_key = license_key.strip().upper()

        self._log("Activating license via API...", "info")
        result = self.api.activate_license(
            normalized_name, normalized_email, normalized_key, self.hardware_id
        )

        if result.get("success") or result.get("valid"):
            self.trial_manager.end_trial()
            save_signed_cache(result)
            self._log("Activation successful", "success")
            return {
                "success": True,
                "message": result.get("message", "License activated"),
                "days_left": result.get("days_left", 0),
                "expiry_date": result.get("expiry_date"),
            }

        self._log(f"Activation failed: {result.get('error')}", "error")
        return {
            "success": False,
            "error": result.get("error", "Activation failed"),
            "error_type": result.get("error_type", "unknown"),
        }

    def activate_license_with_google(self, name: str, email: str, license_key: str) -> dict:
        return self.activate_license(name, email, license_key)

    def clear_cache(self) -> dict:
        self._log("Clearing local license cache", "info")
        return remove_cached_license()

    def clear_local_cache(self) -> dict:
        return self.clear_cache()

    def reload(self):
        self._api_available = None
        self.trial_manager.clear_cache()

    def has_valid_license_for_download(self) -> bool:
        status = self.check_license()
        return status.get("is_valid", False) and status.get("days_left", 0) > 0


_license_service = None


def get_license_service() -> LicenseService:
    global _license_service
    if _license_service is None:
        _license_service = LicenseService()
    return _license_service


def reload_license_service() -> None:
    global _license_service
    if _license_service is not None:
        _license_service.reload()
    else:
        _license_service = LicenseService()


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
