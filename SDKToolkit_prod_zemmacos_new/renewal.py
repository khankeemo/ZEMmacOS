"""License renewal workflow — delegates to LicenseEngine"""
from .license_engine import LicenseEngine

__all__ = ["renew_license", "verify_license_for_renewal", "get_available_plans", "send_renewal_request"]


def renew_license(engine: LicenseEngine, extra_days: int = 0) -> dict:
    return engine.renew(extra_days)


def verify_license_for_renewal(engine: LicenseEngine, license_key: str) -> dict:
    return engine.verify_license_for_renewal(license_key)


def get_available_plans(engine: LicenseEngine, license_key: str) -> dict:
    return engine.get_available_plans(license_key)


def send_renewal_request(engine: LicenseEngine, **kwargs) -> dict:
    return engine.send_renewal_request(**kwargs)
