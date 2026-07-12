"""Cryptographic utilities for API request signing"""
import base64
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
    nonce: str,
    method: str = 'POST',
    path: str = '',
    query: str = ''
) -> str:
    payload_json = json.dumps(payload, separators=(',', ':'))
    body_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    message = f"{method}
{path}
{query}
{body_hash}
{timestamp}
{nonce}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')
