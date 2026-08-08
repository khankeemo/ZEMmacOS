"""GlobalMessage — the single source for every SDK user-facing message.

Every workflow step MUST go through GlobalMessage so that the exact text a user
sees is also the exact text written to the shared LiveLog. No module keeps its
own copy of a user-facing string; hardcoded strings in other modules are
replaced by catalog keys.

Categories: startup, validation, otp, trial, activation, renewal, hardware,
license, restart, sales, support, success, warning, error, offline.
"""
from typing import Any, Dict, Optional

from .live_log import LiveLog

__all__ = ["GlobalMessage", "message", "log_message"]

# Category constants (single canonical spelling).
CAT_STARTUP = "startup"
CAT_VALIDATION = "validation"
CAT_OTP = "otp"
CAT_TRIAL = "trial"
CAT_ACTIVATION = "activation"
CAT_RENEWAL = "renewal"
CAT_HARDWARE = "hardware"
CAT_LICENSE = "license"
CAT_RESTART = "restart"
CAT_SALES = "sales"
CAT_SUPPORT = "support"
CAT_SUCCESS = "success"
CAT_WARNING = "warning"
CAT_ERROR = "error"
CAT_OFFLINE = "offline"

ALL_CATEGORIES = (
    CAT_STARTUP, CAT_VALIDATION, CAT_OTP, CAT_TRIAL, CAT_ACTIVATION,
    CAT_RENEWAL, CAT_HARDWARE, CAT_LICENSE, CAT_RESTART, CAT_SALES,
    CAT_SUPPORT, CAT_SUCCESS, CAT_WARNING, CAT_ERROR, CAT_OFFLINE,
)


class _Messages:
    """User-facing message catalog. Values are final strings; callers override
    details (e.g. an email address) via format() arguments."""

    # Startup
    startup_begin = "Starting the Universal License SDK..."
    startup_complete = "Startup complete."
    migration_ok = "Cache upgraded to the current SDK version."
    migration_failed = "Cache upgrade could not be completed. Continuing with defaults."
    engine_initialized = "License Engine initialized."
    session_ready = "Runtime session ready."
    version_compat_ok = "SDK version is compatible with the server."
    version_compat_failed = "This version of the application is no longer supported. Please update to continue."
    instance_locked = "Application instance lock engaged."
    instance_already_running = "Another instance of the Universal License Center is already running. Only one instance may control the licensing workflow."
    instance_lock_failed = "The application lock could not be acquired."
    ulc_opened = "Universal License Center opened."
    ulc_already_open = "Universal License Center is already open."
    ulc_no_status = "No pre-initialised license status was provided. Showing the default welcome state."
    license_launch = "Valid license detected - launching the application directly."
    license_unreachable = "The license server could not be reached. Please check your connection and retry."

    # Validation
    validation_start = "Validating the license with the server..."
    validation_success = "License validated successfully."
    validation_failed = "License validation could not be completed. Please check the license key and try again, or contact support."
    validation_key_required = "Please enter a license key."
    already_activated = "Already activated on this device. Continue using the application."

    # Activation dialog — compact universal phrasing (SECTION 0E). Every message
    # shown in the Activate License flow resolves here; no hardcoded strings.
    ui_validating = "Checking license..."
    ui_license_not_found = "License not found. Please verify your license key."
    ui_customer_not_found = "Customer not found. Please check your email."
    ui_license_inactive = "License is inactive."
    ui_license_revoked = "License has been revoked."
    ui_license_expired = "License has expired. Please renew your license."
    ui_license_active = "License validated successfully."
    ui_sending_otp = "Sending OTP..."
    ui_otp_sent = "OTP sent successfully."
    ui_otp_expires_in = "OTP sent — expires in {0}"
    ui_otp_invalid = "Invalid OTP. Please try again."
    ui_otp_expired = "OTP expired. Request a new OTP."
    ui_otp_verified = "OTP verified successfully."
    ui_binding_hardware = "Binding Hardware..."
    ui_creating_activation = "Creating Activation..."
    ui_updating_license = "Updating License..."
    ui_refreshing_license = "Refreshing License..."
    ui_updating_application = "Updating Application..."
    ui_activation_completed = "License activated successfully."
    ui_enter_license_key = "Enter your license key"
    ui_hardware_hint = "Hardware: {0}"
    ui_otp_label = "Security Code"

    # OTP
    otp_sending = "Sending a one-time password..."
    otp_sent = "One-time password sent. Please check your email."
    otp_verified = "One-time password verified."
    otp_invalid = "OTP is not valid."
    otp_expired = "The one-time password has expired. Request a new one."
    otp_no_email = "No registered email was found for this license."
    otp_required = "Enter the OTP code."

    # Trial
    trial_started = "Your free trial has started."
    trial_success = "Trial started successfully."
    trial_starting = "Starting the free trial..."
    trial_creating = "Creating your trial..."
    trial_created = "Trial created."
    trial_refreshing = "Refreshing the trial licence..."
    trial_consumed = "This email has already used its free trial. Please activate a license or contact sales."
    trial_failed = "The trial could not be started. Please try again or contact support."
    trial_no_email = "A valid email is required to start a trial."
    trial_active = "Your trial is active."

    # Activation
    activation_start = "Activating your license..."
    activation_success = "License activated successfully."
    activation_already = "License already active on this device."
    activation_failed = "Activation could not be completed. The server did not return a reason. Please contact support."
    activation_no_key = "License key unavailable. Please activate first."

    # Renewal
    renewal_start = "Renewing your license..."
    renewal_success = "License renewed successfully."
    renewal_failed = "Renewal could not be completed. The server did not return a reason. Please contact support."
    renewal_no_key = "License key unavailable. Please activate first."

    # Hardware
    hardware_locked = "Hardware replacement requires administrator approval."
    hardware_binding_failed = "This device could not be bound. Please contact support."
    hardware_detected = "Hardware identification complete."
    hardware_mismatch = "Hardware replacement requires administrator approval."

    # License
    license_inactive = "This license is inactive or no longer exists. Please contact your administrator or activate using a valid license."
    license_expired = "Your license has expired. Please renew."
    license_revoked = "Your license has been revoked. Please contact support."
    license_success = "Your licence has been updated successfully. Please restart the application to apply the latest licence information."
    no_license_welcome = "Welcome! No license or trial was found. Please choose one of the options below to continue."

    # Workflow progress (every step resolves through the manager)
    checking_customer = "Checking Customer"
    starting_operation = "Starting..."
    updating_license = "Updating License..."
    refreshing_license = "Refreshing License..."
    saving_cache = "Saving local license data..."

    # Restart
    restarting = "Restarting the application to apply the latest licence information..."
    restart_launched = "The application is restarting."
    restart_failed = "The application could not restart automatically. Please close and reopen it."

    # Sales / Support
    sales_opened = "Sales enquiry opened."
    support_opened = "Support request opened."
    request_submitted = "Your request has been submitted. Our team will contact you."
    request_failed = "The request could not be submitted. Please try again or contact support."

    # Success / Warning / Error / Offline
    operation_success = "Operation completed successfully."
    operation_failed = "The operation could not be completed."
    warning_generic = "Please review the information above."
    error_generic = "An unexpected error occurred. Please try again or contact support."
    offline_mode = "You are offline. Showing the last known licence state; it may be out of date."


