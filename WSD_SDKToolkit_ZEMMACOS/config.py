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
