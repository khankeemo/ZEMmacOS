"""Authoritative license business logic (PostgreSQL)."""

import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models.activation import Activation
from models.license import License
from services import audit_service, hardware_service
from services.cache_service import build_client_payload

load_dotenv()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _days_left(expiry: Optional[datetime]) -> int:
    if not expiry:
        return 365
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return max(0, (expiry - _utc_now()).days)


def _format_expiry(expiry: Optional[datetime]) -> Optional[str]:
    if not expiry:
        return None
    return expiry.strftime("%Y-%m-%d")


def _get_license_by_key(db: Session, license_key: str) -> Optional[License]:
    key = hardware_service.normalize_key(license_key)
    return db.query(License).filter(License.license_key == key).first()


def _get_activations(db: Session, license_id: int) -> List[Activation]:
    return db.query(Activation).filter(Activation.license_id == license_id).all()


def generate_license_key(length: int = 24) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_license_info(
    db: Session,
    license_key: str,
    ip_address: str = "",
) -> Dict[str, Any]:
    lic = _get_license_by_key(db, license_key)
    if not lic:
        return {"success": False, "error": "License key not found", "error_type": "not_found"}

    activations = _get_activations(db, lic.id)
    hwids = [a.hardware_id for a in activations]

    audit_service.log_event(
        db, "license_info", f"Info requested for {lic.license_key}", ip_address, lic.license_key
    )

    return {
        "success": True,
        "customer_name": lic.customer_name,
        "customer_email": lic.customer_email,
        "license_key": lic.license_key,
        "expiry_date": _format_expiry(lic.expiry_date),
        "days_left": _days_left(lic.expiry_date),
        "status": lic.status,
        "hardware_ids": hwids,
        "plan": lic.plan,
        "max_devices": lic.max_devices,
        "notes": lic.notes or "",
    }


def validate_license(
    db: Session,
    name: str,
    email: str,
    license_key: str,
    hardware_id: str,
    ip_address: str = "",
) -> Dict[str, Any]:
    lic = _get_license_by_key(db, license_key)
    if not lic:
        audit_service.log_event(
            db, "validate_fail", "License not found", ip_address, license_key, hardware_id
        )
        return build_client_payload(
            valid=False,
            license_type="none",
            error="License key not found",
            error_type="not_found",
            hardware_id=hardware_id,
        )

    if hardware_service.normalize_name(lic.customer_name) != hardware_service.normalize_name(name):
        return build_client_payload(
            valid=False, license_type="none",
            error="Name does not match this license", error_type="name_mismatch", hardware_id=hardware_id,
        )

    if hardware_service.normalize_email(lic.customer_email) != hardware_service.normalize_email(email):
        return build_client_payload(
            valid=False, license_type="none",
            error="Email does not match this license", error_type="email_mismatch", hardware_id=hardware_id,
        )

    if lic.status.lower() != "active":
        return build_client_payload(
            valid=False, license_type="none",
            error=f"License status is '{lic.status}'", error_type="inactive",
            hardware_id=hardware_id, status=lic.status,
        )

    if lic.expiry_date and _utc_now() > lic.expiry_date.replace(tzinfo=timezone.utc):
        return build_client_payload(
            valid=False, license_type="none",
            error="License has expired", error_type="expired",
            hardware_id=hardware_id, expiry_date=_format_expiry(lic.expiry_date),
        )

    hw = hardware_service.normalize_hardware_id(hardware_id)
    activations = _get_activations(db, lic.id)
    bound = [a.hardware_id for a in activations]

    if not bound:
        return build_client_payload(
            valid=True, license_type="paid",
            customer_name=lic.customer_name, customer_email=lic.customer_email,
            license_key=lic.license_key, days_left=_days_left(lic.expiry_date),
            expiry_date=_format_expiry(lic.expiry_date), status="licensed",
            hardware_id=hw, message="Valid — activation required",
        )

    if hw in bound:
        audit_service.log_event(db, "validate_ok", "License validated", ip_address, lic.license_key, hw)
        return build_client_payload(
            valid=True, license_type="paid",
            customer_name=lic.customer_name, customer_email=lic.customer_email,
            license_key=lic.license_key, days_left=_days_left(lic.expiry_date),
            expiry_date=_format_expiry(lic.expiry_date), status="licensed",
            hardware_id=hw, message=f"Licensed. {_days_left(lic.expiry_date)} days remaining.",
        )

    if len(bound) < lic.max_devices:
        return build_client_payload(
            valid=True, license_type="paid",
            customer_name=lic.customer_name, customer_email=lic.customer_email,
            license_key=lic.license_key, days_left=_days_left(lic.expiry_date),
            expiry_date=_format_expiry(lic.expiry_date), status="licensed",
            hardware_id=hw, message="Valid — additional device activation available",
        )

    audit_service.log_event(db, "validate_fail", "Device limit reached", ip_address, lic.license_key, hw)
    return build_client_payload(
        valid=False, license_type="none",
        error=f"Device limit reached ({lic.max_devices} devices).",
        error_type="device_limit", hardware_id=hw,
    )


