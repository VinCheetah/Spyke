from spyke.infrastructure.ffvb.dto import EntityRecord
from spyke.infrastructure.sources.http import HttpDocument
from spyke.domain.rules.categorisation import get_echelon_from_code_ffvb
from spyke.infrastructure.ffvb.parsers.base import HttpDocumentParser
from spyke.domain.enums import Echelon
from typing import Any
from bs4 import BeautifulSoup, Tag
import re
import logging


logger = logging.getLogger(__name__)

# Entités non listées dans le menu déroulant du site mais accessibles directement
# HIDDEN_ENTITIES = [
#     EntityInfo(code="AALNV", nom="Compétitions Professionnelles LNV", type="nationale"),
#     EntityInfo(code="ACJEUNES", nom="Coupe de France Jeunes", type="nationale"),
# ]


class EntityParser(HttpDocumentParser[EntityRecord]):
    """
    Parser for entities data from the FFVolley system.
    """

    def parse(self, document: HttpDocument) -> list[EntityRecord]:
        """
        Parse the given HTTP document and extract a list of Entity objects.

        Args:
            document (HttpDocument): The HTTP document to parse.

        Returns:
            list[Entity]: A list of Entity objects extracted from the document.
        """
        soup = self.get_soup(document)
        entities: list[EntityRecord] = []

        select = soup.find("select", {"name": "sel_entites"})
        # Corriger le code pour authoriser les caractères speciaux
        if not select:
            raise ValueError("Select 'sel_entites' not found in the document")
        for option in select.find_all("option"):
            val = option.get("value")
            code = val.strip() if isinstance(val, str) else ""
            name = option.text.strip()

            if not code or code == "0" or code.startswith("-") or code == "ZZALL":
                logger.warning(f"Skipping invalid option: {name} ({code})")
                continue
            
            
            
            entity_type = get_echelon_from_code_ffvb(code)
            if entity_type == Echelon.DEPARTEMENTAL:
                # PEut etre strip avant ou nettoyer 
                if not name.startswith("CD") and "-" in name:
                    logger.warning(f"Warning: Departmental entity name does not start with 'CD': {name} ({code})")
                # Name is in the format "CDXX - Comité [du / de / de la / de l' / des / rien / d'] [Nom comité]"
                # Mettre les options dans le bon sens pour la reconnaissance maximale
                name = re.sub(r"^CD\d+\s*-\s*Comité\s*(?:des|de la|de l'|du l'|de|d'|du)?\s*", "", name, flags=re.IGNORECASE)
            if entity_type == Echelon.REGIONAL:
                # Name is in the format "Ligue [Nom ligue]"
                name = re.sub(r"^Ligue\s+", "", name, flags=re.IGNORECASE)
            
            print(code, name)
            entities.append(EntityRecord(code_ffvb=code, name=name, entity_type=get_echelon_from_code_ffvb(code)))

        return entities
    
    
class EntityDirectoryCodeParser(HttpDocumentParser[EntityRecord]):
    """
    Parser for entity directory data from the FFVolley system.
    """

    def parse(self, document: HttpDocument) -> list[EntityRecord]:
        raise NotImplementedError("This parser is only used for enriching existing entities, not for parsing new ones.")


    def enrich(self, records: list[EntityRecord], document: HttpDocument) -> None:
        """Extract FFVB entity codes and names from the selection lists."""
        soup: BeautifulSoup = self.get_soup(document)
        selectors = {Echelon.REGIONAL: "ws_new_ligue", Echelon.DEPARTEMENTAL: "ws_new_comit"}
        print("\n".join(map(str, records)))
        print(records)
        for entity_type, select_name in selectors.items():
            select: Tag | None = soup.find("select", attrs={"name": select_name})
            if select is None:
                raise ValueError(f"Select element not found: {select_name}")

            for option in select.find_all("option"):
                code: str | None = option.get("value", "").strip()
                name = option.get_text(strip=True)
                if not code or code in ("0", ""):
                    continue
                record = next((r for r in records if r.name.upper() == name.upper()), None)
                if record is None:
                    record = next((r for r in records if code[0] == "0" and code[1:] in r.code_ffvb and r.entity_type == Echelon.DEPARTEMENTAL), None)
                    if record is not None:
                        logger.warning(f"Warning: No exact match found for {name} ({code}), using partial match: {name} -> {record.name}")
                if record is None:
                    if entity_type != Echelon.DEPARTEMENTAL:
                        logger.info(f"Critical: No matching record found for non departmental entity: {name} ({code})")
                    else:
                        logger.info(f"Warning: No matching record found for department entity: {name} ({code})")
                elif entity_type != record.entity_type:
                    logger.warning(f"Warning: Entity type mismatch for {name} ({code}): expected {entity_type}, found {record.entity_type}")
                else:
                    logger.info(f"Info: Enriching entity {record.name} ({record.code_ffvb}) with code {code}")
                    record.enrich(num_ffvb=code)

        
        
        
