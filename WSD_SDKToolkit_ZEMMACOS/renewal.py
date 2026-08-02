"""License renewal workflow — delegates to LicenseEngine"""
from .license_engine import LicenseEngine
from .universal_license_center import UniversalLicenseCenter
from .universal_email_dialog import UniversalEmailDialog

__all__ = ["renew_license", "verify_license_for_renewal", "get_available_plans", "send_renewal_request", "open_renewal_dialog"]


def renew_license(engine: LicenseEngine, extra_days: int = 0) -> dict:
    return engine.renew(extra_days)


def verify_license_for_renewal(engine: LicenseEngine, license_key: str) -> dict:
    return engine.verify_license_for_renewal(license_key)


def get_available_plans(engine: LicenseEngine, license_key: str) -> dict:
    return engine.get_available_plans(license_key)


def send_renewal_request(engine: LicenseEngine, **kwargs) -> dict:
    return engine.send_renewal_request(**kwargs)


def open_renewal_dialog(center: UniversalLicenseCenter) -> None:
    UniversalEmailDialog(center, "Renewal Request", "renewal").show()
