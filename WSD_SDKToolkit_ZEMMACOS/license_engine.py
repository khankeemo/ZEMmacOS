"""LicenseEngine — Universal Workflow Controller (SDK V2 single-state architecture).

The engine is the ONLY module that may:
  - call the API (orchestration),
  - refresh the cache,
  - refresh dashboard / SDK state,
  - update widgets / status,
  - save status,
  - fire status events.

Everything else is either a transport layer (client.py), a storage layer
(cache.py), a fingerprint layer (hardware.py), a UI layer (ULC / welcome /
dialogs), or a thin wrapper (activation.py / renewal.py / trial.py /
reactivation.py / communication.py).

Global pipeline (Phase 2) — every workflow follows it exactly once:
  User Click → Workflow Lock → Validation → OTP → API → Cache Refresh →
  Status Refresh → Event → Entire UI Refresh → Success → Unlock Workflow

Logging (Phase 13) — exactly one entry per stage:
  WORKFLOW_START / VALIDATION_START / VALIDATION_SUCCESS / OTP_SENT /
  OTP_VERIFIED / ACTIVATION_STARTED / ACTIVATION_SUCCESS / CACHE_REFRESH /
  STATUS_CHANGED / WORKFLOW_COMPLETE
"""
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .client import ApiClient, ApiError, ConnectionUnavailable
from .hardware import HardwareDetector
from .cache import CacheManager
from .live_log import LiveLog
from .event_bus import EventBus
from .workflow_progress import WorkflowProgress, GlobalStateMachine
from .config_manager import ConfigManager
from .session import AUTH_ANONYMOUS, SessionManager
from .feature_flags import FeatureFlags
from .idempotency import IdempotencyManager
from .timeout_rules import TimeoutRules
from .permissions import PermissionEngine
from .metrics import MetricsCollector
from .offline_mode import OfflineMode
from .health_check import HealthCheck
from .communication_queue import CommunicationQueue
from .notification_center import NotificationCenter
from .migration import MigrationRunner
from .rollback import RollbackCoordinator
from .support_workflow import SupportRequestTracker
from .version_compat import VersionCompatibility
from .security import SecurityRules, SecurityUnavailableError

logger = logging.getLogger(__name__)

# Canonical one-per-stage log events (Phase 13)
LOG_WORKFLOW_START = "WORKFLOW_START"
LOG_WORKFLOW_COMPLETE = "WORKFLOW_COMPLETE"
LOG_WORKFLOW_ERROR = "WORKFLOW_ERROR"
LOG_VALIDATION_START = "VALIDATION_START"
LOG_VALIDATION_SUCCESS = "VALIDATION_SUCCESS"
LOG_VALIDATION_ERROR = "VALIDATION_ERROR"
LOG_OTP_SENT = "OTP_SENT"
LOG_OTP_VERIFIED = "OTP_VERIFIED"
LOG_ACTIVATION_STARTED = "ACTIVATION_STARTED"
LOG_ACTIVATION_SUCCESS = "ACTIVATION_SUCCESS"
LOG_CACHE_REFRESH = "CACHE_REFRESH"
LOG_STATUS_CHANGED = "STATUS_CHANGED"


