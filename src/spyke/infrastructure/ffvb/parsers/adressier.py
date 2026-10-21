import csv
import html
import io
import logging

from spyke.infrastructure.ffvb.dto import TeamRecord, VenueRecord
from spyke.infrastructure.ffvb.parsers.base import CsvParser
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)

COL_ENTITE = 0
COL_POULE = 1
COL_NCLUB = 2  # Code club FFVB (ex: "0622126")
COL_NOM_CLUB = 3
COL_LIGUE = 4
COL_POSITION = 5
COL_COULEURS = 6
COL_PRESIDENT = 7  # Pdt
COL_ENTRAINEUR = 8  # Entr.
COL_ADJOINT = 9  # Adj.
COL_CORRESPONDANT = 10
COL_CO_ADR1 = 11
COL_CO_ADR2 = 12
COL_CO_ADR3 = 13
COL_CO_VILLE = 14
COL_CO_TEL = 15
COL_CO_PORT = 16
COL_CO_MAIL = 17
# Salle 1
COL_S1_NOM = 18
COL_S1_ADR1 = 19
COL_S1_ADR2 = 20
COL_S1_ADR3 = 21
COL_S1_VILLE = 22
COL_S1_TEL = 23
COL_S1_SOL = 24
COL_S1_CAP = 25
COL_S1_TRSP = 26
# Salle 2
COL_S2_NOM = 27
COL_S2_ADR1 = 28
COL_S2_ADR2 = 29
COL_S2_ADR3 = 30
COL_S2_VILLE = 31
COL_S2_TEL = 32
COL_S2_SOL = 33
COL_S2_CAP = 34
COL_S2_TRSP = 35

MIN_COLUMNS = 18  # Minimum pour les données de base (jusqu'à Co_Mail)


class AdressierParser(CsvParser[TeamRecord]):
    """Parser for addressier documents."""

    def parse(self, document: HttpDocument) -> list[TeamRecord]:
        """Parse an addressier document and return a list of records.

        Args:
            document (HttpDocument): The document to parse.

        Returns:
            list[TeamRecord]: The parsed records.
        """
        try:
            content = document.body.decode("windows-1252")
        except (UnicodeDecodeError, AttributeError):
            try:
                content = document.body.decode("latin-1")
            except Exception:
                logger.error("Impossible de décoder l'adressier")
                return []

        if not content.strip():
            logger.warning("Adressier vide")
            return []

        content = html.unescape(content)
        reader = csv.reader(io.StringIO(content), delimiter=";")
        teams: list[TeamRecord] = []

        for idx, row in enumerate(reader):
            if idx == 0:
                continue  # Skip header

            if len(row) < MIN_COLUMNS:
                logger.warning("Ligne %d ignorée : moins de %d colonnes", idx + 1, MIN_COLUMNS)
                continue

            co_addr: list[str] = []
            for col in [COL_CO_ADR1, COL_CO_ADR2, COL_CO_ADR3]:
                if addr := self._safe_get(row, col):
                    co_addr.append(addr)

            venues: list[VenueRecord] = []
            for name_c, adr1_c, adr2_c, adr3_c, city_c, tel_c, surf_c, cap_c, trsp_c in [
                (
                    COL_S1_NOM,
                    COL_S1_ADR1,
                    COL_S1_ADR2,
                    COL_S1_ADR3,
                    COL_S1_VILLE,
                    COL_S1_TEL,
                    COL_S1_SOL,
                    COL_S1_CAP,
                    COL_S1_TRSP,
                ),
                (
                    COL_S2_NOM,
                    COL_S2_ADR1,
                    COL_S2_ADR2,
                    COL_S2_ADR3,
                    COL_S2_VILLE,
                    COL_S2_TEL,
                    COL_S2_SOL,
                    COL_S2_CAP,
                    COL_S2_TRSP,
                ),
            ]:
                name = self._safe_get(row, name_c)
                if name:
                    address_lines: list[str] = []
                    for adr_col in [adr1_c, adr2_c, adr3_c]:
                        if adr := self._safe_get(row, adr_col):
                            address_lines.append(adr)
                    venues.append(
                        VenueRecord(
                            name=name,
                            address=address_lines or None,
                            city=self._safe_get(row, city_c),
                            phone_number=self._safe_get(row, tel_c),
                            surface=self._safe_get(row, surf_c),
                            capacity=self._safe_get_int(row, cap_c),
                            transport=self._safe_get(row, trsp_c),
                        )
                    )

            teams.append(
                TeamRecord(
                    club_code=self._safe_get(row, COL_NCLUB),
                    name=self._safe_get(row, COL_NOM_CLUB),
                    coach=self._safe_get(row, COL_ENTRAINEUR),
                    assistant_coach=self._safe_get(row, COL_ADJOINT),
                    venues=venues or None,
                    correspondant=self._safe_get(row, COL_CORRESPONDANT),
                    correspondant_address=co_addr or None,
                    correspondant_email=self._safe_get(row, COL_CO_MAIL),
                    correspondant_phone=self._safe_get(row, COL_CO_TEL),
                    correspondant_portable=self._safe_get(row, COL_CO_PORT),
                )
            )

        return teams
