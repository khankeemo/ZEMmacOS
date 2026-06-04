"""Health and auth utility routes."""

import os
import time

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from services.dashboard_service import get_dashboard_stats
from services.startup_service import check_database_connection, verify_tables

load_dotenv()

router = APIRouter(tags=["auth"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")
API_VERSION = "1.0.0"


def verify_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return True


@router.get("/health")
def health_check(request: Request, db: Session = Depends(get_db)):
    start = time.perf_counter()
    db_status = check_database_connection()
    tables = verify_tables()
    latency_ms = int((time.perf_counter() - start) * 1000)

    database_state = "connected" if db_status.get("connected") else "disconnected"
    if db_status.get("connected") and not tables.get("all_present"):
        database_state = "connected_tables_pending"

    stats = {}
    if db_status.get("connected"):
        try:
            stats = get_dashboard_stats(db)
        except Exception:
            stats = {}

    return {
        "status": "ok" if db_status.get("connected") else "degraded",
        "service": "ZEM License API",
        "version": API_VERSION,
        "database": database_state,
        "database_type": db_status.get("database_type"),
        "tables_ok": tables.get("all_present", False),
        "tables": tables.get("existing", []),
        "latency_ms": latency_ms,
        "admin_auth": "api_key",
        "stats_preview": {
            "total_licenses": stats.get("total_licenses", 0),
            "active_trials": stats.get("active_trials", 0),
        },
    }
