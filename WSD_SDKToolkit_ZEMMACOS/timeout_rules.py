"""Global Timeout Rules — single source for every timeout value (SECTION 0D §7).

API, OTP, retry, poll, and offline-grace timeouts come from here, never hardcoded
in the engine, client, or UI. Values may be overridden by api-config.json.
"""
import time
from typing import Any, Dict, Optional

__all__ = ["TimeoutRules"]

DEFAULTS = {
    "api_timeout_ms": 30000,
    "otp_ttl_seconds": 300,
    "retry_delay_seconds": 60,
    "poll_interval_ms": 2000,
    "health_timeout_ms": 5000,
    "offline_grace_days": 7,
}


class TimeoutRules:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._values = dict(DEFAULTS)
        self._apply_config(config or {})

    def _apply_config(self, config: Dict[str, Any]) -> None:
        api = config.get("api", {}) or {}
        offline = config.get("offline", {}) or {}
        timeouts = config.get("timeouts", {}) or {}
        if api.get("timeout") is not None:
            self._values["api_timeout_ms"] = float(api["timeout"])
        if offline.get("cache_days") is not None:
            self._values["offline_grace_days"] = int(offline["cache_days"])
        if offline.get("grace_days") is not None:
            self._values["offline_grace_days"] = int(offline["grace_days"])
        for key, value in timeouts.items():
            if key in self._values and value is not None:
                self._values[key] = value

    def get(self, name: str) -> float:
        return float(self._values.get(name, DEFAULTS.get(name, 0)))

    @property
    def api_timeout_ms(self) -> float:
        return self.get("api_timeout_ms")

    @property
    def api_timeout_seconds(self) -> float:
        return self.api_timeout_ms / 1000.0

    @property
    def otp_ttl_seconds(self) -> int:
        return int(self.get("otp_ttl_seconds"))

    @property
    def retry_delay_seconds(self) -> int:
        return int(self.get("retry_delay_seconds"))

    @property
    def poll_interval_ms(self) -> int:
        return int(self.get("poll_interval_ms"))

    @property
    def health_timeout_seconds(self) -> float:
        return self.get("health_timeout_ms") / 1000.0

    @property
    def offline_grace_days(self) -> int:
        return int(self.get("offline_grace_days"))

    def snapshot(self) -> Dict[str, float]:
        return dict(self._values)
