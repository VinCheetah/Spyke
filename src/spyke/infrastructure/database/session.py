import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker

Session = SQLAlchemySession

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    """Return the configured database URL."""
    return os.getenv("SPYKE_DATABASE_URL", "sqlite:///spyke.db")


def create_database_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured or supplied database URL."""
    return create_engine(url or database_url(), pool_pre_ping=True)


def get_engine(url: str | None = None) -> Engine:
    """Return a lazily created singleton engine, or build one for a custom URL."""
    global _engine

    if url is not None:
        return create_database_engine(url)

    if _engine is None:
        _engine = create_database_engine()

    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return the configured SQLAlchemy session factory."""
    global _SessionLocal

    if engine is not None:
        return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _SessionLocal


def session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Compatibility wrapper for the session factory."""
    return get_session_factory(engine)


class DatabaseSession:
    """Context manager that yields a SQLAlchemy session."""

    def __init__(self, engine: Engine | None = None):
        self.session = get_session_factory(engine)()

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.session.close()


def get_session(engine: Engine | None = None) -> Iterator[Session]:
    """Yield a database session for dependency-injection patterns."""
    session = session_factory(engine)()
    try:
        yield session
    finally:
        session.close()
