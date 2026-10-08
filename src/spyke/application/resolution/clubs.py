import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from spyke.application.resolution.types import ResolutionCandidate, ResolutionResult
from spyke.domain.enums import ResolutionStatus
from spyke.domain.rules.categorisation import normalize_text_upper
from spyke.infrastructure.database.models import (
    ClubModel,
    EntityResolutionModel,
    ExternalIdentifierModel,
)


def _normalize_club_name(value: str) -> str:
    return normalize_text_upper(re.sub(r"[^\w]+", " ", value, flags=re.UNICODE))


class ClubResolver:
    """Resolve external club records using identifiers first, then contextual names.

    Name matching is deliberately conservative: a normalized name alone can
    produce a probable result, but only an exact unique match is accepted as
    ``MATCH``. Ties remain ``AMBIGUOUS`` and never create a new identity.
    """

    def __init__(self, session: Session, *, source_system: str = "ffvb") -> None:
        self.session = session
        self.source_system = source_system

    def resolve(
        self,
        *,
        external_id: str | None,
        name: str,
        city: str | None = None,
        persist: bool = True,
    ) -> ResolutionResult:
        normalized_name = _normalize_club_name(name)
        candidates: list[ResolutionCandidate] = []
        if external_id:
            identifier = self.session.scalar(
                select(ExternalIdentifierModel).where(
                    ExternalIdentifierModel.source_system == self.source_system,
                    ExternalIdentifierModel.entity_type == "club",
                    ExternalIdentifierModel.external_id == external_id,
                )
            )
            if identifier is not None:
                club = self.session.get(ClubModel, identifier.entity_id)
                if club is not None:
                    result = ResolutionResult(
                        ResolutionStatus.MATCH,
                        club.id,
                        1.0,
                        normalized_name,
                        reason="exact external identifier",
                    )
                    return self._persist(result, external_id, persist)

        normalized_city = _normalize_club_name(city or "")
        for club in self.session.scalars(select(ClubModel)).all():
            club_name = _normalize_club_name(club.name)
            if club_name != normalized_name:
                continue
            score = 0.9
            reason = "normalized name"
            if normalized_city and _normalize_club_name(club.city or "") == normalized_city:
                score = 0.98
                reason = "normalized name and city"
            candidates.append(ResolutionCandidate(club.id, club.name, score, reason))

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        if not candidates:
            result = ResolutionResult(
                ResolutionStatus.UNRESOLVED,
                None,
                0.0,
                normalized_name,
                reason="no candidate matched",
            )
        elif len(candidates) > 1 and candidates[0].score == candidates[1].score:
            result = ResolutionResult(
                ResolutionStatus.AMBIGUOUS,
                None,
                candidates[0].score,
                normalized_name,
                tuple(candidates),
                reason="multiple candidates have the same score",
            )
        elif candidates[0].score >= 0.97:
            result = ResolutionResult(
                ResolutionStatus.MATCH,
                candidates[0].entity_id,
                candidates[0].score,
                normalized_name,
                tuple(candidates),
                reason=candidates[0].reason,
            )
        else:
            result = ResolutionResult(
                ResolutionStatus.PROBABLE,
                None,
                candidates[0].score,
                normalized_name,
                tuple(candidates),
                reason=candidates[0].reason,
            )
        return self._persist(result, external_id, persist)

    def _persist(
        self, result: ResolutionResult, external_id: str | None, enabled: bool
    ) -> ResolutionResult:
        if not enabled:
            return result
        existing = self.session.scalar(
            select(EntityResolutionModel).where(
                EntityResolutionModel.source_system == self.source_system,
                EntityResolutionModel.entity_type == "club",
                EntityResolutionModel.external_id == external_id,
            )
        )
        values = {
            "normalized_name": result.normalized_name,
            "status": result.status.value,
            "canonical_entity_id": result.entity_id,
            "confidence": result.confidence,
            "reason": result.reason,
        }
        if existing is None:
            self.session.add(
                EntityResolutionModel(
                    source_system=self.source_system,
                    entity_type="club",
                    external_id=external_id,
                    **values,
                )
            )
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self.session.commit()
        return result
