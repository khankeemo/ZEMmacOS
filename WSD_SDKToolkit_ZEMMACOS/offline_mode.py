"""Universal Offline Mode — full offline lifecycle (SECTION 0D §5).

States: normal -> offline -> cached -> grace_period -> reconnecting -> back_online.

The backend remains the single source of truth (SECTION 0B Rule 1); the cached
license is only an absent-optional fallback during a genuine outage. Every state is
written to LiveLog and published on the workflow.state channel so the ULC renders
it clearly.
"""
import time
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["OfflineMode"]

STATE_NORMAL = "normal"
STATE_OFFLINE = "offline"
STATE_CACHED = "cached"
STATE_GRACE = "grace_period"
STATE_RECONNECTING = "reconnecting"
STATE_BACK_ONLINE = "back_online"


class OfflineMode:
    def __init__(self, grace_days: int = 7):
        self._state = STATE_NORMAL
        self._grace_days = int(grace_days or 7)
        self._offline_since: Optional[float] = None

    # ====================================================================
    # State
    # ====================================================================

    def set_state(self, state: str, detail: str = "") -> str:
        if state == self._state and not detail:
            return state
        self._state = state
        if state == STATE_OFFLINE:
            self._offline_since = self._offline_since or time.time()
        else:
            self._offline_since = None
        label = f"{state} — {detail}" if detail else state
        try:
            from .workflow_progress import GlobalStateMachine
            GlobalStateMachine.set("PROCESSING" if state not in (STATE_NORMAL,) else "IDLE", detail)
        except Exception:
            pass
        LiveLog.log("OFFLINE_STATE", label)
        return state

    @property
    def state(self) -> str:
        return self._state

    def is_offline(self) -> bool:
        return self._state in (STATE_OFFLINE, STATE_CACHED, STATE_GRACE, STATE_RECONNECTING)

    def is_online(self) -> bool:
        return not self.is_offline()

    def seconds_since_offline(self) -> int:
        if self._offline_since is None:
            return 0
        return int(time.time() - self._offline_since)

    def days_since_offline(self) -> float:
        return self.seconds_since_offline() / (24 * 3600.0)

    def in_grace_period(self) -> bool:
        if not self.is_offline():
            return False
        return self.days_since_offline() <= self._grace_days

    # ====================================================================
    # Lifecycle helpers (called by the engine)
    # ====================================================================

    def server_reachable(self, has_valid_cache: bool = False) -> None:
        """Backend responded (refresh / initialize succeeded)."""
        if self._state == STATE_BACK_ONLINE:
            self.set_state(STATE_NORMAL, "fully restored")
        elif self._state == STATE_NORMAL:
            pass
        else:
            self.set_state(STATE_BACK_ONLINE, "reconnected — status refreshed")

    def server_lost(self, has_valid_cache: bool = False) -> str:
        """Backend unreachable. Choose the clearest offline sub-state."""
        if not has_valid_cache:
            self.set_state(STATE_OFFLINE, "no cached license available")
        elif self.in_grace_period():
            days = self._grace_days - int(self.days_since_offline())
            self.set_state(STATE_GRACE, f"cached license active ({max(0, days)} day(s) of grace)")
        else:
            self.set_state(STATE_OFFLINE, "grace period exceeded")
        return self._state

    def describe(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "offline": self.is_offline(),
            "in_grace_period": self.in_grace_period(),
            "grace_days": self._grace_days,
            "seconds_since_offline": self.seconds_since_offline(),
            "days_since_offline": round(self.days_since_offline(), 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.describe()