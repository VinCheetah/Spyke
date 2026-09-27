import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    return os.getenv("SPYKE_DATABASE_URL", "sqlite:///spyke.db")


def create_database_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url(), pool_pre_ping=True)


def session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or create_database_engine(), expire_on_commit=False)


def get_session(engine: Engine | None = None) -> Iterator[Session]:
    session = session_factory(engine)()
    try:
        yield session
    finally:
        session.close()
