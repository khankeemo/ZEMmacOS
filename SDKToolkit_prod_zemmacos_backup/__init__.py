"""ZEM MAC OS SDK - License Management Client"""
__version__ = "1.0.0"
__all__ = [
    'LicenseEngine', 'LicenseStatus',
    'ApiClient', 'ApiError',
    'HardwareDetector',
    'CacheManager',
    'WelcomeDialog',
    'ActivationDialog',
    'RenewalDialog',
    'DeviceReplaceDialog',
    'DashboardWidget',
    'SettingsWidget',
    'StatusWidget',
    'ActivationButton',
]

from .license_engine import LicenseEngine, LicenseStatus
from .client import ApiClient, ApiError
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog
from .activation import ActivationDialog
from .renewal import RenewalDialog
from .device_replace import DeviceReplaceDialog
from .widgets.dashboard_widget import DashboardWidget
from .widgets.settings_widget import SettingsWidget
from .widgets.status_widget import StatusWidget
from .widgets.activation_button import ActivationButton
