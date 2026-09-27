"""
Modèles liés aux organisations (Club, Equipe, Saison, Competition).
"""

from dataclasses import dataclass, field

from spyke.domain.entities.personne import CoachMatch, PlayerMatch
from spyke.domain.enums import Category, Division, Echelon, Gender
from spyke.domain.types import (
    ClubId,
    CodeClub,
    CompetitionId,
    Coordinate,
    Date,
    LeagueId,
    MatchId,
    SeasonId,
    TeamMatchId,
    TeamSeasonId,
)


@dataclass
class League:
    """Ligue ou comité organisateur de compétitions."""

    id: LeagueId
    name: str
    code_ffvb: str
    echelon: Echelon


@dataclass
class Season:
    """Données d'une saison sportive."""

    start_date: Date
    end_date: Date

    @property
    def code(self) -> str:
        return f"{self.start_date.year}-{self.end_date.year}"

    @classmethod
    def from_code(cls, code: str) -> "Season":
        """Crée une instance de Season à partir d'un code de saison."""
        try:
            start_year, end_year = map(int, code.split("-"))
            if end_year != start_year + 1:
                raise ValueError
            start_date = Date(start_year, 9, 1)
            end_date = Date(end_year, 8, 31)
            return cls(start_date=start_date, end_date=end_date)
        except Exception as e:
            raise ValueError(f"Code de saison invalide: {code}") from e


@dataclass
class Competition:
    """Données fondamentales d'une compétition."""

    id: CompetitionId
    name: str
    code_competition: str
    organizer_id: LeagueId

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
    league_id: LeagueId | None = None
    comitee_id: LeagueId | None = None
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
