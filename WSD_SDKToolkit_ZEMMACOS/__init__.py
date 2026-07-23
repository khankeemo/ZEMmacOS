"""ZEM MAC OS SDK - Universal License Center"""
__version__ = "1.0.0"
__all__ = [
    "UniversalLicenseCenter",
    "UniversalEmailDialog",
    "LicenseEngine", "LicenseStatus",
    "ApiClient", "ApiError",
    "HardwareDetector",
    "CacheManager",
]

from .client import ApiClient, ApiError
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .universal_license_center import UniversalLicenseCenter
from .universal_email_dialog import UniversalEmailDialog
