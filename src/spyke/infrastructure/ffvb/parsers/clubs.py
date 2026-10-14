import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from spyke.infrastructure.ffvb.dto import ClubRecord
from spyke.infrastructure.ffvb.parsers.shared import get_soup
from spyke.infrastructure.sources.http import HttpDocument


class ClubParser:
    """Parse club listings and individual club pages from the FFVB directory."""

    def parse(self, document: HttpDocument, entity_code: str | None = None) -> list[ClubRecord]:
        soup = get_soup(document)
        clubs: list[ClubRecord] = []
        for row in soup.find_all("tr"):
            code_cell = row.find("td", class_="lienquestion", align="center")
            if code_cell is None:
                continue
            code = code_cell.get_text(" ", strip=True)
            if len(code) != 7 or not code.isdigit():
                continue
            name_cells = row.find_all("td", class_="lienquestion")
            name = next(
                (cell.get_text(" ", strip=True) for cell in name_cells if cell is not code_cell),
                "",
            )
            if not name:
                continue
            clubs.append(
                ClubRecord(
                    code_ffvb=code,
                    name=name,
                    entity_code_ffvb=entity_code,
                    email=self._email(row),
                )
            )
        return list({club.code_ffvb: club for club in clubs}.values())

    def parse_detail(self, document: HttpDocument, entity_code: str | None = None) -> ClubRecord:
        soup = get_soup(document)
        title = soup.find("td", class_="titreblanc_gd")
        title_text = title.get_text(" ", strip=True) if title else ""
        match = re.match(r"(?P<code>\d{7})\s+(?P<name>.+)", title_text)
        if match is None:
            raise ValueError(f"Club identifier not found in {document.url}")

        values = self._labelled_values(soup)
        address_lines = self._address_lines(soup)
        address = " ".join(address_lines) or None
        colors = self._colors(soup)
        return ClubRecord(
            code_ffvb=match["code"],
            name=match["name"].strip(),
            city=self._city(address_lines),
            department=match["code"][:3],
            entity_code_ffvb=entity_code,
            email=self._email(soup),
            website=self._website(soup),
            phone_number=values.get("tél.") or values.get("tél"),
            headquarters_address=address,
            colors=colors or None,
        )

    @staticmethod
    def _labelled_values(soup: BeautifulSoup) -> dict[str, str]:
        values: dict[str, str] = {}
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True).lower().rstrip(":")
            value = cells[1].get_text(" ", strip=True)
            if label and value:
                values[label] = value
        return values

    @staticmethod
    def _address_lines(soup: BeautifulSoup) -> list[str]:
        heading = soup.find(string=re.compile(r"Siège Social", re.I))
        if heading is not None:
            for parent in heading.parents:
                if parent.name != "table":
                    continue
                values = [
                    cell.get_text(" ", strip=True)
                    for cell in parent.find_all("td", class_="lienquestion")
                    if cell.get_text(" ", strip=True)
                ]
                if values:
                    return values[:3]
        return []

    @staticmethod
    def _city(address_lines: list[str]) -> str | None:
        if not address_lines:
            return None
        match = re.search(r"\b\d{5}\s+(.+)$", address_lines[-1])
        return match.group(1).strip() if match else address_lines[-1]

    @staticmethod
    def _colors(soup: BeautifulSoup) -> list[str] | None:
        label = soup.find(string=re.compile(r"Couleurs du club", re.I))
        if label is None:
            return None
        parent = label.parent
        if parent is None or parent.parent is None:
            return None
        text = parent.parent.get_text(" ", strip=True)
        value = re.sub(r"^Couleurs du club:\s*", "", text, flags=re.I).strip()
        return [value] if value else None

    @staticmethod
    def _email(node: BeautifulSoup | Tag) -> str | None:
        link = node.find("a", href=re.compile(r"^mailto:", re.I))
        if link is None:
            return None
        href = link.get("href")
        return href[7:].strip() if isinstance(href, str) else None

    @staticmethod
    def _website(node: BeautifulSoup | Tag) -> str | None:
        for link in node.find_all("a", href=re.compile(r"^https?://", re.I)):
            href_value = link.get("href")
            if not isinstance(href_value, str):
                continue
            href = href_value.strip()
            if href and "ffvb" not in href.lower() and "ffvolley" not in href.lower():
                return href
        return None