class GlobalMessage:
    """Facade over the catalog: one `log()` helper keeps LiveLog and the
    displayed text identical for every workflow step."""

    _catalog = _Messages()

    @classmethod
    def catalog(cls) -> _Messages:
        return cls._catalog

    @classmethod
    def categories(cls) -> tuple:
        return ALL_CATEGORIES

    @classmethod
    def get(cls, key: str, *args: Any, **kwargs: Any) -> str:
        """Resolve a catalog key to its final message string."""
        try:
            value = getattr(cls._catalog, key)
        except AttributeError:
            return key
        if callable(value):
            return str(value(*args, **kwargs))
        if args or kwargs:
            try:
                return str(value).format(*args, **kwargs)
            except (IndexError, KeyError):
                return str(value)
        return str(value)

    @classmethod
    def has(cls, key: str) -> bool:
        return hasattr(cls._catalog, key)

    @classmethod
    def log(cls, category: str, event: str, key: Optional[str] = None,
            message: Optional[str] = None, detail: str = "") -> str:
        """Log a workflow step to LiveLog and return the user-facing message.

        - `event` is the LiveLog event name (e.g. 'startup.begin').
        - `key` is the catalog key for the user-facing text.
        - `message`, when given, overrides the catalog (used to pass through a
          real server-provided message verbatim — Rule 5).
        - `detail` is appended to the LiveLog entry only.

        Returns the exact string that should be displayed.
        """
        user_message = message if message else (cls.get(key) if key else "")
        if detail and user_message:
            LiveLog.log(event, f"{user_message} — {detail}")
        elif user_message:
            LiveLog.log(event, user_message)
        else:
            LiveLog.log(event, detail)
        return user_message


# Convenience module-level helpers (kept thin to avoid import churn).
def message(key: str, *args: Any, **kwargs: Any) -> str:
    return GlobalMessage.get(key, *args, **kwargs)


def log_message(category: str, event: str, key: Optional[str] = None,
                message: Optional[str] = None, detail: str = "") -> str:
    return GlobalMessage.log(category, event, key, message, detail)
