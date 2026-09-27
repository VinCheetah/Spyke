from collections.abc import Iterator
from typing import Any

from sqlalchemy import JSON, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator, TypeEngine


class JsonValue(TypeDecorator[Any]):
    """Use JSONB on PostgreSQL while keeping SQLite useful for local tests."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class GeoPoint(TypeDecorator[Any]):
    """PostGIS point in production, JSON latitude/longitude in SQLite tests."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            from geoalchemy2 import Geometry

            return dialect.type_descriptor(Geometry("POINT", srid=4326, spatial_index=False))
        return dialect.type_descriptor(JSON())


def model_modules() -> Iterator[object]:
    """Import mapped classes so metadata and Alembic see every table."""

    from spyke.infrastructure.database import models

    yield models