class EntityDirectoryParser(HttpDocumentParser[EntityRecord]):
    """
    Parser for entity directory data from the FFVolley system.
    """
    
    data: dict[Echelon, dict[str, str]] = {
        Echelon.REGIONAL : {
            "fiche_heading": "Fiche de la Ligue",
            "parent_heading": "Liste des Comités Départementaux",
        },
        Echelon.DEPARTEMENTAL : {
            "fiche_heading": "Fiche du Comité Départemental",
            "parent_heading": "Ligue Régionale",
        }
    }
    
    def parse(self, document: HttpDocument) -> list[EntityRecord]:
        raise NotImplementedError("This parser is only used for enriching existing entities, not for parsing new ones.")

    def enrich_record(self, record: EntityRecord, document: HttpDocument) -> None:
        """
        Parse the given HTTP document and extract a dictionary of Entity objects.

        Args:
            document (HttpDocument): The HTTP document to parse.
            entities (list[EntityRecord]): The list of entities to use for the directory.
        """
        soup = self.get_soup(document)
        
        fiche_data: dict[str, Any] = self.extract_fiche(soup, record.entity_type)
        parents: list[str] = self.extract_parent(soup, record.entity_type)
        clubs: list[str] = self.extract_clubs(soup)
        logger.info(f"Enriching entity {record.name} ({record.code_ffvb}) with data: {list((k, v) for k, v in fiche_data.items() if v is not None)}, parents: {parents}, clubs: {clubs}")
        record.enrich(
            **fiche_data,
            parents_code=parents,
            clubs_code=clubs
        )
        
    def extract_fiche(self, soup: BeautifulSoup, entity_type: Echelon) -> dict[str, Any]:
        """Extract the entity contacts, address and president."""
        address: list[str] = []
        phone_numbers: list[str] = []
        email: str | None = None
        website: str | None = None
        president: str | None = None
        heading: Tag = self.find_heading(soup, self.data[entity_type]["fiche_heading"])
        heading_row: Tag | None = heading.find_parent("tr")
        if heading_row is None:
            raise ValueError("Entity heading has no parent row")
        details_row: Tag | None = heading_row.find_next_sibling()
        if details_row is None:
            raise ValueError("Entity details row not found")
        for column in details_row.find_all("td", class_="lienblanc_pt"):
            column_heading: str | None = self.clean_text(column)
            if column_heading not in {"Coordonnées", "Siège Social", "Divers"}:
                continue
            column_parent: Tag | None = column.parent
            if column_parent is None:
                continue
            column_grandparent: Tag | None = column_parent.parent
            if column_grandparent is None:
                continue
            rows = column_grandparent.find_all("tr", recursive=False)
            for row in rows:
                cells = row.find_all("td", recursive=False)
                if len(cells) != 2:
                    continue
                label = self.clean_text(cells[0]) or ""
                value = self.clean_text(cells[1]) or ""
                if column_heading == "Coordonnées":
                    if label in {"Tél", "Téléphone", "Tél.2", "Portable"}:
                        phone_numbers.append(value)
                    else:
                        link = cells[1].find("a", href=True)
                        if link is not None:
                            link_href = link["href"].strip()
                            if link_href.startswith("mailto:"):
                                email = link_href.removeprefix("mailto:")
                            elif link_href.startswith(("http://", "https://", "//")):
                                website = link_href
                elif column_heading == "Siège Social":
                    address.append(value)
                elif column_heading == "Divers":
                    if "Président" in label:
                        president = value
        return {
            "phone_numbers": phone_numbers or None,
            "email": email or None,
            "website": website or None,
            "headquarters_address": address or None,
            "president": president or None,
        }


    def extract_parent(self, soup: BeautifulSoup, entity_type: Echelon) -> list[str]:
        """Extract the parent entity code from the entity directory page."""
        try:
            heading: Tag = self.find_heading(soup, self.data[entity_type]["parent_heading"])
        except ValueError:
            logger.warning(f"Parent heading not found for entity type {entity_type}")
            return []
        table = heading.find_parent("table")

        if table is None:
            raise ValueError("Parent table not found")

        parents: list[str] = []
        for row in table.find_all("tr"):
            cell = row.find("td", class_="liensuite4_gd", align="center")
            code = self.clean_text(cell)
            if not code or not re.match(r"^\d{3}$", code):
                continue
            parents.append(code)
        return parents


    def extract_clubs(self, soup: BeautifulSoup) -> list[str]:
        """Extract all club codes from the entity directory page."""
        heading: Tag = self.find_heading(soup, "Liste des Clubs")
        table: Tag | None = heading.find_parent("table")

        if table is None:
            raise ValueError("Club listing table not found")

        clubs: list[str] = []
        for row in table.find_all("tr"):
            cell = row.find("td", class_="lienquestion", align="center")
            code = self.clean_text(cell)
            if not code or not re.match(r"^\d{7}$", code):
                continue
            clubs.append(code)
        return clubs




