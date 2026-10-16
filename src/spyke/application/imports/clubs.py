import logging

from sqlalchemy import select

from spyke.application.imports.base import BaseImporter, ImportSummary
from spyke.infrastructure.database.models import ClubModel, EntityModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.dto import ClubRecord, EntityRecord
from spyke.infrastructure.ffvb.parsers.clubs import ClubParser
from spyke.infrastructure.ffvb.parsers.entities import EntityDirectoryParser

logger = logging.getLogger(__name__)


class ClubsImporter(BaseImporter[ClubRecord, ClubModel]):
    """Retrieve and persist clubs from the FFVB directory."""

    def get_filtered_clubs(
        self,
        ffvb_client: FfvbClient,
        entities: list[EntityRecord],
    ) -> list[ClubRecord]:
        parser = ClubParser()
        directory_parser = EntityDirectoryParser()
        clubs: dict[str, ClubRecord] = {}
        clubs_code = set(entity.clubs_code for entity in entities if entity.clubs_code is not None)
        logger.critical(f"Info: Fetching clubs: {', '.join(clubs_code)}")
        for entity in entities:
            if entity.num_ffvb is None:
                continue
            directory = ffvb_client.fetch_entity_directory(entity.directory_code)
            _, _, club_codes = directory_parser.parse(directory)
            listed_clubs = parser.parse(directory, entity.code_ffvb)

            for club in listed_clubs:
                clubs[club.code_ffvb] = club
            for club_code in club_codes:
                detail = ffvb_client.fetch_club(club_code)
                clubs[club_code] = parser.parse_detail(detail, entity.code_ffvb)

        return list(clubs.values())

    def import_records(self, records: list[ClubRecord]) -> ImportSummary:
        created = updated = 0
        for record in records:
            model, was_created = self.find_or_create(record)
            if was_created:
                created += 1
            else:
                self._update(model, record)
                updated += 1
        return ImportSummary(len(records), created, updated)

    def find_or_create(self, record: ClubRecord) -> tuple[ClubModel, bool]:
        code = self._club_code(record.code_ffvb)
        model = self.session.scalar(select(ClubModel).where(ClubModel.code_ffvb == code))
        if model is not None:
            return model, False

        model = ClubModel(
            code_ffvb=code,
            name=record.name,
            city=record.city,
            department=record.department,
            entity_id=self._entity_id(record.entity_code_ffvb),
            email=record.email,
            website=record.website,
            phone_number=record.phone_number,
            headquarters_address=record.headquarters_address,
            colors=record.colors or [],
        )
        self.session.add(model)
        self.session.flush()
        return model, True

    def _update(self, model: ClubModel, record: ClubRecord) -> None:
        model.name = record.name
        model.city = record.city
        model.department = record.department
        model.entity_id = self._entity_id(record.entity_code_ffvb)
        model.email = record.email
        model.website = record.website
        model.phone_number = record.phone_number
        model.headquarters_address = record.headquarters_address
        if record.colors is not None:
            model.colors = record.colors

    def _entity_id(self, code: str | None) -> int | None:
        if code is None:
            return None
        return self.session.scalar(select(EntityModel.id).where(EntityModel.code_ffvb == code))

    @staticmethod
    def _club_code(code: str) -> int:
        if len(code) != 7 or not code.isdigit():
            raise ValueError(f"Invalid FFVB club number: {code!r}")
        return int(code)
