"""License reactivation workflow — delegates to LicenseEngine"""
from .license_engine import LicenseEngine

__all__ = ["send_reactivation_request", "get_reactivation_status"]


def send_reactivation_request(engine: LicenseEngine, **kwargs) -> dict:
    return engine.send_reactivation_request(**kwargs)


def get_reactivation_status(engine: LicenseEngine, license_key: str) -> dict:
    return engine.get_license_details(license_key)
