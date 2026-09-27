from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from spyke.infrastructure.database.models import (
    ClubModel,
    CompetitionModel,
    ExternalIdentifierModel,
    LeagueModel,
    MatchModel,
    SeasonModel,
    TeamSeasonModel,
)
from spyke.infrastructure.ffvb.dto import ClubRecord, CompetitionRecord, LeagueRecord, MatchRecord


@dataclass(frozen=True)
class ImportSummary:
    """Counters returned by one idempotent referential import."""

    seen: int
    created: int
    updated: int


class ReferentialImporter:
    """Persist FFVolley referentials without coupling the app to HTTP or JSON."""

    def __init__(self, session: Session, *, source_system: str = "ffvb") -> None:
        self.session = session
        self.source_system = source_system

    def import_leagues(self, records: list[LeagueRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self._find_or_create(
                LeagueModel,
                record.external_id,
                name=record.name,
                code_ffvb=record.code_ffvb,
                echelon=record.echelon,
            )
            if was_created:
                created += 1
            else:
                model.name = record.name
                model.code_ffvb = record.code_ffvb
                model.echelon = record.echelon
                updated += 1
        self.session.commit()
        return ImportSummary(len(records), created, updated)

    def import_clubs(self, records: list[ClubRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            league_id = self._entity_id("league", record.league_external_id)
            model, was_created = self._find_or_create(
                ClubModel,
                record.external_id,
                name=record.name,
                code_ffvb=record.code_ffvb,
                city=record.city,
                department=record.department,
                league_id=league_id,
            )
            if was_created:
                created += 1
            else:
                model.name = record.name
                model.code_ffvb = record.code_ffvb
                model.city = record.city
                model.department = record.department
                model.league_id = league_id
                updated += 1
        self.session.commit()
        return ImportSummary(len(records), created, updated)

    def import_competitions(self, records: list[CompetitionRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            season = self._season(record.season_start, record.season_end)
            organizer_id = self._entity_id("league", record.organizer_external_id)
            if organizer_id is None:
                raise ValueError(f"Unknown organizer: {record.organizer_external_id}")
            model, was_created = self._find_or_create(
                CompetitionModel,
                record.external_id,
                season_id=season.id,
                organizer_id=organizer_id,
                name=record.name,
                code_competition=record.code,
                gender=record.gender,
                category=record.category,
                echelon=record.echelon,
                division=record.division,
            )
            if was_created:
                created += 1
            else:
                model.name = record.name
                model.code_competition = record.code
                model.gender = record.gender
                model.category = record.category
                model.echelon = record.echelon
                model.division = record.division
                updated += 1
        self.session.commit()
        return ImportSummary(len(records), created, updated)

    def import_calendar(self, records: list[MatchRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            competition_id = self._entity_id("competition", record.competition_external_id)
            home_club_id = self._entity_id("club", record.home_club_external_id)
            away_club_id = self._entity_id("club", record.away_club_external_id)
            if competition_id is None or home_club_id is None or away_club_id is None:
                raise ValueError(f"Unknown match reference: {record.external_id}")
            competition = self.session.get(CompetitionModel, competition_id)
            assert competition is not None
            home_team = self._team(competition, home_club_id, record.home_club_external_id)
            away_team = self._team(competition, away_club_id, record.away_club_external_id)
            model, was_created = self._find_or_create(
                MatchModel,
                record.external_id,
                code=record.code,
                season_id=competition.season_id,
                competition_id=competition.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                scheduled_at=record.scheduled_at,
                status=record.status,
            )
            if was_created:
                created += 1
            else:
                model.code = record.code
                model.scheduled_at = record.scheduled_at
                model.status = record.status
                updated += 1
        self.session.commit()
        return ImportSummary(len(records), created, updated)

    def _find_or_create(
        self, model_type: Any, external_id: str, **values: object
    ) -> tuple[Any, bool]:
        identifier = self.session.scalar(
            select(ExternalIdentifierModel).where(
                ExternalIdentifierModel.source_system == self.source_system,
                ExternalIdentifierModel.entity_type == model_type.__tablename__,
                ExternalIdentifierModel.external_id == external_id,
            )
        )
        if identifier is not None:
            model = self.session.get(model_type, identifier.entity_id)
            if model is None:
                raise ValueError(f"Broken external identifier: {external_id}")
            return model, False
        model = model_type(**values)
        self.session.add(model)
        self.session.flush()
        self.session.add(
            ExternalIdentifierModel(
                source_system=self.source_system,
                entity_type=model_type.__tablename__,
                entity_id=model.id,
                external_id=external_id,
            )
        )
        return model, True

    def _entity_id(self, entity_type: str, external_id: str | None) -> int | None:
        if external_id is None:
            return None
        identifier = self.session.scalar(
            select(ExternalIdentifierModel).where(
                ExternalIdentifierModel.source_system == self.source_system,
                ExternalIdentifierModel.entity_type == entity_type,
                ExternalIdentifierModel.external_id == external_id,
            )
        )
        return identifier.entity_id if identifier else None

    def _season(self, start_year: int, end_year: int) -> SeasonModel:
        season = self.session.scalar(
            select(SeasonModel).where(
                SeasonModel.start_date == date(start_year, 9, 1),
                SeasonModel.end_date == date(end_year, 8, 31),
            )
        )
        if season is None:
            season = SeasonModel(start_date=date(start_year, 9, 1), end_date=date(end_year, 8, 31))
            self.session.add(season)
            self.session.flush()
        return season

    def _team(
        self, competition: CompetitionModel, club_id: int, external_id: str
    ) -> TeamSeasonModel:
        team = self.session.scalar(
            select(TeamSeasonModel).where(
                TeamSeasonModel.competition_id == competition.id,
                TeamSeasonModel.club_id == club_id,
            )
        )
        if team is None:
            team = TeamSeasonModel(
                season_id=competition.season_id,
                competition_id=competition.id,
                club_id=club_id,
                name=external_id,
            )
            self.session.add(team)
            self.session.flush()
        return team