class LicenseStatus:
    def __init__(self, valid: bool, status: str, **kwargs):
        self.valid = valid
        self.status = status
        self.expiry_date = kwargs.get('expiry_date')
        self.days_left = kwargs.get('days_left', 0)
        self.plan = kwargs.get('plan')
        self.hardware_id = kwargs.get('hardware_id')
        self.message = kwargs.get('message')
        self.license_key = kwargs.get('license_key')
        self.trial_active = kwargs.get('trial_active', status == 'trial')
        self.customer_name = kwargs.get('customer_name')
        self.customer_email = kwargs.get('customer_email')
        self.customer_phone = kwargs.get('customer_phone')
        self.customer_mobile = kwargs.get('customer_mobile')
        self.product_name = kwargs.get('product_name')
        self.max_devices = kwargs.get('max_devices', 999)
        self.device_count = kwargs.get('device_count', 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'status': self.status,
            'expiry_date': self.expiry_date,
            'days_left': self.days_left,
            'plan': self.plan,
            'hardware_id': self.hardware_id,
            'message': self.message,
            'license_key': self.license_key,
            'trial_active': self.trial_active,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_mobile': self.customer_mobile,
            'product_name': self.product_name,
            'max_devices': self.max_devices,
            'device_count': self.device_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseStatus':
        return cls(
            valid=data.get('valid', False),
            status=data.get('status', 'no_license'),
            expiry_date=data.get('expiry_date'),
            days_left=data.get('days_left', 0),
            plan=data.get('plan'),
            hardware_id=data.get('hardware_id'),
            message=data.get('message'),
            license_key=data.get('license_key'),
            trial_active=data.get('trial_active', data.get('status') == 'trial'),
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email'),
            customer_phone=data.get('customer_phone'),
            customer_mobile=data.get('customer_mobile'),
            product_name=data.get('product_name'),
            max_devices=data.get('max_devices', 999),
            device_count=data.get('device_count', 0),
        )


def _map_universal_status(api_status: str):
    """Map the backend's universal status to the SDK display status + validity.

    Pure render mapping — the backend (database) already decides the license
    state. The SDK only converts the universal status to a display-friendly
    status string and reflects the backend's validity (ACTIVE / TRIAL_ACTIVE
    are the only valid states). No business reasoning happens here.
    """
    valid = api_status in ('ACTIVE', 'TRIAL_ACTIVE')
    display = {
        'ACTIVE': 'licensed',
        'TRIAL_ACTIVE': 'trial',
        'TRIAL_EXPIRED': 'trial_consumed',
        'NO_CUSTOMER': 'no_license',
        'INACTIVE': 'inactive',
        'REVOKED': 'revoked',
        'EXPIRED': 'expired',
    }.get(api_status, 'no_license')
    return display, valid


class _WorkflowGuard:
    """Workflow Lock (Phase 2) + exactly-once stage logging (Phase 13).

    No two workflows can run concurrently; every workflow logs
    WORKFLOW_START once and WORKFLOW_COMPLETE (or WORKFLOW_ERROR) once.
    """

    def __init__(self, engine: 'LicenseEngine', name: str):
        self._engine = engine
        self._name = name

    def __enter__(self) -> '_WorkflowGuard':
        self._engine._workflow_lock.acquire()
        GlobalStateMachine.set(GlobalStateMachine.PROCESSING, self._name)
        LiveLog.log(LOG_WORKFLOW_START, f"{self._name} — workflow started")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            if exc_type is None:
                WorkflowProgress.stage(WorkflowProgress.COMPLETED, self._name)
                GlobalStateMachine.set(GlobalStateMachine.COMPLETED, self._name)
                LiveLog.log(LOG_WORKFLOW_COMPLETE, f"{self._name} — workflow complete")
            else:
                GlobalStateMachine.set(GlobalStateMachine.FAILED, self._name)
                LiveLog.log(LOG_WORKFLOW_ERROR, f"{self._name} — {exc}")
        finally:
            self._engine._workflow_lock.release()
        return False


class LicenseEngine:
    def __init__(self, config_path: Optional[str] = None,
                 on_license_ready: Optional[Callable[[bool], None]] = None):
        self.config = ConfigManager(config_path)
        self._raw_config = self.config.raw()
        self._hardware = HardwareDetector()
        self._cache = CacheManager(self._raw_config)
        try:
            self._cache.enable_security(self._hardware.get_fingerprint())
        except SecurityUnavailableError as e:
            LiveLog.log("SECURITY_UNAVAILABLE", str(e))
        self._client = ApiClient(
            config=self._raw_config,
            hardware=self._hardware,
        )
        self._workflow_lock = threading.RLock()
        self._status: Optional[LicenseStatus] = None
        self._license_key: Optional[str] = None
        self.on_license_ready: Optional[Callable[[bool], None]] = on_license_ready

        # Enterprise suite (SECTION 0D) — utility/derivation layers composed here.
        self.timeouts = self.config.timeouts
        self.feature_flags = FeatureFlags(self._cache)
        self.idempotency = IdempotencyManager(self._cache)
        self.permissions = PermissionEngine(self.feature_flags, self.get_hardware_state)
        self.metrics = MetricsCollector()
        self.offline = OfflineMode(self.timeouts.offline_grace_days)
        self.health = HealthCheck(self, poll_interval_ms=self.timeouts.poll_interval_ms,
                                  timeout_s=self.timeouts.health_timeout_seconds)
        self.comm_queue = CommunicationQueue(self._cache)
        self.notifications = NotificationCenter(self._cache)
        self.migrator = MigrationRunner(self._cache)
        self.rollback = RollbackCoordinator(self)
        self.support_tracker = SupportRequestTracker(self._cache)
        self.version = VersionCompatibility()

        # Run cache migrations on startup (SECTION 0D §13).
        try:
            self.migrator.run()
        except Exception as e:
            LiveLog.log("MIGRATION_ERROR", str(e))

        # Seed the global session with config-derived values.
        SessionManager.set_runtime(self.config.runtime)
        SessionManager.set_sdk_version(self.config.sdk_version)
        self._hardware_fingerprint_cache = None

    def _workflow(self, name: str) -> _WorkflowGuard:
        return _WorkflowGuard(self, name)

    def _notify_ready(self, valid: bool) -> None:
        if self.on_license_ready:
            try:
                self.on_license_ready(valid)
            except Exception:
                pass

    def _publish_status(self) -> None:
        """Fire the single LicenseStatusChanged event (Phase 3). Every screen
        subscribes to EventBus; the engine emits exactly once per mutation."""
        EventBus.emit_status_changed(self._status)
        LiveLog.log(LOG_STATUS_CHANGED,
                    f"Status: {self._status.status if self._status else 'unknown'}")
        WorkflowProgress.stage(WorkflowProgress.REFRESHING_DASHBOARD,
                               self._status.status if self._status else 'unknown')

    # ====================================================================
    # Cache / state helpers (engine-owned — UI never touches cache directly)
    # ====================================================================

    def mark_onboarding_complete(self) -> None:
        self._cache.set_onboarding_complete()

    def set_customer_email(self, email: str) -> None:
        self._cache.set('customer_email', email)

    def get_customer_email(self) -> Optional[str]:
        return self._cache.peek('customer_email') or self._cache.get('customer_email')

    def set_hardware_pending_otp(self, pending: bool = True) -> None:
        """Engine-only flag used by the Hardware State Machine while a rebind
        OTP flow is in progress. Never clears or rebinds the bound hardware."""
        if pending:
            self._cache.set('pending_otp', True)
        else:
            self._cache.delete('pending_otp')

    # ====================================================================
    # Enterprise suite accessors (SECTION 0D) — UI reads via the engine
    # ====================================================================

    def session(self) -> Dict[str, Any]:
        return SessionManager.snapshot()

    def can_activate(self) -> 'PermissionResult':
        return self.permissions.can_activate()

    def can_renew(self) -> 'PermissionResult':
        return self.permissions.can_renew()

    def can_start_trial(self) -> 'PermissionResult':
        return self.permissions.can_start_trial()

    def can_replace_hardware(self) -> 'PermissionResult':
        return self.permissions.can_replace_hardware()

    def can_reset_hardware(self) -> 'PermissionResult':
        return self.permissions.can_reset_hardware()

    def can_contact_support(self) -> 'PermissionResult':
        return self.permissions.can_contact_support()

    def can_upgrade(self) -> 'PermissionResult':
        return self.permissions.can_upgrade()

    def permission_report(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.permissions.report().items()}

    def feature_flags_report(self) -> Dict[str, bool]:
        return self.feature_flags.enabled()

    def metrics_report(self) -> Dict[str, Any]:
        return self.metrics.report()

    def offline_status(self) -> Dict[str, Any]:
        return self.offline.describe()

    def add_notification(self, title: str, body: str = "",
                         severity: str = 'information', source: str = "") -> Dict[str, Any]:
        return self.notifications.add(title, body, severity, source)

    def notifications_list(self, unread_only: bool = False, pinned_only: bool = False,
                           severity: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.notifications.list(unread_only, pinned_only, severity)

    def notifications_unread(self) -> int:
        return self.notifications.unread_count()

    def mark_notification_read(self, notification_id: str) -> bool:
        return self.notifications.mark_read(notification_id)

    def mark_all_notifications_read(self) -> int:
        return self.notifications.mark_all_read()

    def dismiss_notification(self, notification_id: str) -> bool:
        return self.notifications.dismiss(notification_id)

    def pin_notification(self, notification_id: str) -> bool:
        return self.notifications.pin(notification_id)

    def support_requests(self, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.support_tracker.list(stage)

    def track_support_request(self, subject: str, message: str,
                              license_key: str = "") -> Dict[str, Any]:
        key = license_key or self._license_key or ""
        return self.support_tracker.create(subject, message, license_key=key,
                                           hardware_id=self.get_hardware_id(),
                                           customer_email=self.get_customer_email() or "")

    def health_check(self) -> Dict[str, Any]:
        return self.health.check()

    def persist_runtime_state(self) -> None:
        """Persist current runtime state to cache (used pre-restart)."""
        try:
            status = self._status
            if status:
                self._cache.set_license_status(status.to_dict())
                key = self._license_key
                if key:
                    self._cache.save_license_key(key)
                self._cache.set_onboarding_complete()
                LiveLog.log("Runtime state saved", f"Status: {status.status}")
        except Exception as e:
            LiveLog.log("Runtime state save failed", str(e))

    def flush_cache(self) -> None:
        try:
            self._cache.flush()
            LiveLog.log("Cache flushed to disk", "Pre-restart cache write complete")
        except Exception as e:
            LiveLog.log("Cache flush failed", str(e))

    def _process_message_queue(self) -> None:
        """Flush the offline communication queue via the CommunicationQueue
        lifecycle (§0D §8). The engine is transport-only: the deliver callback
        performs the actual API send and returns True on success."""

        def deliver(msg: Dict[str, Any]) -> bool:
            response = self._client.create_communication(
                category=msg.get('category', 'general'),
                customer_email=msg.get('customer_email', ''),
                customer_name=msg.get('customer_name', ''),
                subject=msg.get('subject', ''),
                message=msg.get('message', ''),
                product_id=msg.get('product_id', ''),
                license_key=msg.get('license_key', ''),
                hardware_id=msg.get('hardware_id', self._hardware.get_fingerprint()),
                sdk_version=msg.get('sdk_version', ''),
                runtime_type=msg.get('runtime_type', ''),
            )
            return bool(response.get('success', False))

        stats = self.comm_queue.process(deliver)
        if stats.get('delivered'):
            self._cache.cleanup_sent_messages()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = str(base_dir / 'config' / 'api-config.json')
            if not Path(config_path).exists():
                config_path = str(Path.cwd() / 'config' / 'api-config.json')
        if not Path(config_path).exists():
            raise FileNotFoundError(
                f"api-config.json not found at: {config_path}"
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _is_valid_status(status: Optional[LicenseStatus]) -> bool:
        """Offline display helper — trust the cached backend verdict only.

        The 'valid' flag stored on a cached LicenseStatus originates from the
        backend's universal verdict. Offline, the SDK only displays that last
        server-returned verdict; it never recomputes validity from local data
        (days_left / expiry are not reasoned over by the SDK).
        """
        if not status:
            return False
        return bool(status.valid)

    def _build_status_from_unified(self, status_response: Dict[str, Any],
                                   hardware_id: str) -> LicenseStatus:
        """Build a LicenseStatus from the backend's unified status response.

        The backend verdict is authoritative: the SDK maps the universal status
        to a display status and valid flag, and never decides business state
        locally. All values (customer / license / plan / product / devices /
        message) come from the backend response.
        """
        cust = status_response.get('customer', {}) or {}
        lic = status_response.get('license', {}) or {}
        plan = status_response.get('plan', {}) or {}
        product = status_response.get('product', {}) or {}
        devices = status_response.get('devices', {}) or {}
        api_status = status_response.get('status', 'NO_CUSTOMER')
        message = status_response.get('message') or status_response.get('reason') or ''

        display_status, valid = _map_universal_status(api_status)
        return LicenseStatus(
            valid=valid,
            status=display_status,
            expiry_date=lic.get('expiry_date'),
            days_left=lic.get('days_remaining', lic.get('days_left', 0)),
            plan=plan.get('name') or lic.get('plan'),
            hardware_id=hardware_id,
            license_key=lic.get('license_key', ''),
            product_name=product.get('name'),
            customer_name=cust.get('name'),
            customer_email=cust.get('email'),
            customer_mobile=cust.get('mobile'),
            max_devices=devices.get('maximum', 999),
            device_count=devices.get('current', 0),
            trial_active=(api_status == 'TRIAL_ACTIVE'),
            message=message,
        )

    def _build_offline_status(self, result: Dict[str, Any],
                              status_key: str = 'licensed',
                              license_key: Optional[str] = None) -> LicenseStatus:
        """Local fallback used ONLY when the backend is genuinely unreachable
        (offline). Values come from the raw API response that just succeeded;
        the backend remains the single source of truth once reachable."""
        hardware_id = self._hardware.get_fingerprint()
        if status_key == 'trial':
            trial = result.get('trial') if isinstance(result.get('trial'), dict) else result
            cust = result.get('customer', {}) or {}
            return LicenseStatus(
                valid=True,
                status='trial',
                expiry_date=trial.get('expiry_date'),
                days_left=trial.get('days_remaining', trial.get('days_left', trial.get('duration_days', 0))),
                plan=trial.get('plan'),
                hardware_id=hardware_id,
                license_key=trial.get('license_key') or license_key,
                product_name=self.config.get('product', {}).get('name'),
                customer_name=trial.get('customer_name') or cust.get('name'),
                customer_email=trial.get('customer_email') or cust.get('email'),
                customer_phone=trial.get('customer_phone') or cust.get('phone'),
                customer_mobile=trial.get('customer_mobile') or cust.get('mobile'),
                trial_active=True,
            )
        lic = result.get('license', {}) or {}
        cust = result.get('customer', {}) or {}
        return LicenseStatus(
            valid=True,
            status=status_key,
            expiry_date=lic.get('new_expiry_date') or lic.get('expiry_date'),
            days_left=lic.get('days_remaining', lic.get('days_left', 0)),
            plan=lic.get('plan'),
            hardware_id=hardware_id,
            license_key=lic.get('license_key') or license_key,
            product_name=self.config.get('product', {}).get('name'),
            customer_name=cust.get('name'),
            customer_email=cust.get('email'),
            customer_phone=cust.get('phone'),
            customer_mobile=cust.get('mobile'),
            max_devices=lic.get('max_devices', 999),
            device_count=lic.get('device_count', 0),
        )

    def _render_offline_status(self, hardware_id: str) -> LicenseStatus:
        """Offline (backend unreachable) display status — never a business decision.

        The Global License Status API (database) is the only source of truth for
        license state. When the backend cannot be reached the SDK cannot know the
        customer state, so it renders a neutral offline placeholder for display
        only. It never infers inactive / trial_consumed / no_license from local
        cache or onboarding / paid-history flags.
        """
        self.offline.server_lost(has_valid_cache=False)
        return LicenseStatus(
            valid=False, status='error',
            hardware_id=hardware_id,
            message='The license server could not be reached. Please check your connection and retry.'
        )

    def _sync_status_from_server(self) -> Optional[LicenseStatus]:
        """Fetch authoritative license status from the unified backend endpoint.

        The backend (database) is the single source of truth. When the server
        responds, its status is authoritative: a valid licensed/trial status is
        cached, and any 'no active license' status (not found / inactive /
        revoked / deleted / expired) immediately removes all cached license
        data and local license state.

        Returns:
            LicenseStatus — authoritative server status (valid or not),
            None when the backend is unreachable (offline).
        """
        hardware_id = self._hardware.get_fingerprint()
        try:
            status_response = self._client.get_license_status(hardware_id)
        except ConnectionUnavailable as e:
            LiveLog.log("license.offline", f"Backend unreachable: {e}")
            return None
        if not isinstance(status_response, dict) or not status_response.get('status'):
            LiveLog.log("license.offline", "License status endpoint error, using local state")
            return None

        api_status = status_response.get('status', 'NO_CUSTOMER')

        # Customer Not Found (fresh install / never activated): the backend is
        # the only source of truth. Immediately clear EVERY piece of previous
        # local state — cache, session, license key, trial, customer — so no
        # stale data can ever survive for a brand-new user. The SDK never layers
        # a derived local status on top of this and never writes cache.
        if api_status == 'NO_CUSTOMER':
            self._cache.reset_all()
            self._license_key = None
            SessionManager.set_customer({})
            SessionManager.set_license({})
            SessionManager.set_plan({})
            SessionManager.set_auth_state(AUTH_ANONYMOUS)
            SessionManager.end_workflow()
            LiveLog.log("license.fresh",
                        "Customer not found on server — cleared local cache, session and license state")
            self._status = self._build_status_from_unified(status_response, hardware_id)
            return self._status

        if api_status in ('ACTIVE', 'TRIAL_ACTIVE'):
            status = self._build_status_from_unified(status_response, hardware_id)
            self._status = status
            self._cache.set_license_status(status.to_dict())
            if not self._license_key and status.license_key:
                self._license_key = status.license_key
            LiveLog.log("license.valid", f"Decision — {api_status} on server (unified API)")
            LiveLog.log(LOG_CACHE_REFRESH, f"Cache refreshed from backend (status: {api_status})")
            return status

        # Server confirmed the customer/license state (universal status). The
        # backend verdict is authoritative — the SDK renders it as-is and never
        # infers inactive / trial_consumed / no_license from local cache.
        LiveLog.log("license.invalid", f"Decision — server state on server (status={api_status})")
        decision = self._build_status_from_unified(status_response, hardware_id)
        self._status = decision
        self._cache.set_license_status(decision.to_dict())
        return decision

    def _apply_fresh_state(self, license_key: str, result: Dict[str, Any],
                           kind: str, operation_label: str,
                           mark_paid: bool = True,
                           mark_onboarding: bool = False) -> None:
        """Single post-success pipeline shared by every state-changing workflow
        (Phase 11 — never save cache twice, never sync twice, never fire twice):

        Rule 3 cache reset (activation only) → reload backend status once →
        save cache once → fire event once → notify once.
        """
        if kind == 'activation':
            # Rule 3 (AWS-01): a fresh activation must not inherit any old
            # cached license/customer state. Clear the stale business keys
            # first, then reload the authoritative status from the backend.
            self._cache.reset_on_fresh_activation()
        GlobalStateMachine.set(GlobalStateMachine.PROCESSING, operation_label)
        self._license_key = license_key or self._license_key
        if self._license_key:
            self._cache.save_license_key(self._license_key)

        WorkflowProgress.stage(WorkflowProgress.UPDATING_LICENSE, operation_label)
        server_status = self._sync_status_from_server()
        if server_status is None:
            # Backend unreachable — keep raw response values only.
            status_key = 'trial' if kind == 'trial' else 'licensed'
            self._status = self._build_offline_status(result, status_key, license_key)
            self._cache.set_license_status(self._status.to_dict())

        GlobalStateMachine.set(GlobalStateMachine.REFRESHING, operation_label)
        WorkflowProgress.stage(WorkflowProgress.SAVING_CACHE, operation_label)
        if self._status and self._status.valid:
            self._cache.set_license_status(self._status.to_dict())
            if mark_paid:
                self._cache.mark_has_ever_activated_paid_license()
            if mark_onboarding:
                self._cache.set_onboarding_complete()

        # Seed the global session from the freshly applied state (SECTION 0D §1).
        self._seed_session()

        if kind == 'activation':
            LiveLog.log(LOG_ACTIVATION_SUCCESS, "License activated successfully")
            self.metrics.record_success('activation')
        elif kind == 'renewal':
            LiveLog.log("RENEWAL_SUCCESS", "License renewed successfully")
            self.metrics.record_success('renewal')
        elif kind == 'trial':
            LiveLog.log("trial.success", "Trial activated")
            self.metrics.record_success('trial')
        elif kind in ('bind', 'hardware_binding'):
            LiveLog.log("hardware.bound", "Device bound")
            self.metrics.record_success('hardware_rebind')

        WorkflowProgress.stage(WorkflowProgress.REFRESHING_SDK, operation_label)
        self._publish_status()
        self._notify_ready(bool(self._status and self._status.valid))
        GlobalStateMachine.set(GlobalStateMachine.COMPLETED, operation_label)

    def _seed_session(self) -> None:
        """Write the current status into the global session (SECTION 0D §1)."""
        status = self._status
        if status is None:
            return
        SessionManager.set_customer({
            "name": status.customer_name,
            "email": status.customer_email,
            "mobile": status.customer_mobile or status.customer_phone,
        })
        SessionManager.set_license({
            "license_key": status.license_key,
            "status": status.status,
            "expiry_date": status.expiry_date,
            "days_left": status.days_left,
        })
        SessionManager.set_plan({"name": status.plan, "max_devices": status.max_devices})
        SessionManager.set_auth_state('licensed' if status.status == 'licensed'
                                      else 'trial' if status.status == 'trial'
                                      else 'anonymous')

    # ====================================================================
    # Initialization / refresh
    # ====================================================================

    def initialize(self) -> LicenseStatus:
        with self._workflow('initialize'):
            hardware_id = self._hardware.get_fingerprint()
            # Enable encryption-at-rest with the hardware-bonded key (SECTION 0D §11).
            try:
                self._cache.enable_security(hardware_id)
            except SecurityUnavailableError as e:
                LiveLog.log("SECURITY_UNAVAILABLE", str(e))
            self._cache.invalidate_if_hardware_mismatch(hardware_id)
            self._process_message_queue()
            LiveLog.log("engine.initialize", f"License Engine initialize — hardware: {hardware_id[:16]}...")

            # Seed the global session (SECTION 0D §1).
            SessionManager.set_hardware_id(hardware_id)
            SessionManager.set_product({
                "id": self.config.get_product_id(),
                "name": self.config.get_product_name(),
                "version": self.config.product().get("version", ""),
            })

            # Health + feature flags + version compatibility (SECTIONS 0D §4/§15/§17).
            health = self.health.check()
            if health.get("status") == "ok":
                self.feature_flags.apply_server_payload(health.get("flags"))
            compat = self.version.verify(self, health)
            if not compat.get("ok"):
                self._status = LicenseStatus(
                    valid=False, status='upgrade_required',
                    hardware_id=hardware_id,
                    message=compat.get("message") or 'This version of the application is no longer supported. Please update to continue.',
                )
                self._publish_status()
                self._notify_ready(False)
                return self._status

            # Server-first: the backend is the single source of truth while online.
            server_status = self._sync_status_from_server()
            if server_status is not None:
                self.offline.server_reachable(True)
                self._publish_status()
                self._notify_ready(server_status.valid)
                return server_status

            # Backend unreachable — offline fallback to cached local state only.
            saved = self._cache.peek_license_status()
            if saved:
                self.offline.server_lost(has_valid_cache=True)
                self._status = LicenseStatus.from_dict(saved)
                if not self._license_key and self._status.license_key:
                    self._license_key = self._status.license_key
                if self._is_valid_status(self._status):
                    LiveLog.log("license.cache", f"Decision — restored from cache (status: {self._status.status})")
                    self._publish_status()
                    self._notify_ready(True)
                    return self._status
                LiveLog.log("license.invalid", f"Decision — cached state found but not valid ({self._status.status})")

            self.offline.server_lost(has_valid_cache=False)
            self._status = self._render_offline_status(hardware_id)
            self._publish_status()
            self._notify_ready(False)
            return self._status

    def get_hardware_id(self) -> str:
        if self._hardware_fingerprint_cache is None:
            self._hardware_fingerprint_cache = self._hardware.get_fingerprint()
        return self._hardware_fingerprint_cache

    def get_health(self) -> Dict[str, Any]:
        """Health check transport passthrough (SECTION 0D §15) — non-mutating."""
        try:
            return self._client.get_health()
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'tests': {}}

    def get_status(self) -> Optional[LicenseStatus]:
        return self._status

    def refresh(self) -> Optional[LicenseStatus]:
        """Re-fetch authoritative license status from the backend.

        Single refresh per call: one API call → one cache update → one status
        update → one LicenseStatusChanged event. Returns None only when the
        backend is unreachable (offline) — the caller keeps the current status.
        """
        with self._workflow('refresh'):
            WorkflowProgress.stage(WorkflowProgress.CHECKING_SERVER, 'refresh')
            GlobalStateMachine.set(GlobalStateMachine.REFRESHING, 'status')
            timer = self.metrics.start_timer('refresh')
            status = self._sync_status_from_server()
            if status is not None:
                self._status = status
                self.offline.server_reachable(True)
                self.metrics.record_success('refresh', self.metrics.stop_timer('refresh') or timer)
                self._publish_status()
            else:
                self.offline.server_lost(has_valid_cache=bool(self._cache.peek_license_status()))
                GlobalStateMachine.set(GlobalStateMachine.FAILED, 'refresh')
            return self._status

    def get_license_key(self) -> Optional[str]:
        return self._license_key

    def has_license_key(self) -> bool:
        return self._license_key is not None

    # ====================================================================
    # Validation / OTP (single shared path for every flow)
    # ====================================================================

    def validate_license_key(self, license_key: str,
                             hardware_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate a license key — ONE API call. Returns a structured result:
        {success, validated, already_activated, new_customer, status, license,
         customer, error, message}. The UI never calls the client directly."""
        if not license_key:
            return {'success': False, 'validated': False, 'already_activated': False,
                    'new_customer': False, 'status': '',
                    'license': {}, 'customer': {},
                    'error': {}, 'message': 'Please enter a license key'}
        hardware_id = hardware_id or self._hardware.get_fingerprint()
        LiveLog.log(LOG_VALIDATION_START, "Validating license key")
        GlobalStateMachine.set(GlobalStateMachine.VALIDATING, 'license')
        WorkflowProgress.stage(WorkflowProgress.CHECKING_LICENSE)
        try:
            result = self._client.validate_license(license_key, hardware_id)
        except ApiError as e:
            GlobalStateMachine.set(GlobalStateMachine.FAILED, 'license')
            LiveLog.log(LOG_VALIDATION_ERROR, str(e))
            return {'success': False, 'validated': False, 'already_activated': False,
                    'new_customer': False, 'status': '',
                    'license': {}, 'customer': {},
                    'error': {'message': e.message}, 'message': e.message}
        except Exception as e:
            LiveLog.log(LOG_VALIDATION_ERROR, str(e))
            return {'success': False, 'validated': False, 'already_activated': False,
                    'new_customer': False, 'status': '',
                    'license': {}, 'customer': {},
                    'error': {'message': str(e)}, 'message': str(e)}

        lic = result.get('license', {}) or {}
        cust = result.get('customer', {}) or {}
        err = result.get('error', {}) or {}
        api_status = result.get('status', '')

        out: Dict[str, Any] = {
            'success': True,
            'validated': False,
            'already_activated': bool(result.get('already_activated')),
            'new_customer': False,
            'status': api_status,
            'license': lic,
            'customer': cust,
            'error': err if isinstance(err, dict) else {},
            'message': result.get('message', ''),
        }

        if out['already_activated']:
            LiveLog.log("ALREADY_ACTIVATED", "This device already has this license")
            out['message'] = 'Already activated on this device.'
            return out

        hard_fail = ('expired', 'revoked', 'inactive', 'deleted',
                     'no_license', 'not_found', 'unlicensed')
        out['validated'] = bool(lic) and api_status not in hard_fail
        out['new_customer'] = (not lic) and (not cust) and api_status in ('no_license', 'unlicensed', 'not_found', '')

        if out['validated']:
            LiveLog.log(LOG_VALIDATION_SUCCESS, f"License validated (status: {api_status})")
            return out

        msg = err.get('message') if isinstance(err, dict) else None
        out['message'] = msg or out['message'] or (
            f"License validation could not be completed (status: {api_status}). "
            "Please check the license key and try again, or contact support."
            if api_status else
            "License validation could not be completed. Please check the license key "
            "and try again, or contact support.")
        GlobalStateMachine.set(GlobalStateMachine.FAILED, 'license')
        LiveLog.log(LOG_VALIDATION_ERROR, str(out['message']))
        return out

    def send_otp(self, email: str) -> Dict[str, Any]:
        """Engine-owned OTP send — one path for Welcome, Activation and Renewal."""
        if not email:
            raise ValueError("No registered email was found for this license.")
        GlobalStateMachine.set(GlobalStateMachine.VALIDATING, 'otp-send')
        WorkflowProgress.stage(WorkflowProgress.SENDING_OTP, email)
        result = self._client.send_otp(email)
        if result.get('success'):
            LiveLog.log(LOG_OTP_SENT, f"OTP sent to {email}")
            GlobalStateMachine.set(GlobalStateMachine.OTP_SENT, email)
            WorkflowProgress.stage(WorkflowProgress.OTP_SENT, email)
        return result

    def verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """Engine-owned OTP verification — one shared path. Invalid OTP (4xx)
        is normalized to a result dict so every flow shows the same shared
        message; transport errors still raise for the caller to surface."""
        if not email or not otp:
            raise ValueError("Email and OTP code are required.")
        WorkflowProgress.stage(WorkflowProgress.WAITING_OTP)
        try:
            result = self._client.verify_otp(email, otp)
        except ApiError as e:
            if e.status_code and 400 <= e.status_code < 500:
                GlobalStateMachine.set(GlobalStateMachine.FAILED, 'otp')
                return {'success': False, 'message': 'OTP is not valid.'}
            raise
        if result.get('success'):
            LiveLog.log(LOG_OTP_VERIFIED, f"OTP verified for {email}")
            GlobalStateMachine.set(GlobalStateMachine.OTP_VERIFIED, email)
            WorkflowProgress.stage(WorkflowProgress.OTP_VERIFIED, email)
        else:
            GlobalStateMachine.set(GlobalStateMachine.FAILED, 'otp')
        return result

    def register_customer(self, name: str, email: str, mobile: str,
                          country_code: str, hardware_id: Optional[str] = None,
                          company_name: str = '') -> Dict[str, Any]:
        hardware_id = hardware_id or self._hardware.get_fingerprint()
        return self._client.register_customer(
            name=name, email=email, mobile=mobile,
            country_code=country_code, hardware_id=hardware_id,
            company_name=company_name)

    def get_countries(self) -> Dict[str, Any]:
        return self._client.get_countries()

    def validate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable.")
        result = self.validate_license_key(key)
        if result.get('validated'):
            lic = result.get('license', {})
            if lic.get('license_key'):
                self._license_key = lic['license_key']
            # Backend normalized status is authoritative (single source of truth).
            server_status = self._sync_status_from_server()
            if server_status is None:
                # Offline fallback — keep raw response values only.
                self._status = self._build_offline_status(
                    {'license': lic, 'customer': result.get('customer', {}) or {}},
                    'licensed', self._license_key)
            if self._status and self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def validate_hardware(self) -> Dict[str, Any]:
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.validate_license('', hardware_id)
        if result.get('status') in ('licensed', 'force_reactivation'):
            lic = result.get('license', {})
            cust = result.get('customer', {})
            # Backend normalized status is authoritative (single source of truth).
            server_status = self._sync_status_from_server()
            if server_status is None:
                # Offline fallback — keep raw response values only.
                self._status = self._build_offline_status(
                    {'license': lic, 'customer': cust}, 'licensed', lic.get('license_key'))
            if self._status and self._status.status == 'licensed':
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
                self._publish_status()
                self._notify_ready(True)
                return {'success': True, 'status': self._status.status, 'data': self._status.to_dict()}
            return {'success': True, 'status': 'force_reactivation', 'message': 'License requires reactivation. Contact support.', 'data': self._status.to_dict() if self._status else {}}
        elif result.get('error'):
            err = result.get('error', {})
            err_code = err.get('code', '')
            if err_code == 'LICENSE_EXPIRED':
                return {'success': False, 'valid': False, 'error': {'code': 'LICENSE_EXPIRED', 'message': err.get('message', 'License has expired')}, 'status': 'expired'}
            return {'success': False, 'valid': False, 'error': err, 'status': result.get('status', 'unlicensed')}
        else:
            return {'success': False, 'valid': False, 'error': {'code': 'NO_LICENSE_FOUND', 'message': 'No license found for this hardware'}, 'status': 'unlicensed'}

    # ====================================================================
    # Activation / Renewal / Trial / Reactivation (Phase 6-9 pipelines)
    # ====================================================================

    def activate(self, license_key: str) -> Dict[str, Any]:
        """Activation pipeline (Phase 6):
        Validate → License Found → Customer Found → Hardware Ready →
        (OTP verified by caller) → Bind Hardware → Create Activation →
        Download Latest Status → Clear Local Cache → Save New Cache →
        Fire Event → Refresh Entire SDK → Success.
        Idempotent (SECTION 0D §6): repeated clicks produce ONE activation."""
        if not license_key:
            raise ValueError("License key unavailable.")
        op = self.idempotency.begin('activation')
        if op is None:
            return {'success': False, 'already_activated': True,
                    'message': 'Activation already completed.'}
        with self._workflow('activation'):
            LiveLog.log(LOG_ACTIVATION_STARTED, "Activation started")
            WorkflowProgress.stage(WorkflowProgress.CHECKING_HARDWARE, 'activation')
            result = self._client.activate_license(license_key, idempotency=op.payload())
            if result.get('success'):
                self._apply_fresh_state(license_key, result, 'activation',
                                        'Activation', mark_onboarding=True)
                self.idempotency.complete(op)
            else:
                self.metrics.record_failure('activation')
                LiveLog.log(LOG_ACTIVATION_SUCCESS, "Activation failed — server response")
            return result

    def reactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        """Reactivation after an admin hardware reset — same activation
        pipeline; the backend performs the rebind (Phase 10)."""
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        op = self.idempotency.begin('reactivation')
        with self._workflow('reactivation'):
            LiveLog.log(LOG_ACTIVATION_STARTED, "Reactivation started")
            result = self._client.activate_license(key, idempotency=op.payload() if op else None)
            if result.get('success'):
                self._apply_fresh_state(key, result, 'activation',
                                        'Reactivation', mark_onboarding=True)
                if op:
                    self.idempotency.complete(op)
            else:
                self.metrics.record_failure('activation')
            return result

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trial workflow (Phase 8):
        Customer Created → Trial Created → Download Trial → Cache → Event →
        Refresh."""
        if not email:
            raise ValueError("A valid email is required to start a trial.")
        op = self.idempotency.begin('trial')
        with self._workflow('trial'):
            WorkflowProgress.stage(WorkflowProgress.CHECKING_CUSTOMER, email)
            result = self._client.start_trial(email, customer_name=customer_name,
                                              customer_data=customer_data,
                                              idempotency=op.payload() if op else None)
            if result.get('success'):
                LiveLog.log("trial.started", "Trial started on server — applying fresh state")
                self._apply_fresh_state(self._license_key or '', result, 'trial',
                                        'Trial', mark_paid=False, mark_onboarding=False)
                if op:
                    self.idempotency.complete(op)
            else:
                self.metrics.record_failure('trial')
            return result

    def convert_trial(self, plan: Optional[str] = None, customer_name: str = '',
                      customer_email: str = '') -> Dict[str, Any]:
        """Trial conversion (Phase 8): Trial → Purchase → OTP → Payment →
        Activation → Lock Trial → Convert Record → Create License → Refresh.
        Idempotent (SECTION 0D §6)."""
        status = self._status or self.get_status()
        if not status or status.status != 'trial':
            raise RuntimeError("No active trial to convert.")
        op = self.idempotency.begin('trial_conversion')
        with self._workflow('trial_conversion'):
            hardware_id = self._hardware.get_fingerprint()
            result = self._client.convert_trial(hardware_id, plan, customer_name, customer_email,
                                                idempotency=op.payload() if op else None)
            if result.get('success'):
                lic = result.get('license', {}) or {}
                self._apply_fresh_state(lic.get('license_key') or '', result,
                                        'conversion', 'Trial Conversion')
                self.metrics.record_success('trial_conversion')
                if op:
                    self.idempotency.complete(op)
            else:
                self.metrics.record_failure('trial_conversion')
            return result

    def get_plans(self) -> Dict[str, Any]:
        return self._client.get_products()

    def renew(self, extra_days: Optional[int] = None,
              license_key: Optional[str] = None) -> Dict[str, Any]:
        """Renewal pipeline (Phase 7): OTP verified → Verify Payment → Renew →
        Update Expiry → Download Status → Refresh Cache → Fire Event →
        Refresh SDK. Idempotent (SECTION 0D §6)."""
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        op = self.idempotency.begin('renewal')
        with self._workflow('renewal'):
            LiveLog.log("renewal.start", "Renewal started")
            result = self._client.renew_license(key, extra_days,
                                                idempotency=op.payload() if op else None)
            if result.get('success'):
                LiveLog.log("renewal.success", "License renewed on server — applying fresh state")
                self._apply_fresh_state(key, result, 'renewal', 'Renewal',
                                        mark_paid=True, mark_onboarding=False)
                self.metrics.record_success('renewal')
                if op:
                    self.idempotency.complete(op)
            else:
                self.metrics.record_failure('renewal')
            return result

    def deactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please provide a key.")
        with self._workflow('deactivation'):
            result = self._client.deactivate_license(key)
            if result.get('success'):
                self._cache.reset_all()
                self._status = None
                self._license_key = None
                self._publish_status()
            return result

    def view_hardware_status(self) -> Dict[str, Any]:
        status = {"current_hardware_id": self._hardware.get_fingerprint()}
        cached = self._cache.get_license_status()
        if cached and cached.get('hardware_id'):
            status["registered_hardware_id"] = cached.get('hardware_id')
            status["matched"] = status["current_hardware_id"] == cached.get('hardware_id')
        status["message"] = "Hardware replacement requires administrator approval. Please contact support."
        return status

    def get_hardware_state(self) -> Dict[str, Any]:
        """Hardware State Machine (Phase 10):
        unknown → new → bound → changed → pending_otp → rebound → blocked.

        Read-only derivation: the engine is the only owner of binding state
        (AWS-01 Rule 2 — never bind/unbind/clear hardware locally). A rebind
        only ever happens through the backend after OTP verification.
        """
        current = self._hardware.get_fingerprint()
        cached = self._cache.peek_license_status() or {}
        registered = cached.get('hardware_id')
        cached_status = cached.get('status')
        pending = bool(self._cache.peek('pending_otp'))

        if not cached:
            return {'state': 'pending_otp' if pending else 'unknown',
                    'current_hardware_id': current,
                    'registered_hardware_id': None, 'matched': False}
        if not registered:
            return {'state': 'new', 'current_hardware_id': current,
                    'registered_hardware_id': None, 'matched': False}
        if current == registered:
            return {'state': 'bound', 'current_hardware_id': current,
                    'registered_hardware_id': registered, 'matched': True}
        if pending:
            return {'state': 'pending_otp', 'current_hardware_id': current,
                    'registered_hardware_id': registered, 'matched': False}
        if cached_status in ('force_reactivation', 'blocked'):
            return {'state': 'blocked', 'current_hardware_id': current,
                    'registered_hardware_id': registered, 'matched': False}
        return {'state': 'changed', 'current_hardware_id': current,
                'registered_hardware_id': registered, 'matched': False}

    def bind_device(self, license_key: Optional[str] = None, device_name: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable.")
        op = self.idempotency.begin('hardware_bind')
        with self._workflow('hardware_binding'):
            result = self._client.bind_device(key, device_name=device_name,
                                              idempotency=op.payload() if op else None)
            if result.get('success'):
                LiveLog.log("hardware.bound", "Device bound on server — applying fresh state")
                self._apply_fresh_state(key, result, 'bind', 'Hardware Binding')
                self._cache.delete('pending_otp')
                self.metrics.record_success('hardware_rebind')
                if op:
                    self.idempotency.complete(op)
            else:
                self.metrics.record_failure('hardware_rebind')
            return result

    # ====================================================================
    # Renewal / license details / requests (thin engine passthroughs)
    # ====================================================================

    def verify_license_for_renewal(self, license_key: str) -> Dict[str, Any]:
        return self._client.verify_license_for_renewal(license_key)

    def get_license_details(self, license_key: str) -> Dict[str, Any]:
        return self._client.get_license_details(license_key)

    def get_available_plans(self, license_key: str) -> Dict[str, Any]:
        return self._client.get_available_plans(license_key)

    def send_renewal_request(self, license_key: str, customer_name: str = '',
                             customer_email: str = '', customer_mobile: str = '',
                             message: str = '', request_type: str = 'renew',
                             current_plan_id: str = '', current_plan_name: str = '',
                             requested_plan_id: str = '', requested_plan_name: str = '') -> Dict[str, Any]:
        return self._client.send_request(
            request_type=request_type, customer_name=customer_name,
            customer_email=customer_email, customer_mobile=customer_mobile,
            message=message, license_key=license_key,
            current_plan_id=current_plan_id, current_plan_name=current_plan_name,
            requested_plan_id=requested_plan_id, requested_plan_name=requested_plan_name,
        )

    def send_reactivation_request(self, license_key: str, customer_name: str = '',
                                  customer_email: str = '', message: str = '') -> Dict[str, Any]:
        return self._client.send_reactivation_request(
            license_key=license_key, customer_name=customer_name,
            customer_email=customer_email, message=message,
        )

    def send_support_request(self, license_key: str = '',
                             customer_name: str = '',
                             customer_email: str = '', subject: str = '',
                             message: str = '') -> Dict[str, Any]:
        return self._client.send_support_request(
            license_key=license_key, customer_name=customer_name,
            customer_email=customer_email, subject=subject, message=message,
        )

    def get_request_history(self, email: str) -> Dict[str, Any]:
        return self._client.get_request_history(email)

    def get_trial_status(self) -> Dict[str, Any]:
        return self._client.get_trial_status(self._hardware.get_fingerprint())

    # ====================================================================
    # Universal Communication Engine
    # ====================================================================

    def create_communication(self, category: str = 'general',
                             customer_email: str = '',
                             customer_name: str = '',
                             subject: str = '', message: str = '',
                             product_id: str = '', license_key: str = '',
                             hardware_id: str = '', sdk_version: str = '',
                             runtime_type: str = '') -> Dict[str, Any]:
        try:
            return self._client.create_communication(
                category=category, customer_email=customer_email,
                customer_name=customer_name, subject=subject,
                message=message, product_id=product_id,
                license_key=license_key,
                hardware_id=hardware_id or self._hardware.get_fingerprint(),
                sdk_version=sdk_version, runtime_type=runtime_type,
            )
        except ConnectionUnavailable:
            self._cache.queue_message({
                'category': category, 'customer_email': customer_email,
                'customer_name': customer_name, 'subject': subject,
                'message': message, 'product_id': product_id,
                'license_key': license_key,
                'hardware_id': hardware_id or self._hardware.get_fingerprint(),
                'sdk_version': sdk_version, 'runtime_type': runtime_type,
            })
            return {'success': False, 'message': 'Message queued - will send when online.', 'queued': True}
        except ApiError:
            raise
        except Exception as e:
            self._cache.queue_message({
                'category': category, 'customer_email': customer_email,
                'customer_name': customer_name, 'subject': subject,
                'message': message, 'product_id': product_id,
                'license_key': license_key,
                'hardware_id': hardware_id or self._hardware.get_fingerprint(),
                'sdk_version': sdk_version, 'runtime_type': runtime_type,
            })
            return {'success': False, 'message': 'Message queued - will send when online.', 'queued': True}

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        return self._client.get_conversation(conversation_id)

    def reply_to_conversation(self, conversation_id: str, message: str,
                              customer_name: str = '',
                              customer_email: str = '') -> Dict[str, Any]:
        try:
            return self._client.reply_to_conversation(
                conversation_id, message, customer_name, customer_email)
        except ConnectionUnavailable:
            cached = self._cache.get_license_status() or {}
            self._cache.queue_message({
                'category': 'general',
                'customer_email': customer_email or cached.get('customer_email', ''),
                'customer_name': customer_name or cached.get('customer_name', ''),
                'subject': f'Reply to conversation {conversation_id}',
                'message': message,
            })
            return {'success': False, 'message': 'Reply queued - will send when online.', 'queued': True}
        except ApiError:
            raise

    def list_conversations(self, email: str) -> Dict[str, Any]:
        return self._client.list_conversations(email)

    def get_notifications(self, email: str) -> Dict[str, Any]:
        return self._client.get_notifications(email)

    def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        return self._client.mark_notification_read(notification_id)

    def get_unread_notification_count(self, email: str) -> Dict[str, Any]:
        return self._client.get_unread_notification_count(email)

    def upload_attachment(self, conversation_id: str, file_path: str) -> Dict[str, Any]:
        return self._client.upload_attachment(conversation_id, file_path)
