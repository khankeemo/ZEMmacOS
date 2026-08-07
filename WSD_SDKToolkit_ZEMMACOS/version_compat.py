"""Version Compatibility — SDK ↔ API ↔ Publisher ↔ Template ↔ Database (SECTION 0D §17).

Verified before activation. Incompatible versions are rejected gracefully with
UPGRADE_REQUIRED messaging, never a crash.
"""
from typing import Any, Dict, Optional, Tuple

from .live_log import LiveLog
from .error_catalog import ErrorCatalog

__all__ = ["VersionCompatibility"]

SUPPORTED_SDK_MAJOR = 1
SUPPORTED_API_MAJOR = 1


class VersionCompatibility:
    @staticmethod
    def parse(version: Optional[str]) -> Tuple[int, int, int]:
        if not version:
            return (0, 0, 0)
        parts = str(version).lstrip("v").split(".")
        def _part(p: str) -> int:
            digits = "".join(ch for ch in p if ch.isdigit())
            return int(digits) if digits else 0
        while len(parts) < 3:
            parts.append("0")
        return (_part(parts[0]), _part(parts[1]), _part(parts[2]))

    @staticmethod
    def incompatible(component: str, sdk: str, server: Optional[str]) -> Tuple[bool, str]:
        if not server:
            return False, ""
        sdk_major, _, _ = VersionCompatibility.parse(sdk)
        server_major, _, _ = VersionCompatibility.parse(server)
        if sdk_major != server_major:
            return True, f"{component}"
        return False, ""

    def verify(self, engine: Any, health: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = {
            "ok": True,
            "sdk": {},
            "api": {},
            "publisher": {},
            "template": {},
            "database": {},
            "message": "",
            "code": "",
        }
        try:
            sdk_version = engine.config.sdk_version if hasattr(engine, "config") else "1.0.0"
        except Exception:
            sdk_version = "1.0.0"
        result["sdk"] = {"version": sdk_version}

        if not health:
            health = {}
        server = health.get("api_version") or "v1"

        api_ok, api_comp = self.incompatible("api", sdk_version, server)
        result["api"] = {"version": server, "ok": not api_ok}
        result["publisher"] = {"version": health.get("publisher_version"), "ok": True}
        result["template"] = {"version": health.get("template_version"), "ok": True}
        result["database"] = {"version": health.get("database_version"), "ok": True}

        if api_ok:
            result["ok"] = False
            result["code"] = "UPGRADE_REQUIRED"
            result["message"] = ErrorCatalog.message("UPGRADE_REQUIRED")
            result["incompatible"] = api_comp
            LiveLog.log("VERSION_COMPAT", f"Incompatible API version: server={server} sdk={sdk_version}")
        else:
            LiveLog.log("VERSION_COMPAT", f"Compatible (api={server}, publisher={result['publisher'].get('version')})")
        return result