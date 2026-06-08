"""
License API configuration for Websmith backend.

BACKEND URL: https://www.websmithdigital.com/internal/backend
FRONTEND DASHBOARD: https://www.websmithdigital.com/internal/api
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_API_CONFIG = {
    "license_api_url": "https://www.websmithdigital.com/internal/backend",
    "license_api_timeout": 15,
    "offline_grace_hours": 72,
}


def load_api_config() -> dict:
    """Load API configuration - returns dict with license_api_url, timeout, grace hours"""
    config = DEFAULT_API_CONFIG.copy()

    # Note: config.json has been deleted to prevent override
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for key in DEFAULT_API_CONFIG:
                if key in loaded:
                    config[key] = loaded[key]
        except (json.JSONDecodeError, OSError):
            pass

    return config