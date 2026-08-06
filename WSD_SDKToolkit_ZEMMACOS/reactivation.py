"""License reactivation workflow — thin wrapper; ALL logic lives in LicenseEngine"""
from .license_engine import LicenseEngine

__all__ = ["reactivate", "send_reactivation_request", "get_reactivation_status"]


def reactivate(engine: LicenseEngine, license_key: str = "") -> dict:
    return engine.reactivate(license_key or None)


def send_reactivation_request(engine: LicenseEngine, **kwargs) -> dict:
    return engine.send_reactivation_request(**kwargs)


def get_reactivation_status(engine: LicenseEngine, license_key: str) -> dict:
    return engine.get_license_details(license_key)
