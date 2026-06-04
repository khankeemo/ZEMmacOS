"""PostgreSQL database connection and session management."""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Set USE_SQLITE_DEV=1 in .env for local dev without PostgreSQL
USE_SQLITE_DEV = os.getenv("USE_SQLITE_DEV", "1").lower() in ("1", "true", "yes")

if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
elif USE_SQLITE_DEV:
    _db_path = os.path.join(os.path.dirname(__file__), "zemmacos_dev.db")
    DATABASE_URL = f"sqlite:///{_db_path}"
    print(f"[ZEM API] Using SQLite dev database: {_db_path}")
else:
    DB_USER = os.getenv("DB_USER", "Keemo")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "zemmacos")
    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False, connect_args=connect_args)
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
    from models import activation, admin, license, logs, trial  # noqa: F401

    Base.metadata.create_all(bind=engine)
