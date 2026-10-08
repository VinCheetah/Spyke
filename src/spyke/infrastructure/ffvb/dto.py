from dataclasses import dataclass
from datetime import datetime

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus


class Record:
    """Base class for all records representing data from the FFVB."""

    @property
    def external_id(self) -> str:
        """Return the external identifier for the record."""
        raise NotImplementedError("Subclasses must implement the external_id property.")


@dataclass(frozen=True)
class ArbitreRecord:
    """Official identity as reported by the FFVB calendar export."""

    licence: str | None
    name: str
    entity: str | None = None
    department: str | None = None


@dataclass(frozen=True)
class EntityRecord(Record):
    code_ffvb: str
    name: str


@dataclass(frozen=True)
class ClubRecord(Record):
    code_ffvb: str
    name: str
    city: str | None = None
    department: str | None = None
    entity_code_ffvb: str | None = None


@dataclass(frozen=True)
class CompetitionRecord:
    external_id: str
    name: str
    code: str
    season_start: int
    season_end: int
    organizer_external_id: str
    gender: Gender
    category: Category
    echelon: Echelon
    division: Division


@dataclass(frozen=True)
class MatchRecord:
    external_id: str
    code: str
    competition_external_id: str
    home_club_external_id: str
    away_club_external_id: str
    scheduled_at: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
