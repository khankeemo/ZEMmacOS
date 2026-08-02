"""License activation workflow — delegates to LicenseEngine"""
from .license_engine import LicenseEngine, LicenseStatus
from .universal_license_center import UniversalLicenseCenter
from .universal_email_dialog import UniversalEmailDialog

__all__ = ["activate_license", "validate_license", "deactivate_license", "open_activation_dialog"]


def activate_license(engine: LicenseEngine, license_key: str) -> dict:
    return engine.activate(license_key)


def validate_license(engine: LicenseEngine, license_key: str = "") -> dict:
    return engine.validate(license_key)


def deactivate_license(engine: LicenseEngine, license_key: str = "") -> dict:
    return engine.deactivate(license_key)


def open_activation_dialog(center: UniversalLicenseCenter) -> None:
    UniversalEmailDialog(center, "Activation Request", "activation").show()
