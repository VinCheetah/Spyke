from sqlalchemy import select
from sqlalchemy.orm import Session

from spyke.infrastructure.database import session as database_session


def test_database_session_factory_and_context_manager_work() -> None:
    factory = database_session.get_session_factory()
    assert callable(factory)

    db = database_session.DatabaseSession()
    session = db.__enter__()
    try:
        assert isinstance(session, Session)
        assert session.bind is not None
        assert session.execute(select(1)).scalar_one() == 1
    finally:
        db.__exit__(None, None, None)
