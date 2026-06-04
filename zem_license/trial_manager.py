# zem_license/trial_manager.py
"""
Trial Manager — server authoritative.

Local storage only holds signed server trial token for offline grace display.
Trial eligibility, expiry, and anti-abuse are enforced by ZEM API.
"""

import os
import sys
import json
import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from hardware_id import HardwareID

from zem_license.api_client import get_api_client
from zem_license.license_manager import save_signed_cache

TRIAL_CACHE_FILE = ".trial_token"
TRIAL_SALT = b"ZEMmacOS_Trial_Token_v3"


class TrialManager:
    def __init__(self):
        self.hardware_id = HardwareID.generate_stable_id()
        self.api = get_api_client()
        self.storage_path = self._storage_path()
        self._cached_status = None

    def _storage_path(self) -> Path:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            app_dir = os.path.join(base, "ZEMmacOS")
        else:
            app_dir = os.path.expanduser("~/.zemmacos")
        os.makedirs(app_dir, exist_ok=True)
        return Path(app_dir) / TRIAL_CACHE_FILE

    def _derive_key(self) -> bytes:
        material = (self.hardware_id + TRIAL_SALT.decode()).encode()
        derived = hashlib.pbkdf2_hmac("sha256", material, TRIAL_SALT, 100000, 32)
        return base64.urlsafe_b64encode(derived)

    def _save_token(self, payload: dict) -> None:
        data = {"hardware_id": self.hardware_id.upper(), "server_payload": payload}
        encrypted = Fernet(self._derive_key()).encrypt(json.dumps(data).encode())
        self.storage_path.write_bytes(encrypted)

    def _load_token(self) -> dict:
        if not self.storage_path.exists():
            return {}
        try:
            raw = Fernet(self._derive_key()).decrypt(self.storage_path.read_bytes())
            return json.loads(raw.decode())
        except Exception:
            return {}

    def start_trial(self) -> dict:
        result = self.api.start_trial(self.hardware_id)
        if result.get("success") or result.get("valid"):
            save_signed_cache(result)
            self._save_token(result)
            self._cached_status = None
            return {
                "success": True,
                "message": result.get("message", "Trial started"),
                "days_remaining": result.get("days_remaining", result.get("days_left", 7)),
            }
        return {
            "success": False,
            "message": result.get("message") or result.get("error", "Trial unavailable"),
            "is_active": result.get("is_active", False),
            "trial_expired": result.get("trial_expired", False),
            "days_remaining": 0,
        }

    def check_via_api(self) -> dict:
        """Authoritative trial check from server."""
        self._cached_status = None
        result = self.api.trial_status(self.hardware_id)
        if result.get("valid") and (result.get("license_type") == "trial" or result.get("days_left", 0) > 0):
            result["license_type"] = "trial"
            save_signed_cache(result)
            self._save_token(result)
            return {
                "is_valid": True,
                "is_trial": True,
                "license_type": "trial",
                "status": "trial",
                "days_left": result.get("days_left", 0),
                "message": result.get("message", ""),
                "source": "api",
            }
        return None

    def get_local_fallback_status(self) -> dict:
        """Offline display only — grace window from signed token."""
        stored = self._load_token()
        payload = stored.get("server_payload", {})
        if not payload.get("valid"):
            return None
        grace = payload.get("offline_grace_until")
        if grace:
            try:
                end = datetime.fromisoformat(grace.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= end:
                    return None
            except ValueError:
                return None
        days = payload.get("days_left", 0)
        if days <= 0:
            return None
        return {
            "is_valid": True,
            "is_trial": True,
            "license_type": "trial",
            "status": "trial",
            "days_left": days,
            "source": "trial_cache_offline",
            "message": f"Trial (offline grace). {days} days remaining.",
        }

    def is_trial_valid(self) -> bool:
        api_status = self.check_via_api()
        if api_status and api_status.get("is_valid"):
            return True
        local = self.get_local_fallback_status()
        return local is not None and local.get("is_valid", False)

    def get_days_remaining(self) -> int:
        api_status = self.check_via_api()
        if api_status:
            return api_status.get("days_left", 0)
        local = self.get_local_fallback_status()
        return local.get("days_left", 0) if local else 0

    def get_trial_info(self) -> dict:
        api_status = self.check_via_api()
        if api_status:
            return {
                "exists": True,
                "is_active": True,
                "days_remaining": api_status.get("days_left", 0),
            }
        local = self.get_local_fallback_status()
        if local:
            return {"exists": True, "is_active": True, "days_remaining": local.get("days_left", 0)}
        return {"exists": False, "is_active": False, "message": "No trial"}

    def end_trial(self) -> dict:
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
            self._cached_status = None
            return {"success": True, "message": "Trial token cleared"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def clear_cache(self):
        self._cached_status = None

    def trial_exists(self) -> bool:
        return self.storage_path.exists()


_trial_manager = None


def get_trial_manager() -> TrialManager:
    global _trial_manager
    if _trial_manager is None:
        _trial_manager = TrialManager()
    return _trial_manager


def check_trial_mode() -> dict:
    m = get_trial_manager()
    if m.is_trial_valid():
        return {"valid": True, "is_trial": True, "days_remaining": m.get_days_remaining()}
    return {"valid": False, "is_trial": False}


def start_trial_mode() -> bool:
    return get_trial_manager().start_trial().get("success", False)


def get_trial_days_remaining() -> int:
    return get_trial_manager().get_days_remaining()
