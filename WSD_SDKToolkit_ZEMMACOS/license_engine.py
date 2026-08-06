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
from .workflow_progress import WorkflowProgress

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
        LiveLog.log(LOG_WORKFLOW_START, f"{self._name} — workflow started")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            if exc_type is None:
                WorkflowProgress.stage(WorkflowProgress.COMPLETED, self._name)
                LiveLog.log(LOG_WORKFLOW_COMPLETE, f"{self._name} — workflow complete")
            else:
                LiveLog.log(LOG_WORKFLOW_ERROR, f"{self._name} — {exc}")
        finally:
            self._engine._workflow_lock.release()
        return False


class LicenseEngine:
    def __init__(self, config_path: Optional[str] = None,
                 on_license_ready: Optional[Callable[[bool], None]] = None):
        self.config = self._load_config(config_path)
        self._hardware = HardwareDetector()
        self._cache = CacheManager(self.config)
        self._client = ApiClient(
            config=self.config,
            hardware=self._hardware,
        )
        self._workflow_lock = threading.RLock()
        self._status: Optional[LicenseStatus] = None
        self._license_key: Optional[str] = None
        self.on_license_ready: Optional[Callable[[bool], None]] = on_license_ready

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

    def is_onboarding_complete(self) -> bool:
        if self._cache.peek_onboarding_complete():
            return True
        return self._cache.is_onboarding_complete()

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
        queue = self._cache.get_message_queue()
        changed = False
        for msg in queue:
            if msg.get('status') == 'sent':
                continue
            now_ts = int(time.time())
            if now_ts < msg.get('next_retry_at', 0):
                continue
            if msg.get('retry_count', 0) >= msg.get('max_retries', 5):
                continue
            msg['status'] = 'sending'
            try:
                self._client.create_communication(
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
                msg['status'] = 'sent'
                changed = True
            except Exception as e:
                msg['retry_count'] = msg.get('retry_count', 0) + 1
                msg['last_error'] = str(e)
                exp_backoff = pow(2, msg['retry_count']) * 60
                msg['next_retry_at'] = now_ts + exp_backoff
                msg['status'] = 'failed'
                changed = True
        if changed:
            self._cache.save_message_queue(queue)
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
        if not status:
            return False
        if status.status == 'trial':
            if status.days_left is not None and status.days_left <= 0:
                return False
            if status.expiry_date:
                try:
                    expiry = datetime.fromisoformat(status.expiry_date.replace('Z', '+00:00'))
                    if expiry.timestamp() < datetime.now().timestamp():
                        return False
                except Exception:
                    pass
        return status.status in ('licensed', 'trial')

    def _build_status_from_unified(self, status_response: Dict[str, Any],
                                   hardware_id: str) -> LicenseStatus:
        """Build a LicenseStatus from the backend's normalized status response.
        All license values come from the backend — nothing is calculated or
        defaulted locally except absent-optional fallbacks."""
        cust = status_response.get('customer', {}) or {}
        lic = status_response.get('license', {}) or {}
        plan = status_response.get('plan', {}) or {}
        product = status_response.get('product', {}) or {}
        devices = status_response.get('devices', {}) or {}
        api_status = status_response.get('status', 'no_license')
        return LicenseStatus(
            valid=True,
            status=api_status,
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
            trial_active=(api_status == 'trial'),
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

    def _build_no_license_decision(self, hardware_id: str) -> LicenseStatus:
        """Local customer-state decision used only when the backend is
        unreachable or has confirmed there is no active license."""
        onboarding_complete = self.is_onboarding_complete()
        has_paid = self._cache.peek_has_ever_activated_paid_license()
        if not has_paid:
            has_paid = self._cache.has_ever_activated_paid_license()

        if onboarding_complete:
            if has_paid:
                LiveLog.log("license.invalid", "Decision — inactive (existing customer with paid history)")
                return LicenseStatus(
                    valid=False, status='inactive',
                    hardware_id=hardware_id,
                    message='License not found or inactive. Please contact your administrator or activate a valid license.'
                )
            LiveLog.log("license.invalid", "Decision — trial_consumed (onboarding complete, no paid license)")
            return LicenseStatus(
                valid=False, status='trial_consumed',
                hardware_id=hardware_id,
                message='Your trial has ended. Please activate a paid license or renew an existing license.'
            )
        LiveLog.log("license.invalid", "Decision — no_license (new customer)")
        return LicenseStatus(
            valid=False, status='no_license',
            hardware_id=hardware_id,
            message='No license or trial was found. Start a Free Trial or activate your license.'
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
        if not status_response.get('success'):
            LiveLog.log("license.offline", "License status endpoint error, using local state")
            return None

        api_status = status_response.get('status', 'no_license')
        if api_status in ('licensed', 'trial'):
            status = self._build_status_from_unified(status_response, hardware_id)
            self._status = status
            self._cache.set_license_status(status.to_dict())
            if not self._license_key and status.license_key:
                self._license_key = status.license_key
            if api_status == 'licensed':
                self._cache.mark_has_ever_activated_paid_license()
            LiveLog.log("license.valid", f"Decision — {api_status} on server (unified API)")
            LiveLog.log(LOG_CACHE_REFRESH, f"Cache refreshed from backend (status: {api_status})")
            return status

        # Server confirmed no active license — never fall back to cached business values.
        self._cache.invalidate_license_status()
        self._cache.clear_license_key()
        self._license_key = None
        LiveLog.log("license.invalid", f"Decision — no active state on server (status={api_status})")
        decision = self._build_no_license_decision(hardware_id)
        self._status = decision
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

        WorkflowProgress.stage(WorkflowProgress.SAVING_CACHE, operation_label)
        if self._status and self._status.valid:
            self._cache.set_license_status(self._status.to_dict())
            if mark_paid:
                self._cache.mark_has_ever_activated_paid_license()
            if mark_onboarding:
                self._cache.set_onboarding_complete()

        if kind == 'activation':
            LiveLog.log(LOG_ACTIVATION_SUCCESS, "License activated successfully")
        elif kind == 'renewal':
            LiveLog.log("RENEWAL_SUCCESS", "License renewed successfully")
        elif kind == 'trial':
            LiveLog.log("trial.success", "Trial activated")

        WorkflowProgress.stage(WorkflowProgress.REFRESHING_SDK, operation_label)
        self._publish_status()
        self._notify_ready(bool(self._status and self._status.valid))

    # ====================================================================
    # Initialization / refresh
    # ====================================================================

    def initialize(self) -> LicenseStatus:
        with self._workflow('initialize'):
            hardware_id = self._hardware.get_fingerprint()
            self._cache.invalidate_if_hardware_mismatch(hardware_id)
            self._process_message_queue()
            LiveLog.log("engine.initialize", f"License Engine initialize — hardware: {hardware_id[:16]}...")

            # Server-first: the backend is the single source of truth while online.
            server_status = self._sync_status_from_server()
            if server_status is not None:
                self._publish_status()
                self._notify_ready(server_status.valid)
                return server_status

            # Backend unreachable — offline fallback to cached local state only.
            saved = self._cache.peek_license_status()
            if saved:
                self._status = LicenseStatus.from_dict(saved)
                if not self._license_key and self._status.license_key:
                    self._license_key = self._status.license_key
                if self._is_valid_status(self._status):
                    LiveLog.log("license.cache", f"Decision — restored from cache (status: {self._status.status})")
                    self._publish_status()
                    self._notify_ready(True)
                    return self._status
                LiveLog.log("license.invalid", f"Decision — cached state found but not valid ({self._status.status})")

            self._status = self._build_no_license_decision(hardware_id)
            self._publish_status()
            self._notify_ready(False)
            return self._status

    def get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

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
            status = self._sync_status_from_server()
            if status is not None:
                self._status = status
                self._publish_status()
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
        WorkflowProgress.stage(WorkflowProgress.CHECKING_LICENSE)
        try:
            result = self._client.validate_license(license_key, hardware_id)
        except ApiError as e:
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
        LiveLog.log(LOG_VALIDATION_ERROR, str(out['message']))
        return out

    def send_otp(self, email: str) -> Dict[str, Any]:
        """Engine-owned OTP send — one path for Welcome, Activation and Renewal."""
        if not email:
            raise ValueError("No registered email was found for this license.")
        WorkflowProgress.stage(WorkflowProgress.SENDING_OTP, email)
        result = self._client.send_otp(email)
        if result.get('success'):
            LiveLog.log(LOG_OTP_SENT, f"OTP sent to {email}")
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
                return {'success': False, 'message': 'OTP is not valid.'}
            raise
        if result.get('success'):
            LiveLog.log(LOG_OTP_VERIFIED, f"OTP verified for {email}")
            WorkflowProgress.stage(WorkflowProgress.OTP_VERIFIED, email)
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
        Fire Event → Refresh Entire SDK → Success."""
        if not license_key:
            raise ValueError("License key unavailable.")
        with self._workflow('activation'):
            LiveLog.log(LOG_ACTIVATION_STARTED, "Activation started")
            WorkflowProgress.stage(WorkflowProgress.CHECKING_HARDWARE, 'activation')
            result = self._client.activate_license(license_key)
            if result.get('success'):
                self._apply_fresh_state(license_key, result, 'activation',
                                        'Activation', mark_onboarding=True)
            else:
                LiveLog.log(LOG_ACTIVATION_SUCCESS, "Activation failed — server response")
            return result

    def reactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        """Reactivation after an admin hardware reset — same activation
        pipeline; the backend performs the rebind (Phase 10)."""
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        with self._workflow('reactivation'):
            LiveLog.log(LOG_ACTIVATION_STARTED, "Reactivation started")
            result = self._client.activate_license(key)
            if result.get('success'):
                self._apply_fresh_state(key, result, 'activation',
                                        'Reactivation', mark_onboarding=True)
            return result

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trial workflow (Phase 8):
        Customer Created → Trial Created → Download Trial → Cache → Event →
        Refresh."""
        if not email:
            raise ValueError("A valid email is required to start a trial.")
        with self._workflow('trial'):
            WorkflowProgress.stage(WorkflowProgress.CHECKING_CUSTOMER, email)
            result = self._client.start_trial(email, customer_name=customer_name, customer_data=customer_data)
            if result.get('success'):
                LiveLog.log("trial.started", "Trial started on server — applying fresh state")
                self._apply_fresh_state(self._license_key or '', result, 'trial',
                                        'Trial', mark_paid=False, mark_onboarding=False)
            return result

    def convert_trial(self, plan: Optional[str] = None, customer_name: str = '',
                      customer_email: str = '') -> Dict[str, Any]:
        """Trial conversion (Phase 8): Trial → Purchase → OTP → Payment →
        Activation → Lock Trial → Convert Record → Create License → Refresh."""
        status = self._status or self.get_status()
        if not status or status.status != 'trial':
            raise RuntimeError("No active trial to convert.")
        with self._workflow('trial_conversion'):
            hardware_id = self._hardware.get_fingerprint()
            result = self._client.convert_trial(hardware_id, plan, customer_name, customer_email)
            if result.get('success'):
                lic = result.get('license', {}) or {}
                self._apply_fresh_state(lic.get('license_key') or '', result,
                                        'conversion', 'Trial Conversion')
            return result

    def get_plans(self) -> Dict[str, Any]:
        return self._client.get_products()

    def renew(self, extra_days: Optional[int] = None,
              license_key: Optional[str] = None) -> Dict[str, Any]:
        """Renewal pipeline (Phase 7): OTP verified → Verify Payment → Renew →
        Update Expiry → Download Status → Refresh Cache → Fire Event →
        Refresh SDK."""
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        with self._workflow('renewal'):
            LiveLog.log("renewal.start", "Renewal started")
            result = self._client.renew_license(key, extra_days)
            if result.get('success'):
                LiveLog.log("renewal.success", "License renewed on server — applying fresh state")
                self._apply_fresh_state(key, result, 'renewal', 'Renewal',
                                        mark_paid=True, mark_onboarding=False)
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
        with self._workflow('hardware_binding'):
            result = self._client.bind_device(key, device_name=device_name)
            if result.get('success'):
                LiveLog.log("hardware.bound", "Device bound on server — applying fresh state")
                self._apply_fresh_state(key, result, 'bind', 'Hardware Binding')
                self._cache.delete('pending_otp')
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
