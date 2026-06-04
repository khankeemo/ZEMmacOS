"""Build signed client cache payloads for offline grace."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from security.encryption import attach_signature
from security.jwt_handler import create_access_token

load_dotenv()

OFFLINE_GRACE_HOURS = int(os.getenv("OFFLINE_GRACE_HOURS", "72"))


def build_client_payload(
    *,
    valid: bool,
    license_type: str,
    customer_name: str = "",
    customer_email: str = "",
    license_key: str = "",
    days_left: int = 0,
    expiry_date: Optional[str] = None,
    status: str = "",
    hardware_id: str = "",
    message: str = "",
    error: str = "",
    error_type: str = "",
) -> Dict[str, Any]:
    """Create standardized response with JWT and offline grace window."""
    now = datetime.now(timezone.utc)
    offline_until = now + timedelta(hours=OFFLINE_GRACE_HOURS)

    payload: Dict[str, Any] = {
        "valid": valid,
        "license_type": license_type,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "license_key": license_key,
        "days_left": days_left,
        "expiry_date": expiry_date,
        "status": status,
        "hardware_id": hardware_id,
        "message": message,
        "error": error,
        "error_type": error_type,
        "offline_grace_until": offline_until.isoformat(),
        "server_time": now.isoformat(),
    }

    if valid:
        token_data = {
            "sub": license_key or "trial",
            "hw": hardware_id,
            "type": license_type,
            "expiry": expiry_date,
            "days_left": days_left,
        }
        payload["access_token"] = create_access_token(token_data)

    return attach_signature(payload)
