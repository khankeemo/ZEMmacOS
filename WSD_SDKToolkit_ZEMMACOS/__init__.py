"""ZEM MAC OS SDK - License Management Client"""
__version__ = "1.0.0"
__all__ = [
    "ApiClient", "ApiError",
    "LicenseEngine", "LicenseStatus",
    "HardwareDetector",
    "CacheManager",
    "WelcomeDialog",
    "ActivationDialog",
    "RenewalDialog",
    "RenewLicenseDialog",
    "DeviceReplaceDialog",
    "AboutWidget",
    "AboutDialog",
]

from .client import ApiClient, ApiError
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog
from .activation import ActivationDialog
from .renewal import RenewalDialog
from .renew_license_dialog import RenewLicenseDialog
from .device_replace import DeviceReplaceDialog
from .widgets.about import AboutWidget, AboutDialog
