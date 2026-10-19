import logging

from sqlalchemy import select

from spyke.application.imports.base import BaseImporter, ImportSummary
from spyke.domain.enums import Echelon
from spyke.domain.rules.categorisation import get_echelon_from_code_ffvb
from spyke.infrastructure.database.models import EntityModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.dto import EntityRecord
from spyke.infrastructure.ffvb.parsers.entities import (
    EntityDirectoryCodeParser,
    EntityDirectoryParser,
    EntityParser,
)
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)


class EntitiesImporter(BaseImporter[EntityRecord, EntityModel]):
    def enrich_entities_codes(self, entities: list[EntityRecord]) -> None:
        """Enrich a list of entities with additional details from the FFVB directory."""
        parser = EntityDirectoryCodeParser()
        document = self.client.fetch_entities_directory()
        parser.enrich(entities, document)

    def enrich_entities(self, entities: list[EntityRecord]) -> None:
        """Enrich a list of entities with additional details from the FFVB directory."""
        parser = EntityDirectoryParser()
        for entity in entities:
            if entity.entity_type in (Echelon.REGIONAL, Echelon.DEPARTEMENTAL):
                if entity.num_ffvb is None:
                    logger.warning(
                        f"Entity {entity.name} ({entity.code_ffvb}) does not have a num_ffvb for enrichment."
                    )
                    continue
                document: HttpDocument = self.client.fetch_entity_directory(
                    entity_code=entity.num_ffvb, entity_type=entity.entity_type
                )
                logger.debug(f"Enriching entity {entity.name} ({entity.code_ffvb}).")
                parser.enrich_record(entity, document)

    def get_filtered_entities(
        self,
        selected_entities: list[str],
        all_entities: bool,
        entity_type: Echelon | None = None,
    ) -> list[EntityRecord]:
        """Retrieve a filtered list of entities from the database."""
        entities = self._get_entities()
        return self._filter_entities(entities, selected_entities, all_entities, entity_type)

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

    def _get_entities(self) -> list[EntityRecord]:
        """Retrieve all entities from the database."""
        document = self.client.fetch_entities()
        parser = EntityParser()
        return parser.parse(document)

    def _filter_entities(
        self,
        entities: list[EntityRecord],
        selected_entities: list[str],
        all_entities: bool,
        entity_type: Echelon | None = None,
    ) -> list[EntityRecord]:
        """Retrieve a filtered list of entities from the database."""
        if entity_type is not None:
            entities = [entity for entity in entities if entity.entity_type == entity_type]
        if all_entities:
            return entities
        for entity_code in selected_entities:
            if not any([e.code_ffvb == entity_code for e in entities]):
                raise ValueError(f"Entity code '{entity_code}' not found in the available entities.")
        return [entity for entity in entities if entity.code_ffvb in selected_entities]

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
    from spyke.infrastructure.database.session import Session
    from spyke.infrastructure.ffvb.client import FfvbClient

    importer = EntitiesImporter(Session(), FfvbClient())
    entities = importer.get_entities()
    print(entities)
    importer.enrich_entities_codes(entities)
    importer.enrich_entities(entities)
