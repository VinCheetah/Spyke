"""
Modèles liés aux personnes (Joueur, Arbitre, Officiel).
"""
from dataclasses import dataclass
from typing import Optional


from spyke.domain.types import Jersey, MatchId, PersonId, PlayerId, RefereeId, CoachId, LeagueId
from src.spyke.domain.enums import RoleCoach, RoleReferee


@dataclass
class Person:
    """Données identitaires d'une personne (indépendamment de son rôle)."""
    name: str
    surname: str
    licence: Optional[int]

    @property
    def complete_name(self) -> str:
        return f"{self.name} {self.surname}"


class Player:
    id: PlayerId
    person_id: PersonId
    

class Referee:
    id: RefereeId
    person_id: PersonId
    ligue: Optional[str] = None


class Coach:
    id: CoachId
    person_id: PersonId
    

class PlayerMatch:
    player_id: PlayerId
    match_id: MatchId
    jersey: Jersey
    is_captain: bool = False
    is_libero: bool = False
    
    
class RefereeMatch:
    referee_id: RefereeId
    match_id: MatchId
    league_id: LeagueId
    role: RoleReferee
    
    
class CoachMatch:
    coach_id: CoachId
    match_id: MatchId
    role: RoleCoach