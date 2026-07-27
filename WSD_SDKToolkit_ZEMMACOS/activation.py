"""License activation workflow — delegates to LicenseEngine"""
from .license_engine import LicenseEngine, LicenseStatus

__all__ = ["activate_license", "validate_license", "deactivate_license"]


def activate_license(engine: LicenseEngine, license_key: str) -> dict:
    return engine.activate(license_key)


def validate_license(engine: LicenseEngine, license_key: str = "") -> dict:
    return engine.validate(license_key)


def deactivate_license(engine: LicenseEngine, license_key: str = "") -> dict:
    return engine.deactivate(license_key)
