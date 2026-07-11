"""Cryptographic utilities for API request signing"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any


def generate_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def generate_nonce() -> str:
    return str(uuid.uuid4())


def sign_request(
    payload: Dict[str, Any],
    secret: str,
    timestamp: str,
    nonce: str
) -> str:
    payload_json = json.dumps(payload, separators=(',', ':'))
    message = f"{timestamp}:{nonce}:{payload_json}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature
