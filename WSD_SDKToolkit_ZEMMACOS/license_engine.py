"""License validation and management engine"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .client import ApiClient
from .hardware import HardwareDetector
from .cache import CacheManager

logger = logging.getLogger(__name__)


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
            'customer_mobile': self.customer_mobile
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseStatus':
        return cls(
            valid=data.get('valid', False),
            status=data.get('status', 'unlicensed'),
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
            customer_mobile=data.get('customer_mobile')
        )


class LicenseEngine:
    def __init__(self, config_path: Optional[str] = None,
                 on_license_ready: Optional[Callable[[bool], None]] = None):
        self.config = self._load_config(config_path)
        self._hardware = HardwareDetector()
        self._cache = CacheManager(self.config)
        self._client = ApiClient(
            config=self.config,
            hardware=self._hardware,
            cache=self._cache
        )
        self._status: Optional[LicenseStatus] = None
        self._license_key: Optional[str] = None
        self.on_license_ready: Optional[Callable[[bool], None]] = on_license_ready
        if not self._license_key:
            self._license_key = self._cache.load_license_key()

    def _notify_ready(self, valid: bool) -> None:
        if self.on_license_ready:
            try:
                self.on_license_ready(valid)
            except Exception:
                pass

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
        return status.status in ('active', 'trial')

    def initialize(self) -> LicenseStatus:
        hardware_id = self._hardware.get_fingerprint()
        self._cache.invalidate_if_hardware_mismatch(hardware_id)
        self._process_message_queue()
        if self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                self._status = LicenseStatus.from_dict(cached)
                if not self._license_key and self._status.license_key:
                    self._license_key = self._status.license_key
                self._notify_ready(self._is_valid_status(self._status))
                return self._status
        try:
            # Priority 1: Validate active paid license from server
            if self._license_key:
                try:
                    result = self._client.validate_license(self._license_key, hardware_id)
                    data = result.get('data', result)
                    if data.get('valid'):
                        status_str = data.get('status', 'active')
                        if status_str == 'expired':
                            self._status = LicenseStatus(
                                valid=False, status='expired',
                                expiry_date=data.get('expiry_date'), days_left=0,
                                plan=data.get('plan'), hardware_id=hardware_id,
                                license_key=self._license_key,
                                message='License has expired. Please renew.',
                                customer_name=data.get('customer_name'),
                                customer_email=data.get('customer_email'),
                            )
                            self._notify_ready(False)
                            return self._status
                        self._status = LicenseStatus(
                            valid=True, status=status_str,
                            expiry_date=data.get('expiry_date'),
                            days_left=data.get('days_left', 0),
                            plan=data.get('plan'), hardware_id=hardware_id,
                            license_key=self._license_key,
                            customer_name=data.get('customer_name'),
                            customer_email=data.get('customer_email'),
                            customer_phone=data.get('customer_phone'),
                            customer_mobile=data.get('customer_mobile'),
                            message='License active'
                        )
                        self._cache.set_license_status(self._status.to_dict())
                        self._cache.mark_has_ever_activated_paid_license()
                        self._notify_ready(True)
                        return self._status
                    else:
                        server_status = data.get('status', '')
                        if server_status == 'expired':
                            self._status = LicenseStatus(
                                valid=False, status='expired',
                                expiry_date=data.get('expiry_date'), days_left=0,
                                plan=data.get('plan'), hardware_id=hardware_id,
                                license_key=self._license_key,
                                message='License has expired. Please renew.'
                            )
                            self._notify_ready(False)
                            return self._status
                        if self._cache.has_ever_activated_paid_license():
                            self._status = LicenseStatus(
                                valid=False, status='force_reactivation',
                                hardware_id=hardware_id, license_key=self._license_key,
                                message='License inactive. Please reactivate.'
                            )
                            self._notify_ready(False)
                            return self._status
                        self._status = LicenseStatus(
                            valid=False, status='force_activation',
                            hardware_id=hardware_id, license_key=self._license_key,
                            message='License key invalid. Please activate.'
                        )
                        self._notify_ready(False)
                        return self._status
                except Exception:
                    if self._cache.has_ever_activated_paid_license():
                        self._status = LicenseStatus(
                            valid=False, status='force_reactivation',
                            hardware_id=hardware_id, license_key=self._license_key,
                            message='License validation failed. Please reactivate.'
                        )
                        self._notify_ready(False)
                        return self._status
                    self._status = LicenseStatus(
                        valid=False, status='force_activation',
                        hardware_id=hardware_id, license_key=self._license_key,
                        message='License validation failed. Please activate.'
                    )
                    self._notify_ready(False)
                    return self._status
            else:
                if self._cache.has_ever_activated_paid_license():
                    self._status = LicenseStatus(
                        valid=False, status='force_reactivation',
                        hardware_id=hardware_id,
                        message='License key missing. Please reactivate.'
                    )
                    self._notify_ready(False)
                    return self._status
            # Priority 2: Check for active trial (only if user never had a paid license)
            if not self._cache.has_ever_activated_paid_license():
                trial_response = self._client.get_trial_status(hardware_id)
                trial_data = trial_response.get('data', {})
                if trial_data.get('has_trial'):
                    status_str = trial_data.get('status', 'trial')
                    if status_str == 'expired':
                        self._status = LicenseStatus(
                            valid=False, status='expired',
                            expiry_date=trial_data.get('expiry_date'), days_left=0,
                            plan=trial_data.get('plan'), hardware_id=hardware_id,
                            message='Trial has expired. Please renew.',
                            customer_name=trial_data.get('customer_name'),
                            customer_email=trial_data.get('customer_email'),
                        )
                        self._notify_ready(False)
                        return self._status
                    self._status = LicenseStatus(
                        valid=status_str == 'active', status=status_str,
                        expiry_date=trial_data.get('expiry_date'),
                        days_left=trial_data.get('days_left', 0),
                        plan=trial_data.get('plan'), hardware_id=hardware_id,
                        message=f"Trial is {status_str}",
                        customer_name=trial_data.get('customer_name'),
                        customer_email=trial_data.get('customer_email'),
                        customer_phone=trial_data.get('customer_phone'),
                        customer_mobile=trial_data.get('customer_mobile')
                    )
                    if self._status.valid:
                        self._cache.set_license_status(self._status.to_dict())
                    self._notify_ready(self._is_valid_status(self._status))
                    return self._status
            # Priority 3: Determine if new customer or force activation
            if self._cache.is_onboarding_complete():
                self._status = LicenseStatus(
                    valid=False, status='force_activation',
                    hardware_id=hardware_id,
                    message='No active license found. Please activate.'
                )
            else:
                self._status = LicenseStatus(
                    valid=False, status='unlicensed',
                    hardware_id=hardware_id,
                    message='No license or trial found'
                )
            self._notify_ready(False)
            return self._status
        except Exception as e:
            logger.exception("Unexpected error during license initialization")
            cached = self._cache.get_license_status()
            if cached:
                status = LicenseStatus.from_dict(cached)
                self._notify_ready(self._is_valid_status(status))
                return status
            self._status = LicenseStatus(
                valid=False, status='error',
                message=f"Unexpected error: {str(e)}"
            )
            self._notify_ready(False)
            return self._status

    def get_hardware_id(self) -> str:
        return self._hardware.get_fingerprint()

    def get_status(self) -> Optional[LicenseStatus]:
        return self._status

    def get_license_key(self) -> Optional[str]:
        return self._license_key

    def has_license_key(self) -> bool:
        return self._license_key is not None

    def validate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please activate first.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.validate_license(key, hardware_id)
        data = result.get('data', result)
        if data.get('valid'):
            if data.get('license_key'):
                self._license_key = data['license_key']
            self._status = LicenseStatus(
                valid=data.get('valid', True),
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=data.get('license_key'),
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(True)
        return result

    def activate(self, license_key: str) -> Dict[str, Any]:
        result = self._client.activate_license(license_key)
        if result.get('success'):
            self._license_key = license_key
            self._cache.save_license_key(license_key)
            data = result.get('data', result)
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=self._hardware.get_fingerprint(),
                license_key=license_key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(True)
        return result

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = self._client.start_trial(email, customer_name=customer_name, customer_data=customer_data)
        if result.get('success'):
            data = result.get('data', result)
            self._status = LicenseStatus(
                valid=True,
                status='trial',
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', data.get('duration_days', 0)),
                plan=data.get('plan', 'Trial'),
                hardware_id=self._hardware.get_fingerprint(),
                customer_name=data.get('customer_name') or customer_name,
                customer_email=data.get('customer_email') or email,
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
            self._notify_ready(self._is_valid_status(self._status))
        return result

    def convert_trial(self, plan: Optional[str] = None, customer_name: str = '', customer_email: str = '') -> Dict[str, Any]:
        status = self.initialize()
        if not status or status.status != 'trial':
            raise RuntimeError("No active trial to convert.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.convert_trial(hardware_id, plan, customer_name, customer_email)
        if result.get('success'):
            data = result.get('data', result)
            if 'license_key' in data:
                self._license_key = data.get('license_key')
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=data.get('license_key'),
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(self._is_valid_status(self._status))
        return result

    def get_plans(self) -> Dict[str, Any]:
        return self._client.get_products()

    def renew(self, extra_days: Optional[int] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable. Please activate first.")
        result = self._client.renew_license(self._license_key, extra_days)
        if result.get('success'):
            data = result.get('data', result)
            hardware_id = self._hardware.get_fingerprint()
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('new_expiry_date') or data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=self._license_key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile')
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
            self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(self._is_valid_status(self._status))
        return result

    def deactivate(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable. Please provide a key.")
        result = self._client.deactivate_license(key)
        if result.get('success'):
            self._cache.invalidate_license_status()
            self._status = None
            if license_key is None:
                self._license_key = None
                self._cache.clear_license_key()
        return result

    def replace_hardware(self, device_name: Optional[str] = None) -> Dict[str, Any]:
        if not self._license_key:
            raise ValueError("License key unavailable. Please activate first.")
        new_hardware_id = self._hardware.get_fingerprint()
        old_hardware_id = None
        if self._status and self._status.hardware_id:
            old_hardware_id = self._status.hardware_id
        if not old_hardware_id:
            cached = self._cache.get_license_status()
            if cached and cached.get('hardware_id'):
                old_hardware_id = cached.get('hardware_id')
        if not old_hardware_id:
            raise RuntimeError("Current hardware_id unavailable. Cannot replace device.")
        if old_hardware_id == new_hardware_id:
            return {'success': False, 'message': 'Old and new hardware IDs are identical.'}
        result = self._client.replace_device(
            license_key=self._license_key,
            new_hardware_id=new_hardware_id,
            old_hardware_id=old_hardware_id,
            device_name=device_name
        )
        if result.get('success'):
            self._cache.invalidate_license_status()
            data = result.get('data', result)
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=new_hardware_id,
                license_key=self._license_key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile'),
                message='Hardware replaced'
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(self._is_valid_status(self._status))
        return result

    def bind_device(self, license_key: Optional[str] = None, device_name: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable.")
        result = self._client.bind_device(key, device_name=device_name)
        if result.get('success'):
            self._license_key = key
            data = result.get('data', result)
            hardware_id = self._hardware.get_fingerprint()
            self._status = LicenseStatus(
                valid=True,
                status=data.get('status', 'active'),
                expiry_date=data.get('expiry_date'),
                days_left=data.get('days_left', 0),
                plan=data.get('plan'),
                hardware_id=hardware_id,
                license_key=key,
                customer_name=data.get('customer_name'),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                customer_mobile=data.get('customer_mobile'),
                message='Device bound'
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
            self._notify_ready(self._is_valid_status(self._status))
        return result

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
        except Exception as e:
            self._cache.queue_message({
                'category': category, 'customer_email': customer_email,
                'customer_name': customer_name, 'subject': subject,
                'message': message, 'product_id': product_id,
                'license_key': license_key,
                'hardware_id': hardware_id or self._hardware.get_fingerprint(),
                'sdk_version': sdk_version, 'runtime_type': runtime_type,
            })
            return {'success': False, 'message': 'Message queued for delivery when online.', 'queued': True}

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        return self._client.get_conversation(conversation_id)

    def reply_to_conversation(self, conversation_id: str, message: str,
                              customer_name: str = '',
                              customer_email: str = '') -> Dict[str, Any]:
        try:
            return self._client.reply_to_conversation(
                conversation_id, message, customer_name, customer_email)
        except Exception:
            cached = self._cache.get_license_status() or {}
            self._cache.queue_message({
                'category': 'general',
                'customer_email': customer_email or cached.get('customer_email', ''),
                'customer_name': customer_name or cached.get('customer_name', ''),
                'subject': f'Reply to conversation {conversation_id}',
                'message': message,
            })
            return {'success': False, 'message': 'Reply queued for delivery when online.', 'queued': True}

    def list_conversations(self, email: str) -> Dict[str, Any]:
        return self._client.list_conversations(email)

    def get_notifications(self, email: str) -> Dict[str, Any]:
        return self._client.get_notifications(email)

    def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        return self._client.mark_notification_read(notification_id)

    def get_unread_notification_count(self, email: str) -> Dict[str, Any]:
        return self._client.get_unread_notification_count(email)
