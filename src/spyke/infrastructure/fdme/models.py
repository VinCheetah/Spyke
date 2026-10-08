from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedPlayer:
    """Player appearance as reported by a match sheet."""

    name: str
    jersey: int | None = None
    license_number: str | None = None
    captain: bool = False
    libero: bool = False


@dataclass(frozen=True)
class ParsedOfficial:
    name: str
    role: str
    license_number: str | None = None


@dataclass(frozen=True)
class ParsedTeam:
    """One side of a parsed match, without canonical database identities."""

    name: str
    external_id: str | None = None
    players: tuple[ParsedPlayer, ...] = ()
    coaches: tuple[ParsedOfficial, ...] = ()


@dataclass(frozen=True)
class ParsedSet:
    number: int
    score_a: int
    score_b: int


@dataclass(frozen=True)
class ParsedMatch:
    code: str | None
    team_a: ParsedTeam
    team_b: ParsedTeam
    sets: tuple[ParsedSet, ...] = ()
    officials: tuple[ParsedOfficial, ...] = ()
    remarks: str | None = None

    @property
    def score(self) -> tuple[int, int] | None:
        if not self.sets:
            return None
        return (
            sum(set_score.score_a > set_score.score_b for set_score in self.sets),
            sum(set_score.score_b > set_score.score_a for set_score in self.sets),
        )


@dataclass(frozen=True)
class ParsedFdme:
    """Canonical parser output shared by FFVB, LNV and future formats."""

    parser_type: str
    parser_version: str
    match: ParsedMatch
    capabilities: frozenset[str] = field(default_factory=lambda: frozenset[str]())
