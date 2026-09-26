from typing import TypeAlias
from dataclasses import dataclass
from datetime import date, time, datetime


MatchId: TypeAlias = int
ClubId: TypeAlias = int
TeamMatchId: TypeAlias = int
TeamSeasonId: TypeAlias = int
PersonId: TypeAlias = int
PlayerId: TypeAlias = int
RefereeId: TypeAlias = int
CoachId: TypeAlias = int
CompetitionId: TypeAlias = int
SeasonId: TypeAlias = int
VenueId: TypeAlias = int
LeagueId: TypeAlias = int



@dataclass(frozen=True)
class Coordinate:
    """Représente une coordonnée géographique."""
    latitude: float
    longitude: float
    
    
class Date(date):
    """Classe représentant une date, héritée de datetime.date."""
    pass


class Time(time):
    """Classe représentant une heure, héritée de datetime.time."""
    pass


class DateTime(datetime):
    """Classe représentant une date et une heure, héritée de datetime.datetime."""
    pass


class Jersey(int):
    def __new__(cls, valeur: int):
        # Validation avant la création de l'objet
        entier = super().__new__(cls, valeur)
        if not (0 <= entier <= 99):
            raise ValueError(f"La valeur {entier} est hors de la plage [0..99]")
        return entier


class CodeClub(int):
    def __new__(cls, valeur: int):
        # Validation avant la création de l'objet
        entier = super().__new__(cls, valeur)
        if not (10E6 <= entier < 10E7):
            raise ValueError(f"La valeur {entier} est hors de la plage [1000000..9999999]")
        return entier


class SetNumber(int):
    def __new__(cls, valeur: int):
        # Validation avant la création de l'objet
        entier = super().__new__(cls, valeur)
        if not (1 <= entier <= 5):
            raise ValueError(f"La valeur {entier} est hors de la plage [1..5]")
        return entier