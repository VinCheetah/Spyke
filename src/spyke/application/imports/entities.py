from sqlalchemy import select

from spyke.infrastructure.database.models import (
    CompetitionModel,
    ExternalIdentifierModel,
    EntityModel,
    SeasonModel,
    TeamSeasonModel,
)
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.dto import EntityRecord
from spyke.infrastructure.ffvb.parsers.entities import EntityParser
from spyke.infrastructure.database.models import EntityModel
from spyke.domain.rules.categorisation import get_echelon_from_code_ffvb
from spyke.application.imports.base import BaseImporter, ImportSummary


class EntitiesImporter(BaseImporter[EntityRecord, EntityModel]):
    @staticmethod
    def get_entities(ffvb_client: FfvbClient) -> list[EntityRecord]:
        """Retrieve all entities from the database."""
        document = ffvb_client.fetch_entities()
        parser = EntityParser()
        return parser.parse(document)

    def get_filtered_entities(
        self, ffvb_client: FfvbClient, selected_entities: list[str], all_entities: bool
    ) -> list[EntityRecord]:
        """Retrieve a filtered list of entities from the database."""
        entities = self.get_entities(ffvb_client)
        if all_entities:
            return entities
        for entity_code in selected_entities or []:
            if not any(e.code_ffvb == entity_code for e in entities):
                raise ValueError(
                    f"Entity code '{entity_code}' not found in the available entities."
                )
        return [e for e in entities if e.code_ffvb in selected_entities]

    def import_records(self, records: list[EntityRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self.find_or_create(record)
            if was_created:
                created += 1
            else:
                model.name = record.name
                model.code_ffvb = record.code_ffvb
                model.echelon = get_echelon_from_code_ffvb(record.code_ffvb)
                updated += 1
        return ImportSummary(len(records), created, updated)

    def find_or_create(self, record: EntityRecord) -> tuple[EntityModel, bool]:
        model: EntityModel | None = self.session.scalar(
            select(EntityModel).where(EntityModel.code_ffvb == record.code_ffvb)
        )
        if model is None:
            model = EntityModel(
                code_ffvb=record.code_ffvb,
                name=record.name,
                echelon=get_echelon_from_code_ffvb(record.code_ffvb),
            )
            self.session.add(model)
            self.session.flush()
            return model, True
        else:
            return model, False


if __name__ == "__main__":
    from spyke.infrastructure.ffvb.client import FfvbClient
    # EntitiesImporter.get_entities(FfvbClient())
