"""Security Rules — encryption at rest and secrets policy (SECTION 0D §11).

Never store OTP codes, API secrets, passwords, or auth tokens in plaintext. Cache
values (license status, customer info, message queue) are encrypted before writing
to disk. The fingerprint itself is never persisted in plaintext.

Encryption degrades safely: if the Fernet dependency is unavailable, operations
fail closed — the caller must never fall back to plaintext storage.
"""
import base64
import hashlib
import json
import os
from typing import Any, Dict, Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
    _FERNET_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    Fernet = None  # type: ignore
    InvalidToken = Exception
    _FERNET_AVAILABLE = False

__all__ = ["SecurityRules", "SecurityUnavailableError"]


class SecurityUnavailableError(Exception):
    """Raised when encryption is required but the Fernet dependency is missing."""


class SecurityRules:
    _key: Optional[bytes] = None

    # ====================================================================
    # Key derivation (hardware-bound so the cache only decrypts on-device)
    # ====================================================================

    @classmethod
    def derive_key(cls, hardware_fingerprint: str, salt: str = "websmith-secure-v1") -> bytes:
        material = f"{hardware_fingerprint}|{salt}".encode("utf-8")
        raw = hashlib.sha256(material).digest()
        return base64.urlsafe_b64encode(raw)

    @classmethod
    def set_key(cls, hardware_fingerprint: str, salt: str = "websmith-secure-v1") -> None:
        if not _FERNET_AVAILABLE:
            return
        cls._key = cls.derive_key(hardware_fingerprint, salt)

    # ====================================================================
    # Encrypt / decrypt
    # ====================================================================

    @classmethod
    def _fernet(cls) -> Fernet:
        if not _FERNET_AVAILABLE or cls._key is None:
            raise SecurityUnavailableError(
                "Encryption is unavailable. Cryptographic storage could not be enabled."
            )
        return Fernet(cls._key)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        return cls._fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        try:
            return cls._fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as e:
            raise SecurityUnavailableError("Cached value could not be decrypted.") from e

    @classmethod
    def encrypt_json(cls, value: Any) -> str:
        return cls.encrypt(json.dumps(value))

    @classmethod
    def decrypt_json(cls, ciphertext: str) -> Any:
        return json.loads(cls.decrypt(ciphertext))

    # ====================================================================
    # Secrets policy helpers
    # ====================================================================

    @staticmethod
    def is_secret(name: str) -> bool:
        lowered = name.lower()
        return any(term in lowered for term in (
            "otp", "secret", "password", "token", "api_key", "key_"
        ))

    @staticmethod
    def redact(value: Optional[str]) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "********"
        return value[:4] + "..." + value[-4:]

    @staticmethod
    def assert_not_plaintext(secrets: Dict[str, Any]) -> None:
        """Raise if any secret key is stored with a non-empty plaintext value."""
        for key, value in secrets.items():
            if SecurityRules.is_secret(key) and value:
                raise SecurityUnavailableError(
                    f"Secret field '{key}' must never be persisted in plaintext."
                )
