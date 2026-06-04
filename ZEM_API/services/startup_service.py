"""Backend startup: DB check, tables, default admin."""

import os

from dotenv import load_dotenv
import hashlib

from sqlalchemy import inspect, text

from database import engine, init_db
from database import SessionLocal

load_dotenv()


def _hash_password(password: str) -> str:
    """Dev-safe password hash (bcrypt optional in production)."""
    salt = os.getenv("ADMIN_PASSWORD_SALT", "zem_admin_salt_v1")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")


def check_database_connection() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "sqlite" if str(engine.url).startswith("sqlite") else "postgresql"
        return {"connected": True, "database_type": db_type, "error": None}
    except Exception as exc:
        return {"connected": False, "database_type": None, "error": str(exc)}


def verify_tables() -> dict:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {"licenses", "activations", "trials", "audit_logs", "admins"}
    missing = required - existing
    return {
        "all_present": len(missing) == 0,
        "existing": sorted(existing),
        "missing": sorted(missing),
    }


def ensure_default_admin() -> dict:
    from models.admin import Admin

    db = SessionLocal()
    try:
        count = db.query(Admin).count()
        if count > 0:
            return {"created": False, "message": f"{count} admin(s) already exist"}
        admin = Admin(
            username=DEFAULT_ADMIN_USER,
            password_hash=_hash_password(DEFAULT_ADMIN_PASS),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"[Backend] Default admin created: {DEFAULT_ADMIN_USER} (dev only — change password)")
        return {
            "created": True,
            "username": DEFAULT_ADMIN_USER,
            "message": "Default development admin created",
        }
    finally:
        db.close()


def run_startup() -> dict:
    """Full startup sequence with logging."""
    result = {"success": True, "steps": []}

    db_status = check_database_connection()
    if db_status["connected"]:
        label = "SQLite" if db_status["database_type"] == "sqlite" else "PostgreSQL"
        print(f"[Backend] {label} connected")
        result["steps"].append("database_connected")
    else:
        print(f"[Backend] Database connection FAILED: {db_status['error']}")
        result["success"] = False
        result["database"] = db_status
        return result

    try:
        init_db()
        print("[Backend] Tables verified/created")
        result["steps"].append("tables_initialized")
    except Exception as exc:
        print(f"[Backend] Table init warning: {exc}")
        result["steps"].append(f"tables_warning:{exc}")

    tables = verify_tables()
    for table in ["licenses", "activations", "trials", "audit_logs", "admins"]:
        if table in tables["existing"]:
            print(f"[Backend] {table.replace('_', ' ').title()} table ready")

    admin_result = ensure_default_admin()
    result["admin"] = admin_result
    result["tables"] = tables
    result["database"] = db_status
    return result