from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin


def text_of(tag: Tag | None) -> str | None:
    """Extract normalized text, returning None for missing/empty values."""
    if tag is None:
        return None

    value = tag.get_text(" ", strip=True)
    return value or None


def input_values(tag: Tag) -> dict[str, str]:
    """Collect hidden/form input values contained in a tag."""
    return {
        name: str(value)
        for element in tag.select("input[name]")
        if (name := element.get("name"))
        and (value := element.get("value")) is not None
    }


def first_input_value(tag: Tag, name: str) -> str | None:
    """Return the first input value with the requested name."""
    element = tag.select_one(f'input[name="{name}"]')
    return element.get("value") if element else None


def get_mail(tag: Tag) -> str | None:
    """Extract the first email address exposed by a mailto link."""
    link = tag.select_one('a[href^="mailto:"]')
    if link is None:
        return None

    return link.get("href", "").removeprefix("mailto:").strip() or None


def get_website(tag: Tag, base_url: str) -> str | None:
    """Extract an external website URL, excluding mailto links."""
    for link in tag.select("a[href]"):
        href = link.get("href", "").strip()

        if not href or href.startswith(("mailto:", "javascript:", "#")):
            continue

        url = urljoin(base_url, href)

        if url.startswith(("http://", "https://")):
            # Ignore links to the FFVolley application itself.
            if "ffvbbeach.org/ffvbapp/" not in url:
                return url

    return None


def direct_rows(table: Tag) -> list[Tag]:
    """Get rows belonging to a table, excluding rows of nested tables."""
    rows = table.find("tbody", recursive=False)

    if rows is None:
        rows = table

    return rows.find_all("tr", recursive=False)


def table_heading(table: Tag) -> str | None:
    """Read the title in the first direct row of a table."""
    rows = direct_rows(table)

    if not rows:
        return None

    return text_of(rows[0])


def find_table(soup: BeautifulSoup, heading: str) -> Tag:
    """Find the table whose first row has the given title."""
    for table in soup.find_all("table"):
        if table_heading(table) == heading:
            return table

    raise ValueError(f"Table not found: {heading!r}")


def extract_key_values(table: Tag) -> dict[str, str]:
    """
    Extract label/value pairs from a detail table.

    Rows with no textual label are intentionally ignored;
    address lines are handled separately.
    """
    result: dict[str, str] = {}

    for row in table.find_all("tr"):
        cells = row.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        label = text_of(cells[0])
        value = text_of(cells[1])

        if label and value:
            result[label.rstrip(":").strip()] = value

    return result


