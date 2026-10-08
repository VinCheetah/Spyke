from spyke.infrastructure.ffvb.dto import EntityRecord
from spyke.infrastructure.sources.http import HttpDocument
from spyke.infrastructure.ffvb.parsers.shared import get_soup


# logger = logging.getLogger(__name__)

# Entités non listées dans le menu déroulant du site mais accessibles directement
# HIDDEN_ENTITIES = [
#     EntityInfo(code="AALNV", nom="Compétitions Professionnelles LNV", type="nationale"),
#     EntityInfo(code="ACJEUNES", nom="Coupe de France Jeunes", type="nationale"),
# ]


class EntityParser:
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
        soup = get_soup(document)
        entities: list[EntityRecord] = []

        select = soup.find("select", {"name": "sel_entites"})

        if not select:
            raise ValueError("Select 'sel_entites' not found in the document")
        for option in select.find_all("option"):
            val = option.get("value")
            code = val.strip() if isinstance(val, str) else ""
            name = option.text.strip()

            if not code or code == "0" or code.startswith("-"):
                continue

            entities.append(EntityRecord(code_ffvb=code, name=name))

        return entities
