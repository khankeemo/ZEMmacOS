"""Trial management — server authoritative."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models.trial import Trial
from services import audit_service, hardware_service
from services.cache_service import build_client_payload

load_dotenv()

TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def start_trial(db: Session, hardware_id: str, ip_address: str = "") -> Dict[str, Any]:
    hw = hardware_service.normalize_hardware_id(hardware_id)
    existing = db.query(Trial).filter(Trial.hardware_id == hw).first()

    if existing:
        if existing.status == "active" and existing.expiry_date > _utc_now():
            days = max(0, (existing.expiry_date.replace(tzinfo=timezone.utc) - _utc_now()).days)
            return {
                "success": False,
                "message": f"Trial already active. {days} days remaining.",
                "is_active": True,
                "days_remaining": days,
            }
        return {
            "success": False,
            "message": "Trial has expired. Please purchase a license.",
            "is_active": False,
            "trial_expired": True,
            "days_remaining": 0,
        }

    expiry = _utc_now() + timedelta(days=TRIAL_DAYS)
    trial = Trial(hardware_id=hw, started_at=_utc_now(), expiry_date=expiry, status="active")
    db.add(trial)
    db.commit()
    audit_service.log_event(db, "trial_start", f"Trial started for {hw[:16]}...", ip_address, hardware_id=hw)

    payload = build_client_payload(
        valid=True,
        license_type="trial",
        days_left=TRIAL_DAYS,
        expiry_date=expiry.strftime("%Y-%m-%d"),
        status="trial",
        hardware_id=hw,
        message=f"{TRIAL_DAYS}-day trial started successfully",
    )
    return {"success": True, "days_remaining": TRIAL_DAYS, **payload}


def trial_status(db: Session, hardware_id: str, ip_address: str = "") -> Dict[str, Any]:
    hw = hardware_service.normalize_hardware_id(hardware_id)
    trial = db.query(Trial).filter(Trial.hardware_id == hw).first()

    if not trial:
        return build_client_payload(
            valid=False,
            license_type="none",
            hardware_id=hw,
            message="No trial found",
            error_type="no_trial",
        )

    expiry = trial.expiry_date
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if _utc_now() > expiry or trial.status != "active":
        trial.status = "expired"
        db.commit()
        return build_client_payload(
            valid=False,
            license_type="trial",
            hardware_id=hw,
            status="expired",
            message="Trial has expired",
            error_type="trial_expired",
            days_left=0,
        )

    days = max(0, (expiry - _utc_now()).days)
    return build_client_payload(
        valid=True,
        license_type="trial",
        hardware_id=hw,
        status="trial",
        days_left=days,
        expiry_date=expiry.strftime("%Y-%m-%d"),
        message=f"Trial active: {days} days remaining",
    )
