import logging

from spyke.application.imports.base import BaseImporter, ImportSummary
from spyke.domain.entities.organisation import Season
from spyke.infrastructure.database.models import CompetitionModel
from spyke.infrastructure.ffvb.dto import CompetitionRecord, EntityRecord
from spyke.infrastructure.ffvb.parsers.competitions import CompetitionParser

logger = logging.getLogger(__name__)


class CompetitionImporter(
    BaseImporter[CompetitionRecord, CompetitionModel],
):
    def get_competitions(self, entities: list[EntityRecord], seasons: list[Season]) -> list[CompetitionRecord]:
        """Get competitions from the FFVB website."""
        competition_parser = CompetitionParser()
        competitions: list[CompetitionRecord] = []
        for season in seasons:
            for entity in entities:
                document = self.client.fetch_competitions(entity_code=entity.code_ffvb, season=season)
                c = competition_parser.parse(document, entity.code_ffvb, season)
                competitions.extend(c)
        return competitions

    def import_records(self, records: list[CompetitionRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self.find_or_create(record)
            if was_created:
                created += 1
            else:
                self._update(model, record)
                updated += 1
        return ImportSummary(len(records), created, updated)

    def find_or_create(self, record: CompetitionRecord) -> tuple[CompetitionModel, bool]:
        model = self.session.scalar(
            select(CompetitionModel).where(
                CompetitionModel.name == record.name,
                CompetitionModel.entity_code == record.entity_code,
                CompetitionModel.season_start == record.season_start,
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
