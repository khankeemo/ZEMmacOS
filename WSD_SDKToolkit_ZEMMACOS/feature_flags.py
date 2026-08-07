"""Global Feature Flags — server-driven, never hardcoded (SECTION 0D §4).

Defaults are production-safe. When reachable, /api/v1/health (or config) supplies
server values that win. Server values can be persisted to cache so they survive
restarts and offline use; the offline message queue is always preserved.
"""
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["FeatureFlags"]

DEFAULT_FLAGS: Dict[str, bool] = {
    "allow_activation": True,
    "allow_trial": True,
    "allow_renewal": True,
    "allow_reactivation": True,
    "allow_hardware_reset": False,
    "allow_offline_mode": True,
    "allow_device_replacement": False,
    "allow_communication": True,
    "allow_upgrade": True,
}

CACHE_KEY = "feature_flags"


class FeatureFlags:
    def __init__(self, cache: Any = None):
        self._flags = dict(DEFAULT_FLAGS)
        self._cache = cache
        if cache is not None:
            self._restore()

    def _restore(self) -> None:
        try:
            saved = self._cache.get(CACHE_KEY)
            if isinstance(saved, dict):
                for key, value in saved.items():
                    if key in DEFAULT_FLAGS:
                        self._flags[key] = bool(value)
        except Exception:
            pass

    # ====================================================================
    # Reads / writes
    # ====================================================================

    def is_enabled(self, name: str, default: bool = False) -> bool:
        if name in self._flags:
            return bool(self._flags[name])
        return default

    def enabled(self) -> Dict[str, bool]:
        return dict(self._flags)

    def set_flag(self, name: str, value: bool) -> None:
        if name in DEFAULT_FLAGS:
            self._flags[name] = bool(value)
            self._persist()

    def apply_server_payload(self, payload: Optional[Dict[str, Any]]) -> bool:
        """Merge server-provided flag values; server wins. Returns True if changed."""
        if not payload:
            return False
        changed = False
        for key, value in payload.items():
            flag = key
            if key.startswith("allow_"):
                flag = key
            for candidate in (key, f"allow_{key}"):
                if candidate in DEFAULT_FLAGS:
                    flag = candidate
                    break
            if flag in DEFAULT_FLAGS:
                new_value = bool(value)
                if self._flags[flag] != new_value:
                    self._flags[flag] = new_value
                    changed = True
        if changed:
            self._persist()
            LiveLog.log("FEATURE_FLAGS", "Server feature flags applied")
        return changed

    def _persist(self) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(CACHE_KEY, dict(self._flags))
        except Exception:
            pass

    def report(self) -> Dict[str, bool]:
        return dict(self._flags)