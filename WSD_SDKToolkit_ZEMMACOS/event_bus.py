"""Global Event Bus — single channel for license status changes and workflow events.

The engine is the only emitter of state-changing events. Every screen
(Dashboard, Settings, Main UI, Welcome, Notifications, License Center, Tray,
Integrations) subscribes to ``LicenseStatusChanged`` and re-renders from the
event payload — screens never refresh each other and never poll state.
"""
import time
from typing import Any, Callable, List, Optional


class EventBus:
    """Singleton event bus.

    - ``subscribe_status_changed(callback)`` — called with the new
      ``LicenseStatus`` every time the authoritative state changes.
    - ``emit_status_changed(status)`` — engine-only entry point.
    - Generic ``subscribe(event, callback)`` / ``emit(event, *args)`` channel
      for auxiliary events (progress stages, offline/online, workflow state).
    """

    _status_subscribers: List[Callable[[Any], None]] = []
    _subscribers: dict = {}
    _last_status: Optional[Any] = None

    # ------------------------------------------------------------------
    # LicenseStatusChanged
    # ------------------------------------------------------------------

    @classmethod
    def subscribe_status_changed(cls, callback: Callable[[Any], None]) -> None:
        if callback not in cls._status_subscribers:
            cls._status_subscribers.append(callback)

    @classmethod
    def unsubscribe_status_changed(cls, callback: Callable[[Any], None]) -> None:
        if callback in cls._status_subscribers:
            cls._status_subscribers.remove(callback)

    @classmethod
    def emit_status_changed(cls, status: Any) -> None:
        """Engine-only: fire the single LicenseStatusChanged event exactly once
        per state mutation. Subscribers re-render; no screen refreshes itself
        or others manually."""
        cls._last_status = status
        for callback in list(cls._status_subscribers):
            try:
                callback(status)
            except Exception:
                pass

    @classmethod
    def get_last_status(cls) -> Optional[Any]:
        return cls._last_status

    # ------------------------------------------------------------------
    # Generic events (progress, workflow, connectivity)
    # ------------------------------------------------------------------

    @classmethod
    def subscribe(cls, event: str, callback: Callable[..., None]) -> None:
        callbacks = cls._subscribers.setdefault(event, [])
        if callback not in callbacks:
            callbacks.append(callback)

    @classmethod
    def unsubscribe(cls, event: str, callback: Callable[..., None]) -> None:
        callbacks = cls._subscribers.get(event, [])
        if callback in callbacks:
            callbacks.remove(callback)

    @classmethod
    def emit(cls, event: str, *args: Any, **kwargs: Any) -> None:
        for callback in list(cls._subscribers.get(event, [])):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass

    @classmethod
    def reset(cls) -> None:
        cls._status_subscribers = []
        cls._subscribers = {}
        cls._last_status = None


# Convenience aliases — screens subscribe to one canonical event name.
LICENSE_STATUS_CHANGED = "LicenseStatusChanged"
