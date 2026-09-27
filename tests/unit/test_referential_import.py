from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spyke.application.imports.referentials import ReferentialImporter
from spyke.domain.enums import Category, Division, Echelon, Gender
from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import (
    ClubModel,
    CompetitionModel,
    ExternalIdentifierModel,
    LeagueModel,
)
from spyke.infrastructure.ffvb.dto import ClubRecord, CompetitionRecord, LeagueRecord


def test_referential_import_is_idempotent_and_keeps_external_ids() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    leagues = [LeagueRecord("league-1", "Ligue test", "TEST", Echelon.REGIONAL)]
    clubs = [
        ClubRecord(
            "club-1",
            "Club test",
            1_234_567,
            city="Toulouse",
            league_external_id="league-1",
        )
    ]
    competitions = [
        CompetitionRecord(
            "competition-1",
            "R1 masculin",
            "R1M",
            2025,
            2026,
            "league-1",
            Gender.MASCULIN,
            Category.SENIOR,
            Echelon.REGIONAL,
            Division.REGIONALE_1,
        )
    ]

    with Session(engine) as session:
        importer = ReferentialImporter(session)
        first = importer.import_leagues(leagues)
        importer.import_clubs(clubs)
        importer.import_competitions(competitions)
        second = importer.import_leagues(leagues)

        assert first.created == 1
        assert second.created == 0
        assert second.updated == 1
        assert session.query(LeagueModel).count() == 1
        assert session.query(ClubModel).count() == 1
        assert session.query(CompetitionModel).count() == 1
        assert session.query(ExternalIdentifierModel).count() == 3
