"""
Modèles liés aux matchs (Match, Set, Formations, Changements...).
"""

from dataclasses import dataclass, field

from spyke.domain.entities.personne import PlayerMatch, RefereeMatch
from spyke.domain.enums import MatchStatus, Side, TypeSanction
from spyke.domain.types import (
    CompetitionId,
    DateTime,
    MatchId,
    SeasonId,
    SetNumber,
    TeamMatchId,
    Time,
    VenueId,
)


class Formation:
    position_1: PlayerMatch | None = None  # Arrière droit (serveur)
    position_2: PlayerMatch | None = None  # Avant droit
    position_3: PlayerMatch | None = None  # Avant centre
    position_4: PlayerMatch | None = None  # Avant gauche
    position_5: PlayerMatch | None = None  # Arrière gauche
    position_6: PlayerMatch | None = None  # Arrière centre

    def as_list(self) -> list[PlayerMatch | None]:
        return [
            self.position_1,
            self.position_2,
            self.position_3,
            self.position_4,
            self.position_5,
            self.position_6,
        ]

    def as_dict(self) -> dict[str, PlayerMatch | None]:
        return {
            "I": self.position_1,
            "II": self.position_2,
            "III": self.position_3,
            "IV": self.position_4,
            "V": self.position_5,
            "VI": self.position_6,
        }


@dataclass
class SetScore:
    """Score d'un set de volleyball."""

    score_a: int
    score_b: int

    def __str__(self) -> str:
        return f"{self.score_a}-{self.score_b}"

    @property
    def winner(self) -> Side | None:
        if self.score_a > self.score_b:
            return Side.A
        elif self.score_b > self.score_a:
            return Side.B
        return None


class MatchScore:
    """Score d'un match de volleyball."""

    sets_score: list[SetScore] = field(default_factory=list[SetScore])

    def __str__(self) -> str:
        return "/".join(str(set_score) for set_score in self.sets_score)

    def sets_score_str(self) -> str:
        # Sous forme de sets 3/1
        return f"{self.sets_won(Side.A)}/{self.sets_won(Side.B)}"

    def sets_won(self, side: Side) -> int:
        return sum(1 for set_score in self.sets_score if set_score.winner == side)

    @property
    def winner(self) -> Side | None:
        sets_a = self.sets_won(Side.A)
        sets_b = self.sets_won(Side.B)
        if sets_a > sets_b:
            return Side.A
        elif sets_b > sets_a:
            return Side.B
        return None


@dataclass
class TimeOut:
    """Temps mort demandé."""

    score: SetScore


@dataclass
class Replacement:
    """Changement de joueur pendant un set."""

    player_in: PlayerMatch
    player_out: PlayerMatch
    position: int
    score: SetScore


@dataclass
class SetTeamData:
    """Données d'équipe pour un set (formations, temps morts, changements)."""

    formation: Formation
    timeouts: list[TimeOut]
    replacements: list[Replacement]
    serves: dict[int, list[int]]


@dataclass
class Set:
    """Données d'un set de volleyball."""

    number: SetNumber
    score: SetScore | None = None
    serving_side: Side | None = None
    start: Time | None = None
    end: Time | None = None
    a_team_data: SetTeamData | None = None
    b_team_data: SetTeamData | None = None

    @property
    def score_str(self) -> str:
        return str(self.score) if self.score else "0-0"

    @property
    def winner(self) -> Side | None:
        return self.score.winner if self.score else None

    def team_data(self, side: Side) -> SetTeamData | None:
        if side == Side.A:
            return self.a_team_data
        elif side == Side.B:
            return self.b_team_data


@dataclass
class Sanction:
    """Sanction donnée pendant un match."""

    sanction_type: TypeSanction
    player: PlayerMatch
    score: SetScore


@dataclass
class Match:
    id: MatchId
    code: str

    season_id: SeasonId
    competition_id: CompetitionId
    venue_id: VenueId

    a_team_id: TeamMatchId
    b_team_id: TeamMatchId

    scheduled_at: DateTime
    status: MatchStatus = MatchStatus.UNKNOWN

    sets: list[Set] = field(default_factory=list[Set])

    referees: list[RefereeMatch] = field(default_factory=list[RefereeMatch])
    sanctions: list[Sanction] = field(default_factory=list[Sanction])
    remarks: str | None = None
    score: MatchScore | None = None
    score_pdf: MatchScore | None = None
    journee: int | None = None

    parsed_at: DateTime | None = None

    def team_id(self, side: Side) -> TeamMatchId:
        if side == Side.A:
            return self.a_team_id
        elif side == Side.B:
            return self.b_team_id

    def winner_team_id(self) -> TeamMatchId | None:
        return self.team_id(self.score.winner) if self.score and self.score.winner else None
