"""Health Check API — verify backend health before major workflows (SECTION 0D §15).

Calls GET /api/v1/health (transport-only via the client) and caches the result for
the poll interval. If the server is unhealthy, activation / renewal / trial are
blocked with a clear message.
"""
import time
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["HealthCheck"]


class HealthCheck:
    def __init__(self, engine: Any, poll_interval_ms: int = 2000, timeout_s: float = 5.0):
        self._engine = engine
        self._poll_interval = poll_interval_ms / 1000.0
        self._timeout = timeout_s
        self._last: Dict[str, Any] = {}
        self._last_checked_at: float = 0.0
        self._in_flight: Optional[Dict[str, Any]] = None

    @property
    def is_healthy(self) -> bool:
        self.check_if_stale()
        return bool(self._last.get("status") == "ok")

    def _stale(self) -> bool:
        return (time.time() - self._last_checked_at) > self._poll_interval

    def check_if_stale(self) -> Dict[str, Any]:
        if self._stale():
            return self.check()
        return self._last

    def check(self, force: bool = False) -> Dict[str, Any]:
        if not force and not self._stale() and self._last:
            return self._last
        try:
            result = self._engine.get_health()
        except Exception as e:
            result = {"status": "error", "error": str(e), "tests": {}}
        self._last = result
        self._last_checked_at = time.time()
        if not result.get("status") == "ok":
            LiveLog.log("HEALTH_CHECK", f"Backend unhealthy: {result.get('status')}")
        return result