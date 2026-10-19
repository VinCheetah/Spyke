import logging
from select import select

from spyke.application.imports.base import BaseImporter, ImportSummary
from spyke.domain.entities.organisation import Season
from spyke.infrastructure.database.models import CompetitionModel, MatchModel
from spyke.infrastructure.ffvb.dto import EntityRecord, MatchRecord
from spyke.infrastructure.ffvb.parsers.calendar import CalendarParser

logger = logging.getLogger(__name__)


class CalendarImporter(
    BaseImporter[MatchRecord, MatchModel]  # Assuming you have a MatchModel defined in your database models,
):
    def get_matches(self, entities: list[EntityRecord], seasons: list[Season]) -> list[MatchRecord]:
        """Get matches from the FFVB website."""
        calendarParser = CalendarParser()
        calendards: list[MatchRecord] = []
        for season in seasons:
            for entity in entities:
                document = self.client.fetch_calendar_export(entity_code=entity.code_ffvb, season=season)
                c = calendarParser.parse(document, entity.code_ffvb, season)
                calendards.extend(c)
        return calendards

    def import_records(self, records: list[MatchRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self.find_or_create(record)
            if was_created:
                created += 1
            else:
                self._update(model, record)
                updated += 1
        return ImportSummary(len(records), created, updated)

    def find_or_create(self, record: MatchRecord) -> tuple[MatchModel, bool]:
        model = self.session.scalar(
            select(MatchModel).where(
                MatchModel.code == record.code,
                MatchModel.entity == record.entity,
                MatchModel.a_team == record.a_team,
                MatchModel.b_team == record.b_team,
                MatchModel.a_club_code == record.a_club_code,
                MatchModel.b_club_code == record.b_club_code,
                MatchModel.date == record.date,
                MatchModel.time == record.time,
                MatchModel.score == record.score,
                MatchModel.venue == record.venue,
            )
        )
        if model is not None:
            return model, False

        model = CompetitionModel(
            name=record.name,
            entity_code=record.entity_code,
            season_start=record.season_start,
        )
        self.session.add(model)
        self.session.commit()
        return model, True
