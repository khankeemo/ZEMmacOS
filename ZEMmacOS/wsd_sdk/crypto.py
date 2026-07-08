"""Cryptographic utilities for license verification"""
import hashlib
import hmac
import base64
from typing import Optional

def generate_hmac(data: str, secret: str) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_hmac(data: str, signature: str, secret: str) -> bool:
    expected = generate_hmac(data, secret)
    return hmac.compare_digest(expected, signature)

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')

def base64_decode(data: str) -> bytes:
    return base64.b64decode(data.encode('utf-8'))