def extract_section(
    soup: BeautifulSoup,
    heading: str,
) -> dict[str, Any]:
    """Extract one detail section such as Coordonnées or Divers."""
    table = find_table(soup, heading)
    values = extract_key_values(table)

    return {
        "fields": values,
        "email": get_mail(table),
        "website": get_website(table, BASE_URL),
    }


BASE_URL = "https://www.ffvbbeach.org/ffvbapp/"


@dataclass
class League:
    name: str | None
    code: str | None
    contacts: dict[str, Any]
    headquarters: dict[str, Any]
    miscellaneous: dict[str, Any]


@dataclass
class Committee:
    code: str
    name: str
    parent_league_code: str | None
    email: str | None
    website: str | None
    form_values: dict[str, str] = field(default_factory=dict)


@dataclass
class Club:
    code: str
    name: str
    parent_league_code: str | None
    parent_committee_code: str | None
    label: str | None
    email: str | None
    website: str | None
    results_code: str | None
    ranking_code: str | None
    form_values: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedLeaguePage:
    league: League
    committees: list[Committee]
    clubs: list[Club]


def parse_league_page(
    html: str,
    base_url: str = BASE_URL,
) -> ParsedLeaguePage:
    soup = BeautifulSoup(html, "lxml")

    # ---- League identity and detail sections ----

    title_row = next(
        (
            row
            for row in soup.find_all("tr")
            if (text := text_of(row))
            and text.startswith("Ligue ")
        ),
        None,
    )

    league_name = None
    if title_row is not None:
        league_name = text_of(title_row)

        if league_name:
            league_name = league_name.removeprefix("Ligue ").strip()

    # The supplied HTML does not expose a reliable league code.
    # Do not confuse the form value "0" with an actual league ID.
    league_code = None

    contacts = extract_section(soup, "Coordonnées")
    headquarters = extract_section(soup, "Siège Social")
    miscellaneous = extract_section(soup, "Divers")

    league = League(
        name=league_name,
        code=league_code,
        contacts=contacts,
        headquarters=headquarters,
        miscellaneous=miscellaneous,
    )

    # ---- Committees ----

    committee_table = find_table(
        soup, "Liste des Comités Départementaux"
    )

    committees: list[Committee] = []

    for row in committee_table.find_all("tr"):
        form = input_values(row)

        if "ws_new_comit" not in form:
            continue

        cells = row.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        code = text_of(cells[0])
        name = text_of(cells[1])

        if not code or not name:
            continue

        committees.append(
            Committee(
                code=code,
                name=name,
                parent_league_code=form.get("ws_new_ligue"),
                email=get_mail(row),
                website=get_website(row, base_url),
                form_values=form,
            )
        )

    # ---- Clubs ----

    club_table = find_table(soup, "Liste des Clubs")
    clubs: list[Club] = []

    for row in club_table.find_all("tr"):
        form = input_values(row)

        # Club rows contain an id_club input and a cnclub input
        # for results/rankings. Header and summary rows do not.
        if "id_club" not in form:
            continue

        cells = row.find_all("td", recursive=False)

        if len(cells) < 4:
            continue

        code = text_of(cells[0])
        name = text_of(cells[3])

        if not code or not name:
            continue

        # The first two cells after the club code represent label
        # columns in this table; the first one may be empty.
        label = text_of(cells[1]) or text_of(cells[2])

        # These values are retained exactly as exposed by the form.
        # A zero value is not converted into a real parent code.
        clubs.append(
            Club(
                code=code,
                name=name,
                parent_league_code=form.get("ws_new_ligue"),
                parent_committee_code=form.get("ws_new_comit"),
                label=label,
                email=get_mail(row),
                website=get_website(row, base_url),
                results_code=first_input_value(row, "cnclub"),
                ranking_code=first_input_value(row, "cnclub"),
                form_values=form,
            )
        )

    return ParsedLeaguePage(
        league=league,
        committees=committees,
        clubs=clubs,
    )