"""
Modèles liés aux organisations (Club, Equipe, Saison, Competition).
"""

from dataclasses import dataclass, field

from spyke.domain.entities.personne import CoachMatch, PlayerMatch
from spyke.domain.enums import Category, Division, Echelon, Gender
from spyke.domain.rules.categorisation import get_echelon_from_code_ffvb
from spyke.domain.types import (
    ClubId,
    CodeClub,
    CompetitionId,
    Coordinate,
    Date,
    EntityId,
    MatchId,
    SeasonId,
    TeamMatchId,
    TeamSeasonId,
)


@dataclass
class Entity:
    """Ligue ou comité organisateur de compétitions."""

    id: EntityId
    code: str
    name: str

    @property
    def echelon(self) -> Echelon:
        """Returns the echelon based on the FFVB code."""
        return get_echelon_from_code_ffvb(self.code)

    def __str__(self) -> str:
        return self.code


@dataclass
class Season:
    """Données d'une saison sportive."""

    start_year: int

    @property
    def end_year(self) -> int:
        return self.start_year + 1

    @property
    def start_date(self) -> Date:
        return Date(self.start_year, 9, 1)

    @property
    def end_date(self) -> Date:
        return Date(self.end_year, 8, 31)

    @property
    def code(self) -> str:
        return f"{self.start_year}/{self.end_year}"

    @property
    def short_code(self) -> str:
        return f"{str(self.start_year)[-2:]}/{str(self.end_year)[-2:]}"

    @classmethod
    def from_code(cls, code: str) -> "Season":
        """Crée une instance de Season à partir d'un code de saison."""
        try:
            start_year, end_year = map(int, code.split("-"))
            if end_year != start_year + 1:
                raise ValueError(f"Code de saison invalide: {code}")
            return cls(start_year=start_year)
        except Exception as e:
            raise ValueError(f"Code de saison invalide: {code}") from e

    def __str__(self) -> str:
        return self.code


@dataclass
class Competition:
    """Données fondamentales d'une compétition."""

    id: CompetitionId
    name: str
    code_competition: str
    organizer_id: EntityId

    gender: Gender
    category: Category
    echelon: Echelon
    division: Division


@dataclass
class Club:
    """Club de volleyball."""

    id: ClubId
    name: str
    code_ffvb: CodeClub
    city: str | None
    departement: str | None
    league_id: EntityId | None = None
    comitee_id: EntityId | None = None
    adresse_siege: str | None = None
    email: str | None = None
    website: str | None = None
    phone_number: str | None = None
    colors: list[str] = field(default_factory=list[str])
    president: str | None = None
    correspondant_name: str | None = None
    coordinate: Coordinate | None = None


@dataclass
class TeamMatch:
    """Équipe participant à une compétition."""

    id: TeamMatchId
    name: str
    match_id: MatchId
    captain: PlayerMatch
    players: list[PlayerMatch]
    liberos: list[PlayerMatch]
    coachs: list[CoachMatch]


@dataclass
class TeamSeason:
    """Équipe pour une saison spécifique."""

    id: TeamSeasonId
    season_id: SeasonId
    competition_id: CompetitionId
    club_id: ClubId
