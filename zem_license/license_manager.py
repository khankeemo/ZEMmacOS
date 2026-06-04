# zem_license/license_manager.py
"""
Encrypted temporary cache for signed backend responses.

NOT AUTHORITATIVE — server controls all licensing decisions.
Cache uses hardware-derived encryption (no master.key in client builds).
"""

import os
import sys
import json
import base64
import hashlib
import shutil
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from hardware_id import HardwareID

CACHE_FILE_NAME = "license_cache.lic"
CACHE_SALT = b"ZEMmacOS_Cache_Salt_v3_2024"
MAX_OFFLINE_HOURS = 72


def get_app_directory() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR


def _derive_cache_key(hardware_id: str) -> bytes:
    material = (hardware_id + CACHE_SALT.decode()).encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", material, CACHE_SALT, 100000, 32)
    return base64.urlsafe_b64encode(derived)


def get_cache_file_path(filename: str = None) -> str:
    app_dir = get_app_directory()
    name = filename or CACHE_FILE_NAME
    return os.path.join(app_dir, name)


def _parse_grace_until(payload: dict) -> Optional[datetime]:
    grace = payload.get("offline_grace_until") or payload.get("offline_grace_until_iso")
    if not grace:
        return None
    try:
        dt = datetime.fromisoformat(grace.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _is_grace_valid(payload: dict) -> bool:
    grace_end = _parse_grace_until(payload)
    if not grace_end:
        return False
    return datetime.now(timezone.utc) < grace_end


def save_signed_cache(server_payload: dict, filename: str = None) -> dict:
    """
    Save server-signed response for temporary offline grace.
    Only call after successful online validation/activation.
    """
    hw = HardwareID.generate_stable_id().upper()
    cache_body = {
        "version": 3,
        "hardware_id": hw,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "server_payload": server_payload,
        "access_token": server_payload.get("access_token"),
        "offline_grace_until": server_payload.get("offline_grace_until"),
        "license_key": server_payload.get("license_key", ""),
        "customer_name": server_payload.get("customer_name", ""),
        "customer_email": server_payload.get("customer_email", ""),
        "license_type": server_payload.get("license_type", ""),
        "days_left": server_payload.get("days_left", 0),
        "expiry_date": server_payload.get("expiry_date"),
        "valid": server_payload.get("valid", False),
    }

    try:
        key = _derive_cache_key(hw)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(json.dumps(cache_body).encode("utf-8"))
        content = base64.urlsafe_b64encode(encrypted).decode("ascii")
        path = get_cache_file_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "message": "Signed cache saved"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_cached_license(license_path: str = None) -> dict:
    """
    Read encrypted cache. Valid only if:
    - decrypts on this hardware
    - server marked valid
    - offline grace window not expired
    """
    hw = HardwareID.generate_stable_id().upper()
    path = license_path or get_cache_file_path()

    if not os.path.exists(path):
        return {"valid": False, "error": "No license cache", "error_type": "not_found"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        key = _derive_cache_key(hw)
        decrypted = Fernet(key).decrypt(base64.urlsafe_b64decode(raw))
        data = json.loads(decrypted.decode("utf-8"))

        if data.get("hardware_id", "").upper() != hw:
            return {
                "valid": False,
                "error": "Hardware mismatch — cache invalid",
                "error_type": "hardware_mismatch",
            }

        payload = data.get("server_payload", data)
        if not payload.get("valid"):
            return {
                "valid": False,
                "error": "Cached license marked invalid by server",
                "error_type": "revoked",
                "data": data,
            }

        if not _is_grace_valid(payload):
            return {
                "valid": False,
                "error": "Offline grace expired — connect to license server",
                "error_type": "grace_expired",
                "data": data,
            }

        days_left = payload.get("days_left", 0)
        if days_left <= 0 and payload.get("license_type") == "paid":
            return {
                "valid": False,
                "error": "License expired",
                "error_type": "expired",
                "data": data,
                "days_left": 0,
            }

        return {
            "valid": True,
            "data": data,
            "days_left": days_left,
            "source": "cache_offline_grace",
            "offline_grace_until": payload.get("offline_grace_until"),
            "access_token": payload.get("access_token"),
        }

    except Exception as exc:
        return {"valid": False, "error": f"Cache corrupt: {exc}", "error_type": "corrupt"}


def remove_cached_license(license_path: str = None) -> dict:
    path = license_path or get_cache_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            return {"success": True, "message": "Cache removed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": True, "message": "No cache to remove"}


def cache_exists() -> bool:
    return os.path.exists(get_cache_file_path())


def get_cache_info() -> dict:
    path = get_cache_file_path()
    if not os.path.exists(path):
        return {"exists": False}
    stat = os.stat(path)
    return {
        "exists": True,
        "path": path,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def backup_cached_license(destination_dir: str = None) -> dict:
    path = get_cache_file_path()
    if not os.path.exists(path):
        return {"success": False, "error": "No cache found"}
    dest = destination_dir or os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(dest, exist_ok=True)
    backup = os.path.join(dest, f"license_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.lic")
    shutil.copy2(path, backup)
    return {"success": True, "path": backup}


# Legacy aliases for UI compatibility
def save_cached_license(license_data: dict, filename: str = None) -> dict:
    """Accept server payload or wrap legacy dict."""
    if "server_payload" in license_data or "offline_grace_until" in license_data:
        return save_signed_cache(license_data, filename)
    return save_signed_cache(
        {
            "valid": True,
            "license_type": license_data.get("license_type", "paid"),
            "customer_name": license_data.get("customer_name", ""),
            "customer_email": license_data.get("customer_email", ""),
            "license_key": license_data.get("license_key", ""),
            "days_left": license_data.get("days_left", 0),
            "expiry_date": license_data.get("expiry_date"),
            "offline_grace_until": license_data.get("offline_grace_until"),
            "access_token": license_data.get("access_token"),
        },
        filename,
    )


def find_license_files() -> list:
    app_dir = get_app_directory()
    return [os.path.join(app_dir, f) for f in os.listdir(app_dir) if f.endswith(".lic")]


def get_license_details() -> dict:
    result = get_cached_license()
    if not result.get("valid"):
        return {"exists": False, "error": result.get("error")}
    data = result.get("data", {})
    sp = data.get("server_payload", data)
    return {
        "exists": True,
        "customer_name": sp.get("customer_name", "N/A"),
        "customer_email": sp.get("customer_email", "N/A"),
        "license_key": sp.get("license_key", "N/A"),
        "days_left": result.get("days_left", 0),
        "status": "Active" if result.get("valid") else "Expired",
        "hardware_id": data.get("hardware_id", "N/A"),
        "source": result.get("source", "cache"),
    }


def validate_license(license_file: str = None) -> dict:
    return get_cached_license(license_file)


def get_license_status() -> dict:
    r = get_cached_license()
    if r.get("valid"):
        d = r.get("days_left", 0)
        return {"status": f"✓ Offline grace: {d} days", "is_valid": True, "days_left": d}
    return {"status": f"✗ {r.get('error')}", "is_valid": False, "error": r.get("error")}
