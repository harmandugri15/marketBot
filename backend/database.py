"""
database.py
-----------
SQLAlchemy engine + session factory.
Works with both SQLite (local dev) and PostgreSQL (production).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import get_settings
from typing import Generator

settings = get_settings()


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite needs special connect_args for thread safety
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        return create_engine(url, pool_pre_ping=True)


engine = _make_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables on startup (no-op if they already exist)."""
    from models import signal, trade, backtest_result, forward_test_log  # noqa: F401
    Base.metadata.create_all(bind=engine)
