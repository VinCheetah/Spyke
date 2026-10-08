from dataclasses import dataclass
from typing import Protocol

from spyke.infrastructure.fdme.models import ParsedFdme


@dataclass(frozen=True)
class ParserCapabilities:
    """Information availability, never a claim that missing fields are zero."""

    teams: bool = True
    players: bool = False
    coaches: bool = False
    officials: bool = False
    sets: bool = False
    rotations: bool = False
    substitutions: bool = False
    timeouts: bool = False
    sanctions: bool = False
    service_sequence: bool = False
    detailed_rally: bool = False

    def as_set(self) -> frozenset[str]:
        return frozenset(name for name, available in self.__dict__.items() if available)


class FdmeParser(Protocol):
    """Contract implemented by every electronic match-sheet parser."""

    @property
    def parser_type(self) -> str: ...

    @property
    def parser_version(self) -> str: ...

    @property
    def capabilities(self) -> ParserCapabilities: ...

    def detect(self, text: str) -> bool:
        """Return whether this parser recognizes extracted document text."""
        ...

    def parse(self, text: str) -> ParsedFdme:
        """Parse extracted text without performing I/O or database writes."""
        ...
