"""Universal Metrics — activation/renewal/OTP/rebind/conversion telemetry (SECTION 0D §16).

Records success/failure counters and average response times per event so issues can
be detected early. Written to LiveLog and available to the ULC debug view.
"""
import time
from threading import RLock
from typing import Any, Dict, Optional

__all__ = ["MetricsCollector"]

VALID_EVENTS = (
    "activation", "renewal", "otp", "hardware_rebind",
    "trial_conversion", "refresh", "communication",
)


class MetricsCollector:
    def __init__(self):
        self._lock = RLock()
        self._counters: Dict[str, Dict[str, int]] = {}
        self._durations: Dict[str, Dict[str, float]] = {}
        self._timers: Dict[str, float] = {}

    def _bucket(self, name: str) -> Dict[str, int]:
        if name not in self._counters:
            self._counters[name] = {"success": 0, "failure": 0, "total": 0}
        return self._counters[name]

    def _durations_bucket(self, name: str) -> Dict[str, float]:
        if name not in self._durations:
            self._durations[name] = {"sum_ms": 0.0, "count": 0}
        return self._durations[name]

    def start_timer(self, name: str) -> None:
        if name not in VALID_EVENTS:
            name = "activation"
        with self._lock:
            self._timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        if name not in VALID_EVENTS:
            name = "activation"
        with self._lock:
            started = self._timers.pop(name, None)
            if started is None:
                return 0.0
            return (time.time() - started) * 1000.0

    def record(self, name: str, success: bool, duration_ms: Optional[float] = None) -> None:
        if name not in VALID_EVENTS:
            name = "activation"
        with self._lock:
            bucket = self._bucket(name)
            bucket["total"] += 1
            bucket["success" if success else "failure"] += 1
            if duration_ms is not None:
                db = self._durations_bucket(name)
                db["sum_ms"] += duration_ms
                db["count"] += 1

    def record_success(self, name: str, duration_ms: Optional[float] = None) -> None:
        self.record(name, True, duration_ms)

    def record_failure(self, name: str, duration_ms: Optional[float] = None) -> None:
        self.record(name, False, duration_ms)

    def average_response_time(self, name: str) -> float:
        with self._lock:
            db = self._durations_bucket(name)
            if db["count"] == 0:
                return 0.0
            return db["sum_ms"] / db["count"]

    def report(self) -> Dict[str, Any]:
        with self._lock:
            report: Dict[str, Any] = {}
            for name, bucket in sorted(self._counters.items()):
                report[name] = {
                    "success": bucket["success"],
                    "failure": bucket["failure"],
                    "total": bucket["total"],
                    "avg_response_time_ms": round(self.average_response_time(name), 2),
                }
            return report

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._durations.clear()
            self._timers.clear()
