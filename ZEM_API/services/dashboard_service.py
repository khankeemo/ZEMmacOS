"""Dashboard statistics and admin queries."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.activation import Activation
from models.license import License
from models.logs import AuditLog
from models.trial import Trial


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    now = _utc_now()
    total = db.query(License).count()
    active = db.query(License).filter(License.status == "active").count()
    revoked = db.query(License).filter(License.status == "revoked").count()
    expired = db.query(License).filter(
        License.expiry_date.isnot(None),
        License.expiry_date < now,
    ).count()
    active_trials = db.query(Trial).filter(
        Trial.status == "active",
        Trial.expiry_date > now,
    ).count()
    online_cutoff = now - timedelta(hours=24)
    online_devices = db.query(Activation).filter(Activation.last_seen >= online_cutoff).count()
    total_activations = db.query(Activation).count()

    return {
        "success": True,
        "total_licenses": total,
        "active_licenses": active,
        "revoked_licenses": revoked,
        "expired_licenses": expired,
        "active_trials": active_trials,
        "online_devices_24h": online_devices,
        "total_activations": total_activations,
        "timestamp": now.isoformat(),
    }


def get_activation_history(db: Session, limit: int = 100) -> Dict[str, Any]:
    rows = (
        db.query(Activation, License)
        .join(License, Activation.license_id == License.id)
        .order_by(Activation.last_seen.desc())
        .limit(limit)
        .all()
    )
    items = []
    for act, lic in rows:
        items.append({
            "license_key": lic.license_key,
            "customer_name": lic.customer_name,
            "customer_email": lic.customer_email,
            "hardware_id": act.hardware_id,
            "device_name": act.device_name,
            "ip_address": act.ip_address,
            "activated_at": act.activated_at.isoformat() if act.activated_at else "",
            "last_seen": act.last_seen.isoformat() if act.last_seen else "",
            "plan": lic.plan,
            "status": lic.status,
        })
    return {"success": True, "activations": items, "count": len(items)}


def get_audit_logs(db: Session, limit: int = 200) -> Dict[str, Any]:
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "ip_address": log.ip_address,
                "license_key": log.license_key,
                "hardware_id": log.hardware_id,
            }
            for log in logs
        ],
    }


def search_by_license_key(db: Session, license_key: str) -> Dict[str, Any]:
    from services import license_service
    from services.hardware_service import normalize_key

    key = normalize_key(license_key)
    lic = db.query(License).filter(License.license_key == key).first()
    if not lic:
        return {"success": False, "error": "License not found"}
    info = license_service.get_license_info(db, key)
    activations = (
        db.query(Activation)
        .filter(Activation.license_id == lic.id)
        .order_by(Activation.last_seen.desc())
        .all()
    )
    info["activations_detail"] = [
        {
            "hardware_id": a.hardware_id,
            "device_name": a.device_name,
            "ip_address": a.ip_address,
            "activated_at": a.activated_at.isoformat() if a.activated_at else "",
            "last_seen": a.last_seen.isoformat() if a.last_seen else "",
        }
        for a in activations
    ]
    return info


def list_trials(db: Session, limit: int = 100) -> Dict[str, Any]:
    trials = db.query(Trial).order_by(Trial.started_at.desc()).limit(limit).all()
    now = _utc_now()
    items = []
    for t in trials:
        exp = t.expiry_date
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_left = max(0, (exp - now).days) if exp and exp > now else 0
        items.append({
            "hardware_id": t.hardware_id,
            "started_at": t.started_at.isoformat() if t.started_at else "",
            "expiry_date": t.expiry_date.strftime("%Y-%m-%d") if t.expiry_date else "",
            "status": t.status,
            "days_left": days_left,
        })
    return {"success": True, "trials": items, "count": len(items)}
