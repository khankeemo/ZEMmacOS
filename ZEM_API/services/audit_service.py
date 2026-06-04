"""Audit logging service."""

from sqlalchemy.orm import Session

from models.logs import AuditLog


def log_event(
    db: Session,
    event_type: str,
    message: str,
    ip_address: str = "",
    license_key: str = "",
    hardware_id: str = "",
) -> None:
    entry = AuditLog(
        event_type=event_type,
        message=message,
        ip_address=ip_address,
        license_key=license_key,
        hardware_id=hardware_id,
    )
    db.add(entry)
    db.commit()
