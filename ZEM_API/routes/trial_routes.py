"""Trial endpoints for desktop clients."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from security.rate_limit import limiter
from services import trial_service

router = APIRouter(prefix="/trial", tags=["trial"])


class TrialRequest(BaseModel):
    hardware_id: str = Field(..., min_length=8)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/start")
@limiter.limit("5/minute")
def start_trial(request: Request, body: TrialRequest, db: Session = Depends(get_db)):
    return trial_service.start_trial(db, body.hardware_id, _client_ip(request))


@router.post("/status")
@limiter.limit("60/minute")
def trial_status(request: Request, body: TrialRequest, db: Session = Depends(get_db)):
    return trial_service.trial_status(db, body.hardware_id, _client_ip(request))
