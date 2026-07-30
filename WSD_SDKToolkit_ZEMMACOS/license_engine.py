"""License validation and management engine"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .client import ApiClient, ApiError, ConnectionUnavailable
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

    def initialize(self) -> LicenseStatus:
        hardware_id = self._hardware.get_fingerprint()
        self._cache.invalidate_if_hardware_mismatch(hardware_id)
        self._process_message_queue()
        print(f"[{time.strftime('%H:%M:%S')}] License Engine initialize — hardware: {hardware_id[:16]}...")

        saved = self._cache.peek_license_status()
        if saved:
            self._status = LicenseStatus.from_dict(saved)
            if not self._license_key and self._status.license_key:
                self._license_key = self._status.license_key
            if self._is_valid_status(self._status):
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — restored from cache (status: {self._status.status})")
                self._notify_ready(True)
                return self._status
            print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — cached state found but not valid ({self._status.status})")

        if self._cache.is_valid():
            cached = self._cache.get_license_status()
            if cached:
                self._status = LicenseStatus.from_dict(cached)
                if not self._license_key and self._status.license_key:
                    self._license_key = self._status.license_key
                if self._is_valid_status(self._status):
                    print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — cache hit (status: {self._status.status})")
                    self._notify_ready(True)
                    return self._status
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — cache hit (status: {self._status.status}), not valid, falling through")

        # Cache missed — ask server via unified license status endpoint
        try:
            status_response = self._client.get_license_status(hardware_id)
            if status_response.get('success'):
                api_status = status_response.get('status', 'no_license')
                if api_status in ('licensed', 'trial'):
                    cust = status_response.get('customer', {})
                    lic = status_response.get('license', {})
                    plan = status_response.get('plan', {})
                    product = status_response.get('product', {})
                    devices = status_response.get('devices', {})
                    self._status = LicenseStatus(
                        valid=True,
                        status=api_status,
                        expiry_date=lic.get('expiry_date'),
                        days_left=lic.get('days_remaining', 0),
                        plan=plan.get('name'),
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
                    self._cache.set_license_status(self._status.to_dict())
                    if api_status == 'licensed' and self._status.license_key:
                        self._license_key = self._status.license_key
                        self._cache.mark_has_ever_activated_paid_license()
                    print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — {api_status} on server (unified API)")
                    self._notify_ready(True)
                    return self._status
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — no active state on server (status={api_status})")
            else:
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — server returned error, falling through")
        except Exception as e:
            print(f"{time.strftime('%H:%M:%S')} LiveLog: Warning — unified license status check failed: {e}")

        # Final decision: server confirmed no active state exists
        onboarding_complete = self._cache.is_onboarding_complete()
        if not onboarding_complete:
            onboarding_complete = self._cache.peek_onboarding_complete()
        has_paid = self._cache.has_ever_activated_paid_license()
        if not has_paid and onboarding_complete:
            has_paid = self._cache.peek_has_ever_activated_paid_license()

        if onboarding_complete:
            if has_paid:
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — inactive (existing customer with paid history)")
                self._status = LicenseStatus(
                    valid=False, status='inactive',
                    hardware_id=hardware_id,
                    message='Your license is inactive. Activate a new license or contact support.'
                )
            else:
                print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — trial_consumed (onboarding complete, no paid license)")
                self._status = LicenseStatus(
                    valid=False, status='trial_consumed',
                    hardware_id=hardware_id,
                    message='Your trial has ended. Please activate a paid license or renew an existing license.'
                )
        else:
            print(f"{time.strftime('%H:%M:%S')} LiveLog: Decision — no_license (new customer)")
            self._status = LicenseStatus(
                valid=False, status='no_license',
                hardware_id=hardware_id,
                message='No license or trial was found. Start a Free Trial or activate your license.'
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
            raise ValueError("License key unavailable.")
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.validate_license(key, hardware_id)
        if result.get('status') in ('licensed',):
            lic = result.get('license', {})
            cust = result.get('customer', {})
            if lic.get('license_key'):
                self._license_key = lic['license_key']
            self._status = LicenseStatus(
                valid=True,
                status='licensed',
                expiry_date=lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=hardware_id,
                license_key=lic.get('license_key'),
                product_name=self.config.get('product', {}).get('name'),
                customer_name=cust.get('name'),
                customer_email=cust.get('email'),
                customer_phone=cust.get('phone'),
                customer_mobile=cust.get('mobile'),
                max_devices=lic.get('max_devices', 999),
                device_count=lic.get('device_count', 0),
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
        return result

    def activate(self, license_key: str) -> Dict[str, Any]:
        result = self._client.activate_license(license_key)
        if result.get('success'):
            self._license_key = license_key
            self._cache.save_license_key(license_key)
            lic = result.get('license', {})
            cust = result.get('customer', {})
            self._status = LicenseStatus(
                valid=True,
                status=result.get('status', 'licensed'),
                expiry_date=lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=self._hardware.get_fingerprint(),
                license_key=license_key,
                product_name=self.config.get('product', {}).get('name'),
                customer_name=cust.get('name'),
                customer_email=cust.get('email'),
                customer_phone=cust.get('phone'),
                customer_mobile=cust.get('mobile'),
                max_devices=lic.get('max_devices', 999),
                device_count=lic.get('device_count', 0),
            )
            if self._status.valid:
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
                self._cache.set_onboarding_complete()
            self._notify_ready(True)
        return result

    def validate_hardware(self) -> Dict[str, Any]:
        hardware_id = self._hardware.get_fingerprint()
        result = self._client.validate_license('', hardware_id)
        if result.get('status') in ('licensed', 'force_reactivation'):
            lic = result.get('license', {})
            cust = result.get('customer', {})
            self._status = LicenseStatus(
                valid=result.get('status') == 'licensed',
                status=result.get('status', 'licensed'),
                expiry_date=lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=hardware_id,
                license_key=lic.get('license_key'),
                product_name=self.config.get('product', {}).get('name'),
                customer_name=cust.get('name'),
                customer_email=cust.get('email'),
                customer_phone=cust.get('phone'),
                customer_mobile=cust.get('mobile'),
                max_devices=lic.get('max_devices', 999),
                device_count=lic.get('device_count', 0),
            )
            if self._status.status == 'licensed':
                self._cache.set_license_status(self._status.to_dict())
                self._cache.mark_has_ever_activated_paid_license()
                self._notify_ready(True)
                return {'success': True, 'status': self._status.status, 'data': self._status.to_dict()}
            return {'success': True, 'status': 'force_reactivation', 'message': 'License requires reactivation. Contact support.', 'data': self._status.to_dict()}
        elif result.get('error'):
            err = result.get('error', {})
            err_code = err.get('code', '')
            if err_code == 'LICENSE_EXPIRED':
                return {'success': False, 'valid': False, 'error': {'code': 'LICENSE_EXPIRED', 'message': err.get('message', 'License has expired')}, 'status': 'expired'}
            return {'success': False, 'valid': False, 'error': err, 'status': result.get('status', 'unlicensed')}
        else:
            return {'success': False, 'valid': False, 'error': {'code': 'NO_LICENSE_FOUND', 'message': 'No license found for this hardware'}, 'status': 'unlicensed'}

    def start_trial(self, email: str, customer_name: str = '',
                    customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = self._client.start_trial(email, customer_name=customer_name, customer_data=customer_data)
        if result.get('success'):
            trial_data = result.get('trial', {}) if isinstance(result.get('trial'), dict) else result
            customer_data = customer_data or {}
            self._status = LicenseStatus(
                valid=True,
                status='trial',
                expiry_date=trial_data.get('expiry_date'),
                days_left=trial_data.get('days_left', trial_data.get('duration_days', 0)),
                plan=trial_data.get('plan'),
                hardware_id=self._hardware.get_fingerprint(),
                product_name=self.config.get('product', {}).get('name'),
                customer_name=trial_data.get('customer_name') or customer_name,
                customer_email=trial_data.get('customer_email') or email,
                customer_phone=trial_data.get('customer_phone'),
                customer_mobile=trial_data.get('customer_mobile') or customer_data.get('mobile')
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
            lic = result.get('license', {})
            if 'license_key' in lic:
                self._license_key = lic.get('license_key')
            self._status = LicenseStatus(
                valid=True,
                status=result.get('status', 'licensed'),
                expiry_date=lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=hardware_id,
                license_key=lic.get('license_key'),
                product_name=self.config.get('product', {}).get('name'),
                customer_name=result.get('customer', {}).get('name'),
                customer_email=result.get('customer', {}).get('email'),
                customer_phone=result.get('customer', {}).get('phone'),
                customer_mobile=result.get('customer', {}).get('mobile')
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
            lic = result.get('license', {})
            hardware_id = self._hardware.get_fingerprint()
            self._status = LicenseStatus(
                valid=True,
                status='licensed',
                expiry_date=lic.get('new_expiry_date') or lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=hardware_id,
                license_key=self._license_key,
                product_name=self.config.get('product', {}).get('name'),
                customer_name=result.get('customer', {}).get('name'),
                customer_email=result.get('customer', {}).get('email'),
                customer_phone=result.get('customer', {}).get('phone'),
                customer_mobile=result.get('customer', {}).get('mobile')
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
            self._cache.reset_all()
            self._status = None
            self._license_key = None
        return result

    def view_hardware_status(self) -> Dict[str, Any]:
        status = {"current_hardware_id": self._hardware.get_fingerprint()}
        cached = self._cache.get_license_status()
        if cached and cached.get('hardware_id'):
            status["registered_hardware_id"] = cached.get('hardware_id')
            status["matched"] = status["current_hardware_id"] == cached.get('hardware_id')
        status["message"] = "Hardware replacement requires administrator approval. Please contact support."
        return status

    def bind_device(self, license_key: Optional[str] = None, device_name: Optional[str] = None) -> Dict[str, Any]:
        key = license_key or self._license_key
        if not key:
            raise ValueError("License key unavailable.")
        result = self._client.bind_device(key, device_name=device_name)
        if result.get('success'):
            self._license_key = key
            lic = result.get('license', {})
            hardware_id = self._hardware.get_fingerprint()
            self._status = LicenseStatus(
                valid=True,
                status='licensed',
                expiry_date=lic.get('expiry_date'),
                days_left=lic.get('days_left', 0),
                plan=lic.get('plan'),
                hardware_id=hardware_id,
                license_key=key,
                product_name=self.config.get('product', {}).get('name'),
                customer_name=result.get('customer', {}).get('name'),
                customer_email=result.get('customer', {}).get('email'),
                customer_phone=result.get('customer', {}).get('phone'),
                customer_mobile=result.get('customer', {}).get('mobile'),
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