def activate_license(
    db: Session,
    name: str,
    email: str,
    license_key: str,
    hardware_id: str,
    device_name: str = "",
    ip_address: str = "",
) -> Dict[str, Any]:
    validation = validate_license(db, name, email, license_key, hardware_id, ip_address)
    if not validation.get("valid"):
        return {
            "success": False,
            "error": validation.get("error", "Validation failed"),
            "error_type": validation.get("error_type", "invalid"),
        }

    lic = _get_license_by_key(db, license_key)
    hw = hardware_service.normalize_hardware_id(hardware_id)
    activations = _get_activations(db, lic.id)

    existing = next((a for a in activations if a.hardware_id == hw), None)
    if existing:
        existing.last_seen = _utc_now()
        db.commit()
        days = _days_left(lic.expiry_date)
        audit_service.log_event(db, "activate_ok", "Already activated on device", ip_address, lic.license_key, hw)
        result = build_client_payload(
            valid=True, license_type="paid",
            customer_name=lic.customer_name, customer_email=lic.customer_email,
            license_key=lic.license_key, days_left=days,
            expiry_date=_format_expiry(lic.expiry_date), status="licensed",
            hardware_id=hw,
            message=f"License already activated on this device. {days} days remaining.",
        )
        return {"success": True, **result}

    if len(activations) >= lic.max_devices:
        return {
            "success": False,
            "error": f"Device limit reached ({lic.max_devices})",
            "error_type": "device_limit",
        }

    activation = Activation(
        license_id=lic.id,
        hardware_id=hw,
        device_name=device_name or "ZEMmacOS Client",
        ip_address=ip_address,
        activated_at=_utc_now(),
        last_seen=_utc_now(),
    )
    db.add(activation)
    db.commit()

    days = _days_left(lic.expiry_date)
    audit_service.log_event(db, "activate_ok", "License activated", ip_address, lic.license_key, hw)
    payload = build_client_payload(
        valid=True, license_type="paid",
        customer_name=lic.customer_name, customer_email=lic.customer_email,
        license_key=lic.license_key, days_left=days,
        expiry_date=_format_expiry(lic.expiry_date), status="licensed",
        hardware_id=hw,
        message=f"License activated successfully! {days} days remaining.",
    )
    return {"success": True, **payload}


def reset_device(
    db: Session,
    license_key: str,
    hardware_id: Optional[str] = None,
    ip_address: str = "",
) -> Dict[str, Any]:
    lic = _get_license_by_key(db, license_key)
    if not lic:
        return {"success": False, "error": "License key not found", "error_type": "not_found"}

    query = db.query(Activation).filter(Activation.license_id == lic.id)
    if hardware_id:
        hw = hardware_service.normalize_hardware_id(hardware_id)
        query = query.filter(Activation.hardware_id == hw)
    removed = query.delete()
    db.commit()

    audit_service.log_event(
        db, "reset_device",
        f"Removed {removed} activation(s) for {lic.license_key}",
        ip_address, lic.license_key, hardware_id or "",
    )
    return {
        "success": True,
        "message": f"Hardware reset complete ({removed} device(s) cleared)",
        "removed_count": removed,
    }


def create_license(
    db: Session,
    name: str,
    email: str,
    expiry_days: int = 365,
    plan: str = "Standard",
    max_devices: int = 1,
    notes: str = "",
    license_key: Optional[str] = None,
    ip_address: str = "",
) -> Dict[str, Any]:
    if not hardware_service.validate_email(email):
        return {"success": False, "error": "Invalid email format"}

    key = license_key or generate_license_key()
    key = hardware_service.normalize_key(key)

    existing_email = db.query(License).filter(
        License.customer_email == hardware_service.normalize_email(email)
    ).first()

    expiry = _utc_now() + timedelta(days=expiry_days)

    if existing_email:
        existing_email.customer_name = name
        existing_email.expiry_date = expiry
        existing_email.status = "active"
        existing_email.plan = plan
        existing_email.max_devices = max_devices
        if notes:
            existing_email.notes = notes
        existing_email.updated_at = _utc_now()
        db.commit()
        audit_service.log_event(db, "license_update", f"Updated license for {email}", ip_address, key)
        return {
            "success": True,
            "message": f"License updated for {name}",
            "license_key": existing_email.license_key,
            "expiry_date": _format_expiry(expiry),
            "updated_existing": True,
        }

    if _get_license_by_key(db, key):
        return {"success": False, "error": "License key already exists", "error_type": "duplicate_key"}

    lic = License(
        customer_name=name,
        customer_email=email,
        license_key=key,
        plan=plan,
        status="active",
        expiry_date=expiry,
        max_devices=max_devices,
        notes=notes,
    )
    db.add(lic)
    db.commit()

    audit_service.log_event(db, "license_create", f"Created license for {email}", ip_address, key)
    return {
        "success": True,
        "message": f"License created for {name}",
        "license_key": key,
        "expiry_date": _format_expiry(expiry),
        "updated_existing": False,
    }


def revoke_license(db: Session, license_key: str, ip_address: str = "") -> Dict[str, Any]:
    lic = _get_license_by_key(db, license_key)
    if not lic:
        return {"success": False, "error": "License key not found"}
    lic.status = "revoked"
    lic.updated_at = _utc_now()
    db.commit()
    audit_service.log_event(db, "license_revoke", f"Revoked {license_key}", ip_address, license_key)
    return {"success": True, "message": "License revoked"}


def extend_license(db: Session, license_key: str, extra_days: int, ip_address: str = "") -> Dict[str, Any]:
    lic = _get_license_by_key(db, license_key)
    if not lic:
        return {"success": False, "error": "License key not found"}

    base = lic.expiry_date or _utc_now()
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    lic.expiry_date = base + timedelta(days=extra_days)
    lic.updated_at = _utc_now()
    db.commit()
    audit_service.log_event(db, "license_extend", f"Extended {extra_days} days", ip_address, license_key)
    return {
        "success": True,
        "message": f"License extended by {extra_days} days",
        "expiry_date": _format_expiry(lic.expiry_date),
        "days_left": _days_left(lic.expiry_date),
    }
