"""License API configuration — loaded from config.json (no secrets)."""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_API_CONFIG = {
    "license_api_url": "https://api.websmithdigital.com",
    "license_api_timeout": 15,
    "offline_grace_hours": 72,
}


def load_api_config() -> dict:
    config = DEFAULT_API_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for key in DEFAULT_API_CONFIG:
                if key in loaded:
                    config[key] = loaded[key]
        except (json.JSONDecodeError, OSError):
            pass
    env_url = os.environ.get("ZEM_LICENSE_API_URL")
    if env_url:
        config["license_api_url"] = env_url.rstrip("/")
    return config
