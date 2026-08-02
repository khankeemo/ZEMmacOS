"""Support request workflow — delegates to LicenseEngine and UniversalLicenseCenter"""
from .license_engine import LicenseEngine
from .universal_license_center import UniversalLicenseCenter
from .universal_email_dialog import UniversalEmailDialog

__all__ = ["send_support_request", "open_support_dialog"]


def send_support_request(engine: LicenseEngine, **kwargs) -> dict:
    return engine.send_support_request(**kwargs)


def open_support_dialog(center: UniversalLicenseCenter) -> None:
    UniversalEmailDialog(center, "Contact Support", "support").show()
