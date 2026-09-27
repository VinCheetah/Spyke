from dataclasses import dataclass
from datetime import datetime

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus


@dataclass(frozen=True)
class LeagueRecord:
    external_id: str
    name: str
    code_ffvb: str
    echelon: Echelon


@dataclass(frozen=True)
class ClubRecord:
    external_id: str
    name: str
    code_ffvb: int
    city: str | None = None
    department: str | None = None
    league_external_id: str | None = None


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
