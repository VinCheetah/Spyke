from dataclasses import dataclass
from typing import Any

from spyke.domain.enums import Echelon, RoleReferee


class Record:
    """Base class for all records representing data from the FFVB."""

    @property
    def external_id(self) -> str:
        """Return the external identifier for the record."""
        raise NotImplementedError("Subclasses must implement the external_id property.")

    def enrich(self, **kwargs: Any) -> None:
        """Enrich the record with additional attributes."""
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(self, key):
                if getattr(self, key) is None:
                    setattr(self, key, value)
                else:
                    raise ValueError(
                        f"Attribute '{key}' already has a value and cannot be overwritten. (Current value: {getattr(self, key)!r}, New value: {value!r}) of {self.external_id}"
                    )
            else:
                raise AttributeError(f"Attribute '{key}' does not exist on {self.__class__.__name__}.")


@dataclass
class RefereeRecord(Record):
    """Official identity as reported by the FFVB calendar export."""

    licence: str | None
    name: str
    entity: str | None = None
    department: str | None = None
    role: RoleReferee | None = None


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
    committee_code: str | None = None
    league_code: str | None = None
    correspondant: str | None = None
    email: str | None = None
    website: str | None = None
    phone_numbers: list[str] | None = None
    headquarters_address: list[str] | None = None
    colors: str | None = None


@dataclass
class PouleRecord(Record):
    name: str
    code: str | None = None
    division: str | None = None
    tour: str | None = None


@dataclass
class CompetitionRecord(Record):
    name: str
    entity_code: str
    season_start: int
    pools: list[PouleRecord] | None = None


@dataclass
class MatchRecord(Record):
    code: str
    entity: str | None
    a_team: str | None
    b_team: str | None
    a_club_code: str | None
    b_club_code: str | None
    score: tuple[str, str] | None = None
    sets: list[tuple[int, int]] | None = None
    date: str | None = None
    time: str | None = None
    journee: str | None = None
    venue: str | None = None
    referees: list[RefereeRecord] | None = None
    marqueurs: list[RefereeRecord] | None = None
