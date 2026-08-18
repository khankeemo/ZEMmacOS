"""ConfigManager — single owner of every configuration read (SECTION 0D §3).

Branding, colors, company, emails, URLs, API URL, SDK version, and runtime are all
read through this class. No module calls json.load on api-config.json or config.py
getters directly — LicenseEngine builds a ConfigManager in __init__ and everything
else reads the session/config via engine accessors.
"""
from typing import Any, Dict, Optional

from . import config as _config
from .timeout_rules import TimeoutRules

__all__ = ["ConfigManager"]

SDK_VERSION = "1.0.0"
RUNTIME_TYPE = "python"


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None,
                 raw: Optional[Dict[str, Any]] = None):
        if raw is not None:
            self._raw = raw
        else:
            self._raw = _config.load_api_config(config_path)
        self.timeouts = TimeoutRules(self._raw)
        self.sdk_version = self._raw.get("sdk", {}).get("version", SDK_VERSION)
        self.runtime = RUNTIME_TYPE

    # ====================================================================
    # Raw access (the only module allowed)
    # ====================================================================

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    def raw(self) -> Dict[str, Any]:
        return self._raw

    # ====================================================================
    # Section accessors
    # ====================================================================

    def api(self) -> Dict[str, Any]:
        return self._raw.get("api", {}) or {}

    def get_api_url(self) -> str:
        return (self.api().get("url") or "").strip()

    def get_api_version(self) -> str:
        return self.api().get("version", "v1")

    def branding(self) -> Dict[str, Any]:
        return self._raw.get("branding", {}) or {}

    def product(self) -> Dict[str, Any]:
        return self._raw.get("product", {}) or {}

    def get_product_id(self) -> str:
        return self.product().get("id", "")

    def get_product_name(self) -> str:
        return self.branding().get("product_name") or self.product().get("name", "")

    def get_primary_color(self) -> str:
        return self.branding().get("primary_color", "#3b82f6")

    def company(self) -> Dict[str, Any]:
        return self._raw.get("company", {}) or {}

    def get_company_name(self) -> str:
        return self.company().get("company_name", "")

    def get_website_url(self) -> str:
        return self.company().get("website_url", "")

    def emails(self) -> Dict[str, Any]:
        """Email account configuration (branding section; no IMAP/inbound in SDKs).

        Account roles (strict): no_reply = ONE-WAY (outbound only, never a reply
        channel), support/sales = TWO-WAY (contact channels the SDK offers).
        """
        branding = self.branding()
        emails = self._raw.get("emails", {}) or {}
        return {
            "no_reply": emails.get("no_reply") or branding.get("no_reply_email", ""),
            "support": emails.get("support") or branding.get("support_email", ""),
            "sales": emails.get("sales") or branding.get("sales_email", ""),
        }

    def get_no_reply_email(self) -> str:
        """ONE-WAY account — outbound automated mail only; never a reply channel."""
        return (self.emails().get("no_reply") or "").strip()

    def get_support_email(self) -> str:
        """TWO-WAY account — support contact channel."""
        return (self.emails().get("support") or "").strip()

    def get_sales_email(self) -> str:
        """TWO-WAY account — sales contact channel."""
        return (self.emails().get("sales") or "").strip()

    def urls(self) -> Dict[str, Any]:
        return self._raw.get("urls", {}) or {}

    def get_store_url(self) -> str:
        return self.urls().get("store") or _config.get_store_url(self._raw)

    def get_buy_url(self) -> str:
        return self.urls().get("buy") or _config.get_buy_url(self._raw)

    def get_renew_url(self) -> str:
        return self.urls().get("renew") or _config.get_renew_url(self._raw)

    def get_app_url(self) -> str:
        return self.api().get("app_url", "") or self.get_api_url()

    def offline(self) -> Dict[str, Any]:
        return self._raw.get("offline", {}) or {}