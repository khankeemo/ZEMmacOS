"""Global Permission Engine — every capability is asked, never assumed (SECTION 0D §2).

UI and dialogs call can_activate() / can_renew() / can_start_trial() /
can_replace_hardware() / can_reset_hardware() / can_contact_support() /
can_upgrade() instead of manually checking license status. Capabilities derive
from session state + feature flags + hardware state.
"""
from typing import Any, Dict, Optional

from .session import SessionManager

__all__ = ["PermissionEngine", "PermissionResult"]


class PermissionResult:
    def __init__(self, allow: bool, reason: str = "", code: str = "",
                 requires_admin: bool = False):
        self.allow = allow
        self.reason = reason
        self.code = code
        self.requires_admin = requires_admin

    @property
    def ok(self) -> bool:
        return self.allow

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "code": self.code,
            "requires_admin": self.requires_admin,
        }

    def __bool__(self) -> bool:
        return self.allow


class PermissionEngine:
    def __init__(self, flags: Any, hardware_state_provider: Any = None):
        self._flags = flags
        self._hardware_state_provider = hardware_state_provider

    # ====================================================================
    # Capabilities
    # ====================================================================

    def can_activate(self) -> PermissionResult:
        if not self._flag("allow_activation", True):
            return PermissionResult(False, "Activation is currently disabled.", "ACTIVATION_DISABLED")
        return PermissionResult(True, "Activation is allowed.")

    def can_renew(self) -> PermissionResult:
        if not self._flag("allow_renewal", True):
            return PermissionResult(False, "Renewal is currently disabled.", "RENEWAL_DISABLED")
        session = SessionManager.get()
        if not session.license.get("license_key"):
            return PermissionResult(False, "Activate a license before renewing.", "NO_LICENSE")
        return PermissionResult(True, "Renewal is allowed.")

    def can_start_trial(self) -> PermissionResult:
        if not self._flag("allow_trial", True):
            return PermissionResult(False, "Free trial is not available for this product.", "TRIAL_DISABLED")
        session = SessionManager.get()
        if session.auth_state in ("licensed", "trial"):
            return PermissionResult(False, "You already have an active license or trial.", "ALREADY_ACTIVE")
        return PermissionResult(True, "Trial is allowed.")

    def can_replace_hardware(self) -> PermissionResult:
        if not self._flag("allow_device_replacement", False):
            return PermissionResult(False, "Hardware replacement requires administrator approval.", "HARDWARE_CHANGED",
                                    requires_admin=True)
        return PermissionResult(False, "Hardware replacement requires administrator approval.", "HARDWARE_CHANGED",
                                requires_admin=True)

    def can_reset_hardware(self) -> PermissionResult:
        if not self._flag("allow_hardware_reset", False):
            return PermissionResult(False, "Hardware reset requires administrator approval.", "HARDWARE_CHANGED",
                                    requires_admin=True)
        return PermissionResult(False, "Hardware reset requires administrator approval.", "HARDWARE_CHANGED",
                                requires_admin=True)

    def can_contact_support(self) -> PermissionResult:
        if not self._flag("allow_communication", True):
            return PermissionResult(False, "Communication is currently disabled.", "COMMUNICATION_DISABLED")
        return PermissionResult(True, "Contacting support is allowed.")

    def can_upgrade(self) -> PermissionResult:
        if not self._flag("allow_upgrade", True):
            return PermissionResult(False, "Upgrades are currently disabled.", "UPGRADE_DISABLED")
        return PermissionResult(True, "Upgrades are allowed.")

    def can_reactivate(self) -> PermissionResult:
        if not self._flag("allow_reactivation", True):
            return PermissionResult(False, "Reactivation is currently disabled.", "REACTIVATION_DISABLED")
        return PermissionResult(True, "Reactivation is allowed.")

    def can_use_offline(self) -> PermissionResult:
        if not self._flag("allow_offline_mode", True):
            return PermissionResult(False, "Offline mode is currently disabled.", "OFFLINE_DISABLED")
        return PermissionResult(True, "Offline mode is allowed.")

    # ====================================================================
    # Helpers
    # ====================================================================

    def _flag(self, name: str, default: bool) -> bool:
        try:
            return bool(self._flags.is_enabled(name, default))
        except Exception:
            return default

    def report(self) -> Dict[str, PermissionResult]:
        return {
            "can_activate": self.can_activate(),
            "can_renew": self.can_renew(),
            "can_start_trial": self.can_start_trial(),
            "can_replace_hardware": self.can_replace_hardware(),
            "can_reset_hardware": self.can_reset_hardware(),
            "can_contact_support": self.can_contact_support(),
            "can_upgrade": self.can_upgrade(),
        }
