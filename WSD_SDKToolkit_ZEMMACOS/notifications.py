"""System notifications — delegates to LicenseEngine"""
from .license_engine import LicenseEngine

__all__ = ["get_notifications", "mark_notification_read", "get_unread_notification_count"]


def get_notifications(engine: LicenseEngine, email: str) -> dict:
    return engine.get_notifications(email)


def mark_notification_read(engine: LicenseEngine, notification_id: str) -> dict:
    return engine.mark_notification_read(notification_id)


def get_unread_notification_count(engine: LicenseEngine, email: str) -> dict:
    return engine.get_unread_notification_count(email)
