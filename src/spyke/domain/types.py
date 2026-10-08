from dataclasses import dataclass
from datetime import date, datetime, time

type MatchId = int
type ClubId = int
type TeamMatchId = int
type TeamSeasonId = int
type PersonId = int
type PlayerId = int
type RefereeId = int
type CoachId = int
type CompetitionId = int
type SeasonId = int
type VenueId = int
type EntityId = int


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
        if not (1_000_000 <= entier < 10_000_000):
            raise ValueError(f"La valeur {entier} est hors de la plage [1000000..9999999]")
        return entier


class SetNumber(int):
    def __new__(cls, valeur: int):
        # Validation avant la création de l'objet
        entier = super().__new__(cls, valeur)
        if not (1 <= entier <= 5):
            raise ValueError(f"La valeur {entier} est hors de la plage [1..5]")
        return entier
