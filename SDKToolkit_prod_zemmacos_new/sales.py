"""Sales enquiry workflow — delegates to LicenseEngine and UniversalLicenseCenter"""
from .license_engine import LicenseEngine
from .universal_license_center import UniversalLicenseCenter

__all__ = ["send_sales_enquiry", "open_sales_dialog"]


def send_sales_enquiry(engine: LicenseEngine, **kwargs) -> dict:
    return engine.create_communication(category="sales", **kwargs)


def open_sales_dialog(center: UniversalLicenseCenter) -> None:
    center._sales_enquiry()
