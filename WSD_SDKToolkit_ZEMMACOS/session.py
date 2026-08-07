"""Global Session Manager — the single runtime-session owner (SECTION 0D §1).

All session state (customer, license, product, plan, hardware, runtime, SDK
version, current workflow, auth state) lives here and nowhere else. The engine
writes it; UI and dialogs read it via engine.session(). No module keeps a second
copy of a session field.
"""
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["SessionManager", "Session"]

AUTH_ANONYMOUS = "anonymous"
AUTH_OTP_PENDING = "otp_pending"
AUTH_OTP_VERIFIED = "otp_verified"
AUTH_LICENSED = "licensed"
AUTH_TRIAL = "trial"


class Session:
    def __init__(self):
        self.customer: Dict[str, Any] = {}
        self.license: Dict[str, Any] = {}
        self.product: Dict[str, Any] = {}
        self.plan: Dict[str, Any] = {}
        self.hardware_id: str = ""
        self.runtime: str = "python"
        self.sdk_version: str = "1.0.0"
        self.current_workflow: Optional[str] = None
        self.auth_state: str = AUTH_ANONYMOUS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer": self.customer,
            "license": self.license,
            "product": self.product,
            "plan": self.plan,
            "hardware_id": self.hardware_id,
            "runtime": self.runtime,
            "sdk_version": self.sdk_version,
            "current_workflow": self.current_workflow,
            "auth_state": self.auth_state,
        }


class SessionManager:
    _session = Session()

    @classmethod
    def get(cls) -> Session:
        return cls._session

    @classmethod
    def snapshot(cls) -> Dict[str, Any]:
        return cls._session.to_dict()

    @classmethod
    def reset(cls) -> None:
        cls._session = Session()

    @classmethod
    def set_customer(cls, customer: Optional[Dict[str, Any]]) -> None:
        cls._session.customer = dict(customer or {})
        cls._emit()

    @classmethod
    def set_license(cls, license_data: Optional[Dict[str, Any]]) -> None:
        cls._session.license = dict(license_data or {})
        cls._emit()

    @classmethod
    def set_product(cls, product: Optional[Dict[str, Any]]) -> None:
        cls._session.product = dict(product or {})
        cls._emit()

    @classmethod
    def set_plan(cls, plan: Optional[Dict[str, Any]]) -> None:
        cls._session.plan = dict(plan or {})
        cls._emit()

    @classmethod
    def set_hardware_id(cls, hardware_id: str) -> None:
        cls._session.hardware_id = hardware_id or ""
        cls._emit()

    @classmethod
    def set_runtime(cls, runtime: str) -> None:
        cls._session.runtime = runtime or "python"
        cls._emit()

    @classmethod
    def set_sdk_version(cls, version: str) -> None:
        cls._session.sdk_version = version or "1.0.0"
        cls._emit()

    @classmethod
    def set_workflow(cls, workflow: Optional[str]) -> None:
        cls._session.current_workflow = workflow
        cls._emit()

    @classmethod
    def begin_workflow(cls, name: str) -> None:
        cls._session.current_workflow = name
        cls._emit()

    @classmethod
    def end_workflow(cls) -> None:
        cls._session.current_workflow = None
        cls._emit()

    @classmethod
    def set_auth_state(cls, state: str) -> None:
        cls._session.auth_state = state
        cls._emit()

    @classmethod
    def _emit(cls) -> None:
        try:
            from .event_bus import EventBus
            EventBus.emit("session.updated", cls._session.to_dict())
        except Exception:
            pass
        try:
            LiveLog.log("SESSION_UPDATED", f"auth={cls._session.auth_state} "
                                           f"workflow={cls._session.current_workflow or 'none'}")
        except Exception:
            pass