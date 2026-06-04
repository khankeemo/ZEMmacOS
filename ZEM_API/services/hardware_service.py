"""Hardware ID normalization and validation helpers."""

import re
from typing import List


def normalize_hardware_id(hardware_id: str) -> str:
    return hardware_id.strip().upper() if hardware_id else ""


def normalize_key(key: str) -> str:
    return key.strip().upper() if key else ""


def normalize_email(email: str) -> str:
    return email.strip().lower() if email else ""


def normalize_name(name: str) -> str:
    return name.strip().lower() if name else ""


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def parse_hardware_list(stored: str) -> List[str]:
    if not stored:
        return []
    return [h.strip().upper() for h in stored.split(",") if h.strip()]
