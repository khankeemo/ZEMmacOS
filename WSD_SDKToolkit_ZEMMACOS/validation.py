"""Universal validation for Email, Mobile and OTP — single component used by
every customer-facing flow (Welcome/Trial, Activation, Renewal, customer forms).

Rules:
- Email: real format validation; a green tick appears only when valid.
- Mobile: validated against the selected country's rule (min/max digits)
  served by the API config; the green tick appears only when actually valid.
- OTP: one shared invalid message used by every flow.
"""
import re
from typing import Any, Dict, Optional

EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

OTP_INVALID_MESSAGE = "OTP is not valid."

VALID_TICK = '\u2713'
INVALID_TICK = '\u2716'


def is_valid_email(email: str) -> bool:
    return bool(email and EMAIL_REGEX.match(email.strip()))


def _country_digits(country: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not country:
        return {}
    min_digits = country.get('min_digits', country.get('minDigits'))
    max_digits = country.get('max_digits', country.get('maxDigits'))
    return {
        'min': min_digits if isinstance(min_digits, int) else None,
        'max': max_digits if isinstance(max_digits, int) else None,
    }


def mobile_digits_error(mobile: str, country: Optional[Dict[str, Any]]) -> str:
    """Return an error message for an invalid mobile number, or '' when valid.

    The number is the subscriber part only (dial code excluded). A country
    without published rules imposes no digit-length constraint.
    """
    value = re.sub(r'\s', '', mobile or '')
    if not value:
        return ''
    if not re.fullmatch(r'\d+', value):
        return 'Mobile number must contain digits only.'
    rules = _country_digits(country)
    min_digits = rules.get('min')
    max_digits = rules.get('max')
    if min_digits is not None and max_digits is not None:
        if min_digits == max_digits and len(value) != min_digits:
            return f'Mobile number must be exactly {min_digits} digits.'
        if len(value) < min_digits:
            return f'Mobile number must be at least {min_digits} digits.'
        if len(value) > max_digits:
            return f'Mobile number must be at most {max_digits} digits.'
    return ''


def is_valid_mobile(mobile: str, country: Optional[Dict[str, Any]]) -> bool:
    value = re.sub(r'\s', '', mobile or '')
    return len(value) > 0 and mobile_digits_error(value, country) == ''


class FieldIndicator:
    """Green-tick validation indicator — one visual standard everywhere.

    The tick (✓) is shown only when the value is actually valid; an invalid
    value shows ✗, and an empty field shows nothing.
    """

    def __init__(self, label, success_color: str = '#16a34a',
                 error_color: str = '#dc2626'):
        self._label = label
        self._success_color = success_color
        self._error_color = error_color

    def set_valid(self) -> None:
        try:
            self._label.config(text=VALID_TICK, fg=self._success_color)
        except Exception:
            pass

    def set_invalid(self) -> None:
        try:
            self._label.config(text=INVALID_TICK, fg=self._error_color)
        except Exception:
            pass

    def clear(self) -> None:
        try:
            self._label.config(text='', fg=self._success_color)
        except Exception:
            pass
