import logging

from spyke.application.imports.base import BaseImporter
from spyke.domain.entities.organisation import Season
from spyke.infrastructure.database.models import TeamModel
from spyke.infrastructure.ffvb.dto import CompetitionRecord, EntityRecord, TeamRecord
from spyke.infrastructure.ffvb.parsers.adressier import AdressierParser

logger = logging.getLogger(__name__)


class AdressierImporter(BaseImporter[TeamRecord, TeamModel]):
    def get_adressiers(
        self, entities: list[EntityRecord], competitions: list[CompetitionRecord], seasons: list[Season]
    ) -> list[TeamRecord]:
        """Get adressiers from the FFVB website."""
        adressier_parser = AdressierParser()
        adressiers: list[TeamRecord] = []
        for season in seasons:
            for entity in entities:
                competition_entity = [
                    comp
                    for comp in competitions
                    if comp.entity_code == entity.code_ffvb and comp.season_start == season.start_year
                ]
                if not competition_entity:
                    logger.warning(
                        f"No competition found for entity {entity.code_ffvb} and season {season.start_year}. Skipping."
                    )
                    continue
                pool_codes = [
                    pool.code
                    for competition in competition_entity
                    for pool in competition.pools
                    if pool.code is not None
                ]
                if not pool_codes:
                    logger.warning(
                        f"No pool codes found for entity {entity.code_ffvb} and season {season.start_year}. Skipping."
                    )
                    continue
                document = self.client.fetch_addressier(
                    entity_code=entity.code_ffvb, season=season, pool_codes=pool_codes
                )
                adressiers.extend(adressier_parser.parse(document))
        return adressiers

    def import_records(self, records: list[TeamRecord]) -> None:
        for record in records:
            model, was_created = self.find_or_create(record)
            if not was_created:
                self._update(model, record)

    def find_or_create(self, record: TeamRecord) -> tuple[TeamModel, bool]:
        model = self.session.scalar(
            select(TeamModel).where(
                TeamModel.club_code == record.club_code,
                TeamModel.name == record.name,
            )
        )
        if model is not None:
            return model, False

        model = TeamModel(
            club_code=record.club_code,
            name=record.name,
            coach=record.coach,
            assistant_coach=record.assistant_coach,
            venues=record.venues,
        )
        self.session.add(model)
        self.session.commit()
        return model, True
