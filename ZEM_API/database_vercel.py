"""
Production database configuration for Vercel Postgres
Replace your existing database.py with this for production
"""

import os
from contextlib import contextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Use Vercel Postgres URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_SQLITE_DEV = os.getenv("USE_SQLITE_DEV", "0").lower() in ("1", "true", "yes")

# Fallback to SQLite for local dev
if not DATABASE_URL and USE_SQLITE_DEV:
    _db_path = os.path.join(os.path.dirname(__file__), "zemmacos_dev.db")
    DATABASE_URL = f"sqlite:///{_db_path}"
    print(f"[ZEM API] Using SQLite dev database: {_db_path}")
elif not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required for production")

# SSL required for Vercel Postgres
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    connect_args["sslmode"] = "require"
elif DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yield a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """Context manager for scripts and services."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from models import activation, admin, license, logs, trial
    Base.metadata.create_all(bind=engine)