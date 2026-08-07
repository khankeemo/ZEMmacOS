"""WorkflowProgress — one canonical progress pipeline shared by every workflow.

Every long-running operation (validation, OTP, activation, renewal, trial,
refresh, hardware rebind) reports through the same ordered stage list. The UI
subscribes once and renders stages; no dialog hard-codes its own strings.

Stages are emitted in order; every workflow may skip stages but never invents
new ones. ``stage()`` also forwards to the shared LiveLog so UI and log stay
in sync (AWS-01 Rules 4 & 9).
"""
import time
from typing import Any, Callable, Optional

from .live_log import LiveLog


class GlobalStateMachine:
    """Canonical workflow lifecycle state machine (LOCKED spec §3).

    Every workflow follows the identical lifecycle and may never invent a
    custom state:
        IDLE → VALIDATING → OTP_SENT → OTP_VERIFIED → PROCESSING → REFRESHING
               → COMPLETED
        Failure path (any point): FAILED

    The engine is the only emitter; UI reads the current state. A state change
    is written to LiveLog and published on the generic EventBus channel
    ``workflow.state``. The atomicity (one workflow at a time) is enforced by
    the engine's RLock, not here.
    """

    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    OTP_SENT = "OTP_SENT"
    OTP_VERIFIED = "OTP_VERIFIED"
    PROCESSING = "PROCESSING"
    REFRESHING = "REFRESHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    _state = IDLE

    @classmethod
    def set(cls, state: str, detail: str = "") -> str:
        cls._state = state
        try:
            from .event_bus import EventBus
            EventBus.emit("workflow.state", state, detail)
        except Exception:
            pass
        if detail:
            LiveLog.log("WORKFLOW_STATE", f"{state} — {detail}")
        else:
            LiveLog.log("WORKFLOW_STATE", state)
        return state

    @classmethod
    def get(cls) -> str:
        return cls._state

    @classmethod
    def reset(cls) -> None:
        cls._state = cls.IDLE


class WorkflowProgress:
    """Singleton progress reporter.

    ``set_listener(fn)`` registers exactly one global listener
    (``fn(stage, detail)``); the License Center / main window binds its status
    label to it. Events are also emitted on the generic EventBus channel
    ``workflow.progress`` and written to LiveLog.
    """

    # Canonical stages (order matters) — the only strings any workflow may use.
    CHECKING_INTERNET = "Checking Internet"
    CHECKING_SERVER = "Checking Server"
    CHECKING_LICENSE = "Checking License"
    CHECKING_PRODUCT = "Checking Product"
    CHECKING_CUSTOMER = "Checking Customer"
    CHECKING_HARDWARE = "Checking Hardware"
    SENDING_OTP = "Sending OTP"
    OTP_SENT = "OTP Sent"
    WAITING_OTP = "Waiting OTP"
    OTP_VERIFIED = "OTP Verified"
    BINDING_HARDWARE = "Binding Hardware"
    UPDATING_LICENSE = "Updating License"
    SAVING_CACHE = "Saving Cache"
    REFRESHING_SDK = "Refreshing SDK"
    REFRESHING_DASHBOARD = "Refreshing Dashboard"
    COMPLETED = "Completed"

    STAGES: tuple = (
        CHECKING_INTERNET,
        CHECKING_SERVER,
        CHECKING_LICENSE,
        CHECKING_PRODUCT,
        CHECKING_CUSTOMER,
        CHECKING_HARDWARE,
        SENDING_OTP,
        OTP_SENT,
        WAITING_OTP,
        OTP_VERIFIED,
        BINDING_HARDWARE,
        UPDATING_LICENSE,
        SAVING_CACHE,
        REFRESHING_SDK,
        REFRESHING_DASHBOARD,
        COMPLETED,
    )

    _listener: Optional[Callable[[str, str], None]] = None
    _current_stage: Optional[str] = None

    @classmethod
    def set_listener(cls, listener: Optional[Callable[[str, str], None]]) -> None:
        cls._listener = listener

    @classmethod
    def stage(cls, stage: str, detail: str = "") -> None:
        cls._current_stage = stage
        if cls._listener:
            try:
                cls._listener(stage, detail)
            except Exception:
                pass
        try:
            from .event_bus import EventBus
            EventBus.emit("workflow.progress", stage, detail)
        except Exception:
            pass
        if detail:
            LiveLog.log("WORKFLOW_PROGRESS", f"{stage} — {detail}")
        else:
            LiveLog.log("WORKFLOW_PROGRESS", stage)

    @classmethod
    def get_current_stage(cls) -> Optional[str]:
        return cls._current_stage

    @classmethod
    def reset(cls) -> None:
        cls._current_stage = None


def format_timer(remaining_seconds: int) -> str:
    """mm:ss timer string used by every OTP expiry label."""
    remaining_seconds = max(0, int(remaining_seconds))
    return f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"


def now_ts() -> float:
    return time.time()
