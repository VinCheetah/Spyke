import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from spyke.infrastructure.ffvb.dto import ClubRecord
from spyke.infrastructure.ffvb.parsers.base import HttpDocumentParser
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)


class ClubParser(HttpDocumentParser[ClubRecord]):
    """Parse club listings and individual club pages from the FFVB directory."""

    def parse_single(self, document: HttpDocument) -> ClubRecord:
        address: list[str] | None = None
        contact_info: dict[str, Any] = {}
        correspondant: str | None = None
        soup = self.get_soup(document)
        title = soup.find("td", class_="titreblanc_gd")
        title_text = title.get_text(" ", strip=True) if title else ""
        match = re.match(r"(?P<code>\d{7})\s+(?P<name>.+)", title_text)
        if match is None:
            logger.error(f"Club identifier not found in {document.url}")
            raise ValueError(f"Club identifier not found in {document.url}")
        heading: Tag = self.find_heading(soup, "Fiche du Club")
        heading_row: Tag | None = heading.find_parent("tr")
        if heading_row is None:
            raise ValueError("Entity heading has no parent row")
        details_row: Tag | None = heading_row.find_next_sibling()
        if details_row is None:
            raise ValueError("Entity details row not found")
        columns = {self.clean_text(td): td for td in details_row.find_all("td", class_="lienblanc_pt")}
        if (address_column := columns.get("Siège Social")) and (address_gp := self.get_grandparent(address_column)):
            address = self._address_lines(address_gp)
        if (contact_column := columns.get("Coordonnées")) and (contact_gp := self.get_grandparent(contact_column)):
            contact_info = self._contact_info(contact_gp)
        if (correspondant_column := columns.get("Correspondant.e")) and (
            correspondant_gp := self.get_grandparent(correspondant_column)
        ):
            correspondant = self._correspondant(correspondant_gp)
        return ClubRecord(
            code_ffvb=match.group("code"),
            name=match.group("name"),
            committee_code=self._extract_entity_code(soup, "Comité Départemental", 3),
            league_code=self._extract_entity_code(soup, "Ligue Régionale", 2),
            correspondant=correspondant,
            email=contact_info.get("email"),
            website=contact_info.get("website"),
            phone_numbers=contact_info.get("phones"),
            headquarters_address=address or None,
            colors=self._colors(soup),
        )

    def _contact_info(self, soup: BeautifulSoup | Tag) -> dict[str, Any]:
        """Extract contact information from a club page."""
        contact: dict[str, Any] = {}
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True).lower().rstrip(":")
            value = cells[1].get_text(" ", strip=True)
            if label and value and label.lower() in {"tél", "téléphone", "tél.2", "portable"}:
                if "phones" not in contact:
                    contact["phones"] = [value]
                else:
                    contact["phones"].append(value)
        if email := self._email(soup):
            contact["email"] = email
        if website := self._website(soup):
            contact["website"] = website
        return contact

    def _address_lines(self, soup: BeautifulSoup | Tag) -> list[str]:
        address_cell = soup.find_all("td", class_="lienquestion")
        return [cell.get_text(" ", strip=True) for cell in address_cell if cell.get_text(" ", strip=True)]

    def _correspondant(self, soup: BeautifulSoup | Tag) -> str | None:
        if (value_cell := soup.find("td", class_="lienquestion")) is None:
            return None
        return value_cell.get_text(" ", strip=True) or None

    @staticmethod
    def _colors(soup: BeautifulSoup | Tag) -> str | None:
        label = soup.find(string=re.compile(r"Couleurs du club", re.I))
        if label is None:
            return None
        parent = label.parent
        if parent is None or parent.parent is None:
            return None
        text = parent.parent.get_text(" ", strip=True)
        value = re.sub(r"^Couleurs du club:\s*", "", text, flags=re.I).strip()
        return value or None

    def _extract_committee(self, soup: BeautifulSoup) -> str | None:
        """Extract the committee code from the entity directory page."""
        try:
            heading: Tag = self.find_heading(soup, "Comité Départemental")
        except ValueError:
            logger.warning("Committee heading not found in the document.")
            return None
        table = heading.find_parent("table")
        if table is None:
            raise ValueError("Parent table not found")
        cell = table.find("td", class_="liensuite4_gd", align="center")
        code = self.clean_text(cell)
        if not code or not re.match(r"^\d{3}$", code):
            print(f"Invalid committee code found: {code!r}")
            return None
        return code

    def _extract_league(self, soup: BeautifulSoup) -> str | None:
        """Extract the league code from the entity directory page."""
        try:
            heading: Tag = self.find_heading(soup, "Ligue Régionale")
        except ValueError:
            logger.warning("League heading not found in the document.")
            return None
        table = heading.find_parent("table")
        if table is None:
            raise ValueError("Parent table not found")
        cell = table.find("td", class_="liensuite4_gd", align="center")
        code = self.clean_text(cell)
        if not code or not re.match(r"^\d{2}$", code):
            print(f"Invalid league code found: {code!r}")
            return None
        return code

    def _extract_entity_code(
        self,
        soup: BeautifulSoup,
        heading_text: str,
        expected_length: int,
    ) -> str | None:
        try:
            heading = self.find_heading(soup, heading_text)
        except ValueError:
            logger.warning("%s heading not found.", heading_text)
            return None

        cell = heading.find_next("td", class_="liensuite4_gd", align="center")
        if cell is None:
            logger.warning("No cell found for %s code.", heading_text)
            return None
        code = self.clean_text(cell)
        if not code or len(code) != expected_length or not code.isdigit():
            logger.warning("Invalid %s code found: %r", heading_text, code)
            return None
        return code
