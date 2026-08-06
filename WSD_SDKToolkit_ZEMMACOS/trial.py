"""Trial management workflow — thin wrapper; ALL logic lives in LicenseEngine"""
from .license_engine import LicenseEngine
from .welcome import WelcomeDialog

__all__ = ["start_trial", "get_trial_status", "convert_trial", "WelcomeDialog"]


def start_trial(engine: LicenseEngine, email: str, customer_name: str = "",
                customer_data: dict = None) -> dict:
    return engine.start_trial(email, customer_name, customer_data)


def get_trial_status(engine: LicenseEngine) -> dict:
    return engine.get_trial_status()


def convert_trial(engine: LicenseEngine, plan: str = "",
                  customer_name: str = "", customer_email: str = "") -> dict:
    return engine.convert_trial(plan, customer_name, customer_email)
