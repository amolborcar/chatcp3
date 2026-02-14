"""Database engine and session wiring."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

_settings = get_settings()

engine = create_engine(_settings.database_url, echo=_settings.sql_echo, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)


def get_engine():
    """Return the shared SQLAlchemy engine."""

    return engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

