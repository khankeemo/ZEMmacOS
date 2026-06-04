"""JWT creation and verification for client session tokens."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_HOURS = int(os.getenv("OFFLINE_GRACE_HOURS", "72"))


def create_access_token(
    payload: Dict[str, Any],
    expires_hours: Optional[int] = None,
) -> str:
    """Create a signed JWT for offline grace caching."""
    data = payload.copy()
    hours = expires_hours if expires_hours is not None else DEFAULT_TOKEN_HOURS
    expire = datetime.now(timezone.utc) + timedelta(hours=hours)
    data.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT. Returns None if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
