"""
Optional Google Sheets migration helper (Phase 1/3).
Run from server only — never ship to desktop client.
"""

import os
from typing import Any, Dict

# Reuse logic from legacy backend when service account is configured
GOOGLE_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "ZEMmacOS Licenses")


def is_configured() -> bool:
    return bool(GOOGLE_FILE) and os.path.exists(GOOGLE_FILE)


def migrate_row_to_postgres(db, row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Import a single sheet row into PostgreSQL."""
    from services.license_service import create_license

    return create_license(
        db,
        name=row_data.get("Name", ""),
        email=row_data.get("Email", ""),
        expiry_days=365,
        plan=row_data.get("Plan", "Standard"),
        max_devices=int(row_data.get("Devices", "1") or 1),
        notes=row_data.get("Notes", ""),
        license_key=row_data.get("LicenseKey", ""),
    )
