from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus, Side
from spyke.infrastructure.database.base import Base, GeoPoint, JsonValue


class SeasonModel(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)

    competitions: Mapped[list["CompetitionModel"]] = relationship(back_populates="season")
    teams: Mapped[list["TeamSeasonModel"]] = relationship(back_populates="season")
    matches: Mapped[list["MatchModel"]] = relationship(back_populates="season")

    __table_args__ = (UniqueConstraint("start_year", name="uq_season_year"),)


class EntityModel(Base):
    __tablename__ = "entity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code_ffvb: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    echelon: Mapped[Echelon] = mapped_column(SAEnum(Echelon, native_enum=False), nullable=False)

    clubs: Mapped[list["ClubModel"]] = relationship(back_populates="entities")
    competitions: Mapped[list["CompetitionModel"]] = relationship(back_populates="organizer")


class ClubModel(Base):
    __tablename__ = "club"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code_ffvb: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    city: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(16))
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entity.id"))
    headquarters_address: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))
    website: Mapped[str | None] = mapped_column(String(500))
    phone_number: Mapped[str | None] = mapped_column(String(32))
    colors: Mapped[list[str]] = mapped_column(JsonValue, nullable=False, default=list)
    coordinate: Mapped[dict[str, float] | None] = mapped_column(GeoPoint)

    entities: Mapped[EntityModel | None] = relationship(back_populates="clubs")
    teams: Mapped[list["TeamSeasonModel"]] = relationship(back_populates="club")


class VenueModel(Base):
    __tablename__ = "venue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(255))
    coordinate: Mapped[dict[str, float] | None] = mapped_column(GeoPoint)

    matches: Mapped[list["MatchModel"]] = relationship(back_populates="venue")


class CompetitionModel(Base):
    __tablename__ = "competition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code_competition: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender, native_enum=False), nullable=False)
    category: Mapped[Category] = mapped_column(SAEnum(Category, native_enum=False), nullable=False)
    echelon: Mapped[Echelon] = mapped_column(SAEnum(Echelon, native_enum=False), nullable=False)
    division: Mapped[Division] = mapped_column(SAEnum(Division, native_enum=False), nullable=False)

    season: Mapped[SeasonModel] = relationship(back_populates="competitions")
    organizer: Mapped[EntityModel] = relationship(back_populates="competitions")
    teams: Mapped[list["TeamSeasonModel"]] = relationship(back_populates="competition")
    matches: Mapped[list["MatchModel"]] = relationship(back_populates="competition")

    __table_args__ = (
        UniqueConstraint("season_id", "code_competition", name="uq_competition_season_code"),
    )


class TeamSeasonModel(Base):
    __tablename__ = "team_season"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competition.id"), nullable=False)
    club_id: Mapped[int] = mapped_column(ForeignKey("club.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    season: Mapped[SeasonModel] = relationship(back_populates="teams")
    competition: Mapped[CompetitionModel] = relationship(back_populates="teams")
    club: Mapped[ClubModel] = relationship(back_populates="teams")
    home_matches: Mapped[list["MatchModel"]] = relationship(
        back_populates="home_team", foreign_keys="MatchModel.home_team_id"
    )
    away_matches: Mapped[list["MatchModel"]] = relationship(
        back_populates="away_team", foreign_keys="MatchModel.away_team_id"
    )

    __table_args__ = (
        UniqueConstraint("season_id", "competition_id", "name", name="uq_team_season_name"),
    )


class MatchModel(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competition.id"), nullable=False)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venue.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("team_season.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("team_season.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus, native_enum=False), nullable=False, default=MatchStatus.UNKNOWN
    )
    home_sets: Mapped[int | None] = mapped_column(Integer)
    away_sets: Mapped[int | None] = mapped_column(Integer)
    remarks: Mapped[str | None] = mapped_column(String(2000))

    season: Mapped[SeasonModel] = relationship(back_populates="matches")
    competition: Mapped[CompetitionModel] = relationship(back_populates="matches")
    venue: Mapped[VenueModel | None] = relationship(back_populates="matches")
    home_team: Mapped[TeamSeasonModel] = relationship(
        back_populates="home_matches", foreign_keys=[home_team_id]
    )
    away_team: Mapped[TeamSeasonModel] = relationship(
        back_populates="away_matches", foreign_keys=[away_team_id]
    )
    sets: Mapped[list["MatchSetModel"]] = relationship(
        back_populates="match", cascade="all, delete-orphan", order_by="MatchSetModel.number"
    )


class MatchSetModel(Base):
    __tablename__ = "match_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    serving_side: Mapped[Side | None] = mapped_column(SAEnum(Side, native_enum=False))

    match: Mapped[MatchModel] = relationship(back_populates="sets")

    __table_args__ = (UniqueConstraint("match_id", "number", name="uq_match_set_number"),)


class SourceDocumentModel(Base):
    """Metadata for one immutable response kept in the raw archive."""

    __tablename__ = "source_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content_type: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    parser_type: Mapped[str | None] = mapped_column(String(128))
    parser_version: Mapped[str | None] = mapped_column(String(64))


class ExternalIdentifierModel(Base):
    """Links a canonical entity to an identifier from an external source."""

    __tablename__ = "external_identifier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_document.id"))

    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "entity_type",
            "external_id",
            name="uq_external_identifier_source_entity",
        ),
    )


class EntityResolutionModel(Base):
    """Auditable result of resolving one external entity reference."""

    __tablename__ = "entity_resolution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_entity_id: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_document.id"))

    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "entity_type",
            "external_id",
            name="uq_entity_resolution_external_reference",
        ),
    )


class ImportRunModel(Base):
    """One resumable execution of an import pipeline."""

    __tablename__ = "import_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ImportStepModel(Base):
    """Progress marker for one stage of an import run."""

    __tablename__ = "import_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_run.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ImportErrorModel(Base):
    """A non-fatal error associated with an import run."""

    __tablename__ = "import_error"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_run.id", ondelete="CASCADE"))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_document.id"))
    entity_type: Mapped[str | None] = mapped_column(String(64))
    external_id: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
