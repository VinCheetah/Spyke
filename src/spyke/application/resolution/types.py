from dataclasses import dataclass

from spyke.domain.enums import ResolutionStatus


@dataclass(frozen=True)
class ResolutionCandidate:
    """One canonical candidate and the evidence supporting it."""

    entity_id: int
    name: str
    score: float
    reason: str


@dataclass(frozen=True)
class ResolutionResult:
    """Resolution outcome; ambiguous results intentionally have no entity id."""

    status: ResolutionStatus
    entity_id: int | None
    confidence: float
    normalized_name: str
    candidates: tuple[ResolutionCandidate, ...] = ()
    reason: str = ""
