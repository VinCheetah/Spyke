"""
Modèles liés aux personnes (Joueur, Arbitre, Officiel).
"""

from dataclasses import dataclass

from spyke.domain.enums import RoleCoach, RoleReferee
from spyke.domain.types import CoachId, EntityId, Jersey, MatchId, PersonId, PlayerId, RefereeId


@dataclass
class Person:
    """Données identitaires d'une personne (indépendamment de son rôle)."""

    name: str
    surname: str
    licence: int | None

    @property
    def complete_name(self) -> str:
        return f"{self.name} {self.surname}"


@dataclass
class Player:
    id: PlayerId
    person_id: PersonId


@dataclass
class Referee:
    id: RefereeId
    person_id: PersonId
    ligue: str | None = None


@dataclass
class Coach:
    id: CoachId
    person_id: PersonId


@dataclass
class PlayerMatch:
    player_id: PlayerId
    match_id: MatchId
    jersey: Jersey
    is_captain: bool = False
    is_libero: bool = False


@dataclass
class RefereeMatch:
    referee_id: RefereeId
    match_id: MatchId
    league_id: EntityId
    role: RoleReferee


@dataclass
class CoachMatch:
    coach_id: CoachId
    match_id: MatchId
    role: RoleCoach
