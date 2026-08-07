"""Universal Error Catalog — one source of error wording across every runtime.

The SDK must never invent ad-hoc error strings (SECTION 0D §10). Every user-visible
error is looked up by code from this catalog so all runtimes use identical wording.
SECTION 0B Rule 5 still applies: a server-provided message passes through verbatim;
the catalog is the fallback when the server returns only a code.
"""
import re
from typing import Any, Dict, Optional

__all__ = ["ErrorCatalog", "ErrorEntry"]

CATALOG: Dict[str, Dict[str, Any]] = {
    "LICENSE_EXPIRED": {
        "message": "Your license has expired. Please renew your license to continue using the application.",
        "severity": "error",
        "retryable": False,
    },
    "LICENSE_REVOKED": {
        "message": "Your license has been revoked. Please contact support for assistance.",
        "severity": "error",
        "retryable": False,
    },
    "INVALID_LICENSE": {
        "message": "The license key you entered is invalid. Please check the key and try again.",
        "severity": "error",
        "retryable": False,
    },
    "INVALID_OTP": {
        "message": "The OTP code you entered is not valid. Please check the code and try again.",
        "severity": "error",
        "retryable": True,
    },
    "OTP_EXPIRED": {
        "message": "The OTP code has expired. Please request a new OTP code and try again.",
        "severity": "error",
        "retryable": True,
    },
    "NETWORK_ERROR": {
        "message": "Unable to reach the license server. Please check your internet connection and try again.",
        "severity": "error",
        "retryable": True,
    },
    "SERVER_BUSY": {
        "message": "The license server is busy. Please try again in a few moments.",
        "severity": "warning",
        "retryable": True,
    },
    "PAYMENT_REQUIRED": {
        "message": "A payment is required to complete this action. Please complete the purchase to continue.",
        "severity": "warning",
        "retryable": False,
    },
    "HARDWARE_CHANGED": {
        "message": "Hardware replacement requires administrator approval.",
        "severity": "warning",
        "retryable": False,
    },
    "NO_LICENSE_FOUND": {
        "message": "No license was found for this device. Please activate a valid license.",
        "severity": "warning",
        "retryable": False,
    },
    "ALREADY_ACTIVATED": {
        "message": "This license is already activated on this device.",
        "severity": "information",
        "retryable": False,
    },
    "OFFLINE_UNAVAILABLE": {
        "message": "The application is offline and no valid cached license is available. Please reconnect to the internet to continue.",
        "severity": "error",
        "retryable": True,
    },
    "UPGRADE_REQUIRED": {
        "message": "This version of the application is no longer supported. Please update to continue.",
        "severity": "warning",
        "retryable": False,
    },
    "TRIAL_EXPIRED": {
        "message": "Your trial has ended. Please activate a paid license or renew an existing license.",
        "severity": "warning",
        "retryable": False,
    },
    "TRIAL_NOT_AVAILABLE": {
        "message": "Free trial is not available for this product. Please activate a license to continue.",
        "severity": "warning",
        "retryable": False,
    },
    "GENERIC_ERROR": {
        "message": "An unexpected error occurred. Please try again later or contact support.",
        "severity": "error",
        "retryable": True,
    },
}


class ErrorEntry:
    def __init__(self, code: str, data: Dict[str, Any], server_message: Optional[str] = None):
        self.code = code
        self.message = server_message or data.get("message", "")
        self.severity = data.get("severity", "error")
        self.retryable = bool(data.get("retryable", False))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "retryable": self.retryable,
        }


class ErrorCatalog:
    @classmethod
    def lookup(cls, code: str, server_message: Optional[str] = None) -> ErrorEntry:
        code = (code or "").upper()
        data = CATALOG.get(code, CATALOG["GENERIC_ERROR"])
        return ErrorEntry(code, data, server_message)

    @classmethod
    def message(cls, code: str, server_message: Optional[str] = None) -> str:
        return cls.lookup(code, server_message).message

    @classmethod
    def severity(cls, code: str) -> str:
        return cls.lookup(code).severity

    @classmethod
    def is_retryable(cls, code: str) -> bool:
        return cls.lookup(code).retryable

    @classmethod
    def normalize(cls, code: Optional[str], server_message: Optional[str] = None,
                  error: Optional[Exception] = None) -> Dict[str, Any]:
        """Build a normalized error payload from a code (or a server message).

        Rule 5: a real server message passes through verbatim; the catalog is used
        only when the server provides just a code (or nothing).
        """
        if not code:
            code = "GENERIC_ERROR"
        entry = cls.lookup(code, server_message)
        payload = entry.to_dict()
        if error is not None and not payload["message"]:
            payload["message"] = str(error)
        return payload

    _SERVER_CODE_RE = re.compile(r"[A-Z_]{3,}")

    @classmethod
    def from_error(cls, error: Any) -> Dict[str, Any]:
        """Extract a normalized catalog entry from an exception or API error dict."""
        if isinstance(error, dict):
            code = error.get("code", "")
            message = error.get("message") or error.get("error")
            return cls.normalize(code or None, message)
        message = str(error)
        code = None
        match = cls._SERVER_CODE_RE.search(message)
        if match and match.group(0) in CATALOG:
            code = match.group(0)
        return cls.normalize(code, message, error)
