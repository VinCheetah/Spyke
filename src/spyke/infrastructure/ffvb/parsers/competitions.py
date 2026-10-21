import logging
import re

from bs4 import BeautifulSoup

from spyke.domain.entities.organisation import Season
from spyke.infrastructure.ffvb.dto import CompetitionRecord, PouleRecord
from spyke.infrastructure.ffvb.parsers.base import HttpDocumentParser
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)


class CompetitionParser(HttpDocumentParser[CompetitionRecord]):
    """Parse club listings and individual club pages from the FFVB directory."""

    def parse(self, document: HttpDocument, entity_code: str, season: Season) -> list[CompetitionRecord]:
        competitions: list[CompetitionRecord] = []
        soup: BeautifulSoup = self.get_soup(document)
        tag = soup.find("td", class_="lienblanc", align="left")
        if tag is None:
            logger.error(f"Competition access text not found in {document.url}")
            raise ValueError(f"Competition access text not found in {document.url}")
        table = self.get_grandparent(tag)
        if table is None:
            logger.error(f"Competition table not found in {document.url}")
            raise ValueError(f"Competition table not found in {document.url}")
        rows = table.find_all("td", class_=["liengris", "rubrique1"], align="left")
        for row in rows:
            name = self.clean_text(row)
            if name is None:
                logger.warning(f"Competition name not found in row: {row}")
                continue
            if (link := row.find("a")) is None:
                competitions.append(
                    CompetitionRecord(name=name, entity_code=entity_code, season_start=season.start_year)
                )
            else:
                href = link.get("href")
                if href is None:
                    logger.warning(f"Competition link not found in row: {row}")
                    continue
                code = match.group(1) if (match := re.search(r"poule=([A-Z0-9]{3})", href)) else None
                tour = match.group(1) if (match := re.search(r"tour=([0-9]{2})", href)) else None
                division = match.group(1) if (match := re.search(r"division=([A-Z0-9]{3})", href)) else None
                if not competitions:
                    competitions.append(
                        CompetitionRecord(name="Unknown", entity_code=entity_code, season_start=season.start_year)
                    )
                    logger.warning(
                        f"Competition found without a previous competition to attach to: {name} in {entity_code} for season {season.start_year}. Skipping this competition."
                    )
                    continue
                competitions[-1].pools.append(PouleRecord(name=name, code=code, tour=tour, division=division))
        return competitions
