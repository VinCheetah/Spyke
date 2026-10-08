from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spyke.application.resolution import ClubResolver
from spyke.domain.enums import Echelon, ResolutionStatus
from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import (
    ClubModel,
    EntityResolutionModel,
    ExternalIdentifierModel,
    LeagueModel,
)


def test_club_resolution_prefers_external_identifier() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        league = LeagueModel(name="Ligue", code_ffvb="L", echelon=Echelon.REGIONAL)
        club = ClubModel(name="AS Villeurbanne", code_ffvb=1_234_567, city="Lyon", league=league)
        session.add_all([league, club])
        session.flush()
        session.add(
            ExternalIdentifierModel(
                source_system="ffvb", entity_type="club", entity_id=club.id, external_id="42"
            )
        )
        session.commit()

        result = ClubResolver(session).resolve(external_id="42", name="Other name", persist=True)

        assert result.status == ResolutionStatus.MATCH
        assert result.entity_id == club.id
        assert session.query(EntityResolutionModel).one().confidence == 1.0


def test_club_resolution_keeps_equal_name_candidates_ambiguous() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                ClubModel(name="Volley Club", code_ffvb=1_234_567, city="Lille"),
                ClubModel(name="Volley Club", code_ffvb=2_345_678, city="Rouen"),
            ]
        )
        session.commit()

        result = ClubResolver(session).resolve(external_id=None, name="Volley-Club", persist=False)

        assert result.status == ResolutionStatus.AMBIGUOUS
        assert result.entity_id is None
        assert len(result.candidates) == 2
