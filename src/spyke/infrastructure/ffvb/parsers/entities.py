from spyke.infrastructure.ffvb.dto import EntityRecord
from spyke.infrastructure.ffvb.parsers import entities
from spyke.infrastructure.sources.http import HttpDocument
from spyke.domain.rules.categorisation import get_echelon_from_code_ffvb
from spyke.infrastructure.ffvb.parsers.base import HttpDocumentParser
from spyke.domain.enums import Echelon
from typing import Any
from bs4 import BeautifulSoup, Tag
import re


# logger = logging.getLogger(__name__)

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

        if not select:
            raise ValueError("Select 'sel_entites' not found in the document")
        for option in select.find_all("option"):
            val = option.get("value")
            code = val.strip() if isinstance(val, str) else ""
            name = option.text.strip()

            if not code or code == "0" or code.startswith("-") or code == "ZZALL":
                print(f"Skipping invalid option: {name} ({code})")
                continue
            
            
            # Exemples de codes et noms d'entités qui ne sont pas bien traités
            # PTRA73 CD73 - Comité Savoie/Haute-Savoie
            # LIFL HAUTS-DE-FRANCE
            # PTPI02 l'Aisne
            # PTFL59 CD59 - Comité Nord
            # PTPI60 l'Oise
            
            entity_type = get_echelon_from_code_ffvb(code)
            if entity_type == Echelon.DEPARTEMENTAL:
                # PEut etre strip avant ou nettoyer 
                if not name.startswith("CD") and "-" in name:
                    print(f"Warning: Departmental entity name does not start with 'CD': {name} ({code})")
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
                    # To improve departmental entity matching, we can try to match by code prefix
                    record = next((r for r in records if code[0] == "0" and code[1:] in r.code_ffvb and r.entity_type == Echelon.DEPARTEMENTAL), None)
                    if record is not None:
                        print(f"Warning: No exact match found for {name} ({code}), using partial match: {name} -> {record.name}")
                if record is None:
                    assert entity_type == Echelon.DEPARTEMENTAL, f"Unexpected entity type for unmatched record: {entity_type} ({name} - {code})"
                    print(f"Warning: No matching record found for department entity: {name} ({code})")
                elif entity_type != record.entity_type:
                    print(f"Warning: Entity type mismatch for {name} ({code}): expected {entity_type}, found {record.entity_type}")
                else:
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
        print(f"Enriching entity {record.name} ({record.code_ffvb}) with data: {list((k, v) for k, v in fiche_data.items() if v is not None)}, parents: {parents}, clubs: {clubs}")
        record.enrich(
            **fiche_data,
            parents_code=parents,
            clubs_code=clubs
        )
        
        
    def extract_fiche(self, soup: BeautifulSoup, entity_type: Echelon) -> dict[str, Any]:
        """Extract the entity contacts, address and president."""
        heading: Tag = self.find_heading(soup, self.data[entity_type]["fiche_heading"])
        heading_row: Tag | None = heading.find_parent("tr")
        if heading_row is None:
            raise ValueError("Entity heading has no parent row")
        details_row: Tag | None = heading_row.find_next_sibling("tr")
        if details_row is None:
            raise ValueError("Entity details row not found")
        result: dict[str, Any] = {
            "phone_number": None,
            "email": None,
            "website": None,
            "headquarters_address": None,
            "president": None,
        }
        for table in details_row.find_all("table"):
            rows = table.find_all("tr", recursive=False)
            if not rows:
                rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td", recursive=False)
                if len(cells) < 2:
                    continue
                label = self.clean_text(cells[0]) or ""
                value = self.clean_text(cells[1])
                if label in {"Tél", "Téléphone"}:
                    result["phone"] = value
                elif "Président" in label:
                    result["president"] = value
                elif value and (
                    re.search(r"\b\d{5}\b", value)
                    or "AVENUE" in value.upper()
                    or "RUE " in value.upper()
                    or "BOULEVARD" in value.upper()
                ):
                    result["headquarters_address"] = value
                result.update(
                    {
                        key: link_value
                        for key, link_value in self.extract_links(row).items()
                        if link_value is not None
                    }
                )
        return result

    def extract_links(self, container: Tag) -> dict[str, str | None]:
        """Extract email and website links from a container."""
        email: str | None = None
        website: str | None = None
        
        # Clean typing
        for link in container.find_all("a", href=True):
            href: str | None = link["href"].strip()
            if href.lower().startswith("mailto:"):
                email = href.removeprefix("mailto:")
            elif href.startswith(("http://", "https://", "//")):
                website = href
        return {
            "email": email,
            "website": website,
        }

    def extract_parent(self, soup: BeautifulSoup, entity_type: Echelon) -> list[str]:
        """Extract the parent entity code from the entity directory page."""
        heading: Tag = self.find_heading(soup, self.data[entity_type]["parent_heading"])
        table = heading.find_parent("table")

        if table is None:
            raise ValueError("Parent table not found")

        parents: list[str] = []
        for row in table.find_all("tr"):
            cell = row.find("td", class_="liensuite4_gd", align="center")
            code = self.clean_text(cell)
            if not code or not re.match(r"^\d{3}$", code):
                #print(f"Warning: Skipping invalid parent code '{code}'")
                continue
            else:
                print(f"Info:                     Adding valid parent code '{code}'")
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
            cell = row.find("td", class_="liensuite4_gd", align="center")
            code = self.clean_text(cell)
            if not code or not re.match(r"^\d{7}$", code):
                #print(f"Warning: Skipping invalid club code '{code}'")
                continue
            else:
                print(f"Info:                     Adding valid club code '{code}'")
            clubs.append(code)
        return clubs

