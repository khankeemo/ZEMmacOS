"""HMAC signing for API response integrity."""

import hashlib
import hmac
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

SIGNING_SECRET = os.getenv("SIGNING_SECRET", "change-me-signing-secret").encode()


def sign_payload(payload: Dict[str, Any]) -> str:
    """Create HMAC-SHA256 signature for a response payload."""
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(SIGNING_SECRET, canonical.encode(), hashlib.sha256).hexdigest()


def attach_signature(response: Dict[str, Any]) -> Dict[str, Any]:
    """Add signature field to API response."""
    body = {k: v for k, v in response.items() if k != "signature"}
    response["signature"] = sign_payload(body)
    return response
