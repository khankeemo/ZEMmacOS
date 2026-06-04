"""Admin-only license management endpoints."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from routes.auth_routes import verify_admin
from security.rate_limit import limiter
from services import license_service
from services.dashboard_service import (
    get_activation_history,
    get_audit_logs,
    get_dashboard_stats,
    list_trials,
    search_by_license_key,
)
from services.hardware_service import normalize_email
from models.license import License

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin)])


class CreateLicenseRequest(BaseModel):
    name: str
    email: str  # validated in service (allows internal test domains)
    expiry_days: int = 365
    plan: str = "Standard"
    max_devices: int = 1
    notes: str = ""
    license_key: str | None = None


class ValidateAdminRequest(BaseModel):
    name: str = ""
    email: str = "admin@zemmacos.local"
    license_key: str
    hardware_id: str = "ADMIN-CHECK-00000000"


class LicenseKeyRequest(BaseModel):
    license_key: str


class ExtendLicenseRequest(BaseModel):
    license_key: str
    extra_days: int = Field(..., gt=0)


class ResetDeviceRequest(BaseModel):
    license_key: str
    hardware_id: str | None = None


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.get("/dashboard")
@limiter.limit("120/minute")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return get_dashboard_stats(db)


@router.get("/search/email")
@limiter.limit("60/minute")
def search_by_email(request: Request, email: str, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.customer_email == normalize_email(email)).first()
    if not lic:
        return {"success": False, "error": "Customer not found"}
    return search_by_license_key(db, lic.license_key)


@router.get("/search/license")
@limiter.limit("60/minute")
def search_by_license(request: Request, license_key: str, db: Session = Depends(get_db)):
    return search_by_license_key(db, license_key)


@router.get("/search")
@limiter.limit("60/minute")
def search_customer_legacy(request: Request, email: str, db: Session = Depends(get_db)):
    return search_by_email(request, email, db)


@router.get("/activations")
@limiter.limit("60/minute")
def activation_history(request: Request, limit: int = 100, db: Session = Depends(get_db)):
    return get_activation_history(db, limit)


@router.get("/logs")
@limiter.limit("60/minute")
def audit_logs(request: Request, limit: int = 200, db: Session = Depends(get_db)):
    return get_audit_logs(db, limit)


@router.get("/trials")
@limiter.limit("60/minute")
def trials_list(request: Request, limit: int = 100, db: Session = Depends(get_db)):
    return list_trials(db, limit)


@router.post("/create-license")
@limiter.limit("30/minute")
def create_license(request: Request, body: CreateLicenseRequest, db: Session = Depends(get_db)):
    result = license_service.create_license(
        db,
        body.name,
        body.email,
        body.expiry_days,
        body.plan,
        body.max_devices,
        body.notes,
        body.license_key,
        _client_ip(request),
    )
    if result.get("success"):
        result["expiry"] = result.get("expiry_date")
    return result


@router.post("/create-test-license")
@limiter.limit("10/minute")
def create_test_license(request: Request, db: Session = Depends(get_db)):
    return license_service.create_license(
        db,
        "Test User",
        "test@example.com",
        365,
        "Professional",
        1,
        "Auto-generated test license",
        None,
        _client_ip(request),
    )


@router.post("/validate-license")
@limiter.limit("60/minute")
def validate_license_admin(request: Request, body: ValidateAdminRequest, db: Session = Depends(get_db)):
    info = search_by_license_key(db, body.license_key)
    if not info.get("success"):
        return {"valid": False, "error": info.get("error", "Not found")}
    if body.name:
        return license_service.validate_license(
            db, body.name, str(body.email), body.license_key, body.hardware_id, _client_ip(request)
        )
    return {
        "valid": info.get("status", "").lower() == "active",
        "success": True,
        "license_info": info,
        "days_left": info.get("days_left", 0),
        "plan": info.get("plan"),
        "status": info.get("status"),
        "hardware_ids": info.get("hardware_ids", []),
        "max_devices": info.get("max_devices", 1),
        "activations": info.get("activations_detail", []),
    }


@router.post("/revoke-license")
@limiter.limit("30/minute")
def revoke_license(request: Request, body: LicenseKeyRequest, db: Session = Depends(get_db)):
    return license_service.revoke_license(db, body.license_key, _client_ip(request))


@router.post("/extend-license")
@limiter.limit("30/minute")
def extend_license(request: Request, body: ExtendLicenseRequest, db: Session = Depends(get_db)):
    return license_service.extend_license(
        db, body.license_key, body.extra_days, _client_ip(request)
    )


@router.post("/reset-device")
@limiter.limit("30/minute")
def reset_device(request: Request, body: ResetDeviceRequest, db: Session = Depends(get_db)):
    return license_service.reset_device(
        db, body.license_key, body.hardware_id, _client_ip(request)
    )
