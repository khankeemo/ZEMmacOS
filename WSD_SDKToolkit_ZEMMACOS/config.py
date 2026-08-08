"""Configuration loading and branding — delegates to LicenseEngine and api-config.json"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = ["load_api_config", "get_branding", "get_product_info"]


def load_api_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    cfg_paths = [
        os.path.join(os.path.dirname(__file__), "config", "api-config.json"),
        os.path.join(os.getcwd(), "config", "api-config.json"),
    ]
    for cfg_path in cfg_paths:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return {}


def get_branding(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("branding", {})


def get_product_info(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("product", {})


def get_store_url(config: Dict[str, Any]) -> str:
    """Backwards-compatible store URL accessor. Prefers the dedicated Buy
    portal URL (store.buy_url) and falls back to the generic store.url."""
    return get_buy_url(config)


def get_buy_url(config: Dict[str, Any]) -> str:
    """Central location for the Buy License portal URL (opens the Universal
    Buy portal /internal/api/buy). Used by every Buy License button."""
    store = config.get("store", {}) or {}
    return (store.get("buy_url") or store.get("url") or "").strip()


def get_renew_url(config: Dict[str, Any]) -> str:
    """Central location for the Renew License portal URL (opens the Universal
    Renew portal /internal/api/renew). Used by every Renew License button."""
    store = config.get("store", {}) or {}
    return (store.get("renew_url") or store.get("url") or "").strip()
