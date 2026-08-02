"""Universal SDK — License Center, API client, hardware detection, and messaging"""
__version__ = "1.0.0"
__all__ = [
    "UniversalLicenseCenter",
    "UniversalEmailDialog",
    "WelcomeDialog",
    "SuccessDialog",
    "RestartDialog",
    "LicenseEngine", "LicenseStatus",
    "ApiClient", "ApiError", "ConnectionUnavailable",
    "HardwareDetector",
    "CacheManager",
    "LiveLog",
    "SingleInstance",
]

from .client import ApiClient, ApiError, ConnectionUnavailable
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog
from .live_log import LiveLog
from .universal_license_center import UniversalLicenseCenter
from .universal_email_dialog import UniversalEmailDialog
from .universal_success_dialog import SuccessDialog
from .universal_restart_dialog import RestartDialog
from .single_instance import SingleInstance

from . import activation
from . import renewal
from . import reactivation
from . import trial
from . import communication
from . import notifications
from . import support
from . import sales
from . import config
