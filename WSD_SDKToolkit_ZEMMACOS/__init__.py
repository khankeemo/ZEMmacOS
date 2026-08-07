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
    "EventBus",
    "WorkflowProgress",
    "GlobalStateMachine",
    "DialogManager",
    "SessionManager",
    "PermissionEngine",
    "ConfigManager",
    "FeatureFlags",
    "OfflineMode",
    "IdempotencyManager",
    "TimeoutRules",
    "CommunicationQueue",
    "NotificationCenter",
    "ErrorCatalog",
    "SecurityRules",
    "MigrationRunner",
    "HealthCheck",
    "MetricsCollector",
    "VersionCompatibility",
    "SupportRequestTracker",
    "RollbackCoordinator",
]

from .client import ApiClient, ApiError, ConnectionUnavailable
from .license_engine import LicenseEngine, LicenseStatus
from .hardware import HardwareDetector
from .cache import CacheManager
from .welcome import WelcomeDialog
from .live_log import LiveLog
from .event_bus import EventBus, LICENSE_STATUS_CHANGED
from .workflow_progress import WorkflowProgress, GlobalStateMachine
from .dialog_manager import DialogManager
from .config_manager import ConfigManager
from .session import SessionManager
from .permissions import PermissionEngine
from .feature_flags import FeatureFlags
from .offline_mode import OfflineMode
from .idempotency import IdempotencyManager
from .timeout_rules import TimeoutRules
from .communication_queue import CommunicationQueue
from .notification_center import NotificationCenter
from .error_catalog import ErrorCatalog
from .security import SecurityRules
from .migration import MigrationRunner
from .health_check import HealthCheck
from .metrics import MetricsCollector
from .version_compat import VersionCompatibility
from .support_workflow import SupportRequestTracker
from .rollback import RollbackCoordinator
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
