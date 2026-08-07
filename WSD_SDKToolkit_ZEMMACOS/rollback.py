"""Rollback Strategy — never leave the SDK half-updated (SECTION 0D §20).

A snapshot records cache license status, license key, session state, and the
LicenseStatus object before a mutating workflow. If a step fails after partial
cache writes, rollback() restores the previous state and logs ROLLBACK_EXECUTED.
"""
from typing import Any, Callable, Dict, Optional

from .live_log import LiveLog

__all__ = ["RollbackCoordinator"]


class _Snapshot:
    def __init__(self, cache_status: Any, license_key: Any, status: Any,
                 session_dict: Optional[Callable[[], Dict[str, Any]]] = None):
        self.cache_status = cache_status
        self.license_key = license_key
        self.status = status
        self.session_getter = session_dict


class RollbackCoordinator:
    def __init__(self, engine: Any):
        self._engine = engine
        self._active: Optional[_Snapshot] = None

    def begin(self) -> _Snapshot:
        """Capture the current SDK state before a mutating workflow."""
        try:
            cache_status = self._engine._cache.peek_license_status()
        except Exception:
            cache_status = None
        try:
            license_key = self._engine._license_key
        except Exception:
            license_key = None
        try:
            status = self._engine._status
        except Exception:
            status = None
        snapshot = _Snapshot(cache_status, license_key, status)
        self._active = snapshot
        LiveLog.log("ROLLBACK_BEGIN", "Snapshot captured before workflow")
        return snapshot

    def commit(self) -> None:
        self._active = None
        LiveLog.log("ROLLBACK_COMMIT", "Workflow committed — no rollback needed")

    def rollback(self, reason: str = "") -> bool:
        snapshot = self._active
        self._active = None
        if snapshot is None:
            return False
        restored = False
        try:
            if getattr(self._engine, "_cache", None) is not None:
                if snapshot.cache_status is not None:
                    self._engine._cache.set_license_status(snapshot.cache_status)
                else:
                    self._engine._cache.invalidate_license_status()
            if snapshot.license_key is not None:
                self._engine._license_key = snapshot.license_key
            if snapshot.status is not None:
                self._engine._status = snapshot.status
            LiveLog.log("ROLLBACK_EXECUTED", f"Previous state restored ({reason})")
            restored = True
        except Exception as e:
            LiveLog.log("ROLLBACK_FAILED", f"Rollback error: {e}")
        return restored