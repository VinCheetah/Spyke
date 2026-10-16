from dataclasses import dataclass
from datetime import datetime
from typing import Any

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus


class Record:
    """Base class for all records representing data from the FFVB."""

    @property
    def external_id(self) -> str:
        """Return the external identifier for the record."""
        raise NotImplementedError("Subclasses must implement the external_id property.")
    
    # How can i check the type of the attribute to ensure the value is correct ?
    
    def enrich(self, **kwargs: Any) -> None:
        """Enrich the record with additional attributes."""
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(self, key):
                if getattr(self, key) is None:
                    setattr(self, key, value)
                else:
                    raise ValueError(f"Attribute '{key}' already has a value and cannot be overwritten. (Current value: {getattr(self, key)!r}, New value: {value!r}) of {self.external_id}")
            else:
                raise AttributeError(f"Attribute '{key}' does not exist on {self.__class__.__name__}.")


@dataclass
class ArbitreRecord:
    """Official identity as reported by the FFVB calendar export."""

    licence: str | None
    name: str
    entity: str | None = None
    department: str | None = None


@dataclass
class EntityRecord(Record):
    code_ffvb: str
    name: str
    entity_type: Echelon
    num_ffvb: str | None = None
    email: str | None = None
    website: str | None = None
    phone_numbers: list[str] | None = None
    headquarters_address: list[str] | None = None
    president: str | None = None
    parents_code: list[str] | None = None
    clubs_code: list[str] | None = None
    
    @property
    def external_id(self) -> str:
        """Return the external identifier for the entity record."""
        return f"{self.code_ffvb} ({self.name})"


@dataclass
class ClubRecord(Record):
    code_ffvb: str
    name: str
    city: str | None = None
    department: str | None = None
    entity_code_ffvb: str | None = None
    email: str | None = None
    website: str | None = None
    phone_number: str | None = None
    headquarters_address: str | None = None
    colors: list[str] | None = None


@dataclass
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


@dataclass
class MatchRecord:
    external_id: str
    code: str
    competition_external_id: str
    home_club_external_id: str
    away_club_external_id: str
    scheduled_at: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
