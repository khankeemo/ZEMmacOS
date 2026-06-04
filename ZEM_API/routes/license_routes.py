"""Public license endpoints for desktop clients."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from security.rate_limit import limiter
from services import license_service

router = APIRouter(prefix="/license", tags=["license"])


class LicenseCredentials(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    license_key: str = Field(..., min_length=8)
    hardware_id: str = Field(..., min_length=8)
    device_name: str = ""


class ResetRequest(BaseModel):
    license_key: str
    hardware_id: str | None = None


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/validate")
@limiter.limit("30/minute")
def validate_license(
    request: Request,
    body: LicenseCredentials,
    db: Session = Depends(get_db),
):
    return license_service.validate_license(
        db, body.name, body.email, body.license_key, body.hardware_id, _client_ip(request)
    )


@router.post("/activate")
@limiter.limit("20/minute")
def activate_license(
    request: Request,
    body: LicenseCredentials,
    db: Session = Depends(get_db),
):
    return license_service.activate_license(
        db,
        body.name,
        body.email,
        body.license_key,
        body.hardware_id,
        body.device_name,
        _client_ip(request),
    )


@router.post("/reset")
@limiter.limit("10/minute")
def reset_license(
    request: Request,
    body: ResetRequest,
    db: Session = Depends(get_db),
):
    return license_service.reset_device(
        db, body.license_key, body.hardware_id, _client_ip(request)
    )


@router.get("/info")
@limiter.limit("60/minute")
def license_info(
    request: Request,
    license_key: str,
    db: Session = Depends(get_db),
):
    return license_service.get_license_info(db, license_key, _client_ip(request))
