from spyke.application.imports.base import BaseImporter, ImportSummary
from spyke.infrastructure.database.models import ClubModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.dto import ClubRecord, EntityRecord


class ClubsImporter(BaseImporter[ClubRecord, ClubModel]):
    def get_filtered_clubs(
        self, ffvb_client: FfvbClient, entities: list[EntityRecord]
    ) -> list[ClubRecord]:
        """Retrieve a filtered list of clubs from the database."""
        clubs_codes: dict[str, list[str]] = {}
        for entity in entities:
            document = ffvb_client.fetch_entity(entity.code_ffvb)
            parser = ClubParser()
            clubs_code = parser.parse(document)
            clubs_codes[entity.code_ffvb] = [club.code_ffvb for club in clubs_code]

        document = ffvb_client.fetch()
        parser = JsonReferentialParser()
        clubs = parser.clubs(document)

        return clubs

    def import_records(self, records: list[ClubRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self.find_or_create(record)
            if was_created:
                created += 1
            else:
                model.name = record.name
                model.code_ffvb = record.code_ffvb
                model.city = record.city
                model.department = record.department
                model.entity_code_ffvb = record.entity_code_ffvb
                updated += 1
        return ImportSummary(len(records), created, updated)

    def find_or_create(self, record: ClubRecord) -> tuple[ClubModel, bool]:
        model: ClubModel | None = self.session.scalar(
            select(ClubModel).where(ClubModel.code_ffvb == record.code_ffvb)
        )
        if model is None:
            model = ClubModel(
                code_ffvb=record.code_ffvb,
                name=record.name,
                city=record.city,
                department=record.department,
                entity_code_ffvb=record.entity_code_ffvb,
            )
            self.session.add(model)
            return model, True
        return model, False


if __name__ == "__main__":
    from spyke.infrastructure.ffvb.client import FfvbClient
    from spyke.application.imports.entities import EntitiesImporter
    from spyke.infrastructure.database.session import DatabaseSession

    entities = EntitiesImporter.get_entities(FfvbClient())
    with DatabaseSession() as session:
        importer = ClubsImporter(session=session)
        clubs = importer.get_filtered_clubs(FfvbClient(), entities)
        print(clubs)
        importer.import_records(clubs)
