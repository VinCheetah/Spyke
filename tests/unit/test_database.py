from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus
from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import (
    ClubModel,
    CompetitionModel,
    LeagueModel,
    MatchModel,
    MatchSetModel,
    SeasonModel,
    TeamSeasonModel,
    VenueModel,
)


def test_schema_can_be_created_and_relations_persist_on_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        season = SeasonModel(id=1, start_date=date(2025, 9, 1), end_date=date(2026, 8, 31))
        league = LeagueModel(id=1, name="Ligue test", code_ffvb="TEST", echelon=Echelon.REGIONAL)
        club = ClubModel(id=1, name="Club test", code_ffvb=1_234_567, league=league)
        competition = CompetitionModel(
            id=1,
            season=season,
            organizer=league,
            name="R1 masculine",
            code_competition="R1M",
            gender=Gender.MASCULIN,
            category=Category.SENIOR,
            echelon=Echelon.REGIONAL,
            division=Division.REGIONALE_1,
        )
        home = TeamSeasonModel(
            id=1, season=season, competition=competition, club=club, name="Club A"
        )
        away = TeamSeasonModel(
            id=2, season=season, competition=competition, club=club, name="Club B"
        )
        venue = VenueModel(id=1, name="Gymnase", coordinate={"latitude": 43.6, "longitude": 1.4})
        match = MatchModel(
            id=1,
            code="MATCH-1",
            season=season,
            competition=competition,
            venue=venue,
            home_team=home,
            away_team=away,
            scheduled_at=datetime(2026, 1, 10, 20, tzinfo=UTC),
            status=MatchStatus.PLAYED,
            home_sets=3,
            away_sets=1,
            sets=[MatchSetModel(number=1, home_score=25, away_score=20)],
        )
        session.add(match)
        session.commit()

        stored = session.scalar(select(MatchModel).where(MatchModel.code == "MATCH-1"))
        assert stored is not None
        assert stored.home_team.name == "Club A"
        assert stored.sets[0].home_score == 25


def test_database_constraints_prevent_duplicate_external_codes() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                LeagueModel(id=1, name="A", code_ffvb="DUP", echelon=Echelon.REGIONAL),
                LeagueModel(id=2, name="B", code_ffvb="DUP", echelon=Echelon.REGIONAL),
            ]
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
            assert session.query(LeagueModel).count() == 0
        else:
            raise AssertionError("duplicate FFVB codes must be rejected")
