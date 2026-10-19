import csv
import html
import io
import logging
import re

from spyke.domain.entities.organisation import Season
from spyke.domain.enums import RoleReferee
from spyke.infrastructure.ffvb.dto import MatchRecord, RefereeRecord
from spyke.infrastructure.ffvb.parsers.base import HttpDocumentParser
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)

COL_ENTITE = 0  # Entité
COL_JOURNEE = 1  # Jo
COL_MATCH = 2  # Match (code match, ex: "2FA002", "EMA051")
COL_DATE = 3  # Date (YYYY-MM-DD)
COL_HEURE = 4  # Heure (HH:MM)
COL_EQA_NO = 5  # EQA_no (N° club A, ex: "0132380")
COL_EQA_NOM = 6  # EQA_nom (Équipe A)
COL_EQB_NO = 7  # EQB_no (N° club B)
COL_EQB_NOM = 8  # EQB_nom (Équipe B)
COL_SET = 9  # Set  (" 3/1", " 0/3", " 3/P", "")
COL_SCORE = 10  # Score ("25-18,16-25,25-20" — scores détaillés par set)
COL_TOTAL = 11  # Total ("75-53" — total points)
COL_SALLE = 12  # Salle
COL_ARB1_LIC = 13  # Arb1_Lic
COL_ARB1_NOM = 14  # Arb1_Nom
COL_ARB1_LR = 15  # Arb1_LR (ligue régionale)
COL_ARB1_CD = 16  # Arb1_CD (comité départemental)
COL_ARB2_LIC = 17  # Arb2_Lic
COL_ARB2_NOM = 18  # Arb2_Nom
COL_ARB2_LR = 19  # Arb2_LR
COL_ARB2_CD = 20  # Arb2_CD
COL_JDL1_LIC = 21  # Jdl1_Lic
COL_JDL1_NOM = 22  # Jdl1_Nom
COL_JDL2_LIC = 23  # Jdl2_Lic
COL_JDL2_NOM = 24  # Jdl2_Nom
COL_JDL3_LIC = 25  # Jdl3_Lic
COL_JDL3_NOM = 26  # Jdl3_Nom
COL_JDL4_LIC = 27  # Jdl4_Lic
COL_JDL4_NOM = 28  # Jdl4_Nom
COL_MRQ1_LIC = 29  # Mrq1_Lic
COL_MRQ1_NOM = 30  # Mrq1_Nom
COL_MRQ2_LIC = 31  # Mrq2_Lic
COL_MRQ2_NOM = 32  # Mrq2_Nom
COL_SUP_LIC = 33  # Sup_Lic
COL_SUP_NOM = 34  # Sup_Nom
COL_SLNV_LIC = 35  # Slnv_Lic
COL_SLNV_NOM = 36  # Slnv_Nom
COL_VID_LIC = 37  # Vid_Lic
COL_VID_NOM = 38  # Vid_Nom
# Colonne 39 : vide (trailing ;)

MIN_COLUMNS = 13  # Minimum requis pour un export valide (jusqu'à Salle)

# Timeout plus long pour l'export CSV (le serveur peut mettre > 45s)
EXPORT_TIMEOUT = 90


class CalendarParser(HttpDocumentParser[MatchRecord]):
    """Parse club listings and individual club pages from the FFVB directory."""

    def parse(self, document: HttpDocument, entity_code: str, season: Season) -> list[MatchRecord]:
        try:
            content = document.body.decode("latin-1")
        except (UnicodeDecodeError, AttributeError):
            try:
                content = document.body.decode("utf-8")
            except Exception:
                logger.error("Impossible de décoder l'export pour %s", entity_code)
                return []

        if not content.strip():
            logger.warning("Export vide pour %s (saison %s)", entity_code, season)
            return []

        # Unescape HTML entities (ex: &#039; for apostrophe) to prevent semicolons
        # from breaking the CSV delimiter ';'
        content = html.unescape(content)

        # Parse CSV (séparé par points-virgules)
        reader = csv.reader(io.StringIO(content), delimiter=";")
        matches: list[MatchRecord] = []
        for row_idx, row in enumerate(reader):  # Commence à la ligne 2 pour ignorer l'en-tête
            # Ignorer la première ligne (en-têtes)
            if row_idx == 0:
                continue

            if len(row) != 40:
                logger.critical(
                    "Ligne %d pour %s (saison %s) a un nombre inattendu de colonnes (%d au lieu de 40): %s",
                    row_idx + 1,
                    entity_code,
                    season,
                    len(row),
                    row,
                )

            code_match = self._clean_str(row[COL_MATCH])
            if not code_match:
                logger.warning(
                    "Ligne %d pour %s (saison %s) a un code de match manquant: %s",
                    row_idx + 1,
                    entity_code,
                    season,
                    row,
                )
                continue

            # Équipes
            equipe_a_nom = self._clean_str(row[COL_EQA_NOM])
            equipe_b_nom = self._clean_str(row[COL_EQB_NOM])

            club_a_code = self._clean_str(row[COL_EQA_NO])
            club_b_code = self._clean_str(row[COL_EQB_NO])

            # Score sets depuis la colonne Set (" 3/1", " P/3", etc.)
            set_result: tuple[str, str] | None = None
            if (
                len(row) > COL_SET
                and (set_str := self._clean_str(row[COL_SET]))
                and len(parts := set_str.split("/")) == 2
                and (sa := self._clean_str(parts[0]))
                and (sb := self._clean_str(parts[1]))
            ):
                set_result = (sa, sb)

            # Scores détaillés par set depuis la colonne Score ("25-18,16-25,25-20")
            sets: list[tuple[int, int]] | None = None
            if len(row) > COL_SCORE and (score_str := self._clean_str(row[COL_SCORE])):
                for part in score_str.split(","):
                    scores = part.split("-")
                    if (
                        len(scores) == 2
                        and (sa := self._clean_str(scores[0]))
                        and (sb := self._clean_str(scores[1]))
                        and sa.isdigit()
                        and sb.isdigit()
                    ):
                        sets = sets or []
                        sets.append((int(sa), int(sb)))

            # Date et heure
            date_match: str | None = None
            if len(row) > COL_DATE and row[COL_DATE] and re.match(r"^\d{4}-\d{2}-\d{2}$", row[COL_DATE]):
                date_match = row[COL_DATE]
            heure: str | None = None
            if len(row) > COL_HEURE and row[COL_HEURE] and re.match(r"^\d{2}:\d{2}$", row[COL_HEURE]):
                heure = row[COL_HEURE]
            salle: str | None = None
            if len(row) > COL_SALLE and row[COL_SALLE]:
                salle = self._clean_str(row[COL_SALLE])
            journee: str | None = None
            if len(row) > COL_JOURNEE and row[COL_JOURNEE]:
                journee = self._clean_str(row[COL_JOURNEE])

            # Arbitres
            referees: list[RefereeRecord] = []
            for lic_col, nom_col, lr_col, cd_col, role in [
                (COL_ARB1_LIC, COL_ARB1_NOM, COL_ARB1_LR, COL_ARB1_CD, RoleReferee.PREMIER),
                (COL_ARB2_LIC, COL_ARB2_NOM, COL_ARB2_LR, COL_ARB2_CD, RoleReferee.SECOND),
            ]:
                if nom_col < len(row):
                    arb_nom = self._clean_str(row[nom_col])
                    arb_lic = self._clean_str(row[lic_col]) if lic_col < len(row) else None
                    # Filtrer les licences/noms "0" (placeholder FFVB pour vide)
                    if arb_lic == "0":
                        arb_lic = None
                    if arb_nom == "0":
                        arb_nom = None
                    if arb_nom or arb_lic:
                        referees.append(
                            RefereeRecord(
                                licence=arb_lic or "",
                                name=arb_nom or "",
                                entity=self._clean_str(row[lr_col]) if lr_col < len(row) else None,
                                department=self._clean_str(row[cd_col]) if cd_col < len(row) else None,
                                role=role,
                            )
                        )

            # Juges de ligne (paires licence/nom : colonnes 21-28)
            juges: list[str] | None = None
            for jl_nom_col in (COL_JDL1_NOM, COL_JDL2_NOM, COL_JDL3_NOM, COL_JDL4_NOM):
                if jl_nom_col < len(row) and (jl := self._clean_str(row[jl_nom_col])):
                    juges = juges or []
                    juges.append(jl)

            # Marqueurs (paires licence/nom : colonnes 29-32)
            marqueurs: list[RefereeRecord] = []
            for mrq_nom_col, mrq_lic_col, role in (
                (COL_MRQ1_NOM, COL_MRQ1_LIC, RoleReferee.MARQUEUR),
                (COL_MRQ2_NOM, COL_MRQ2_LIC, RoleReferee.MARQUEUR_ASSISTANT),
            ):
                if (
                    mrq_lic_col < len(row)
                    and (mrq := self._clean_str(row[mrq_nom_col]))
                    and (mrq_lic := self._clean_str(row[mrq_lic_col]))
                ):
                    marqueurs.append(
                        RefereeRecord(
                            licence=mrq_lic,
                            name=mrq,
                            role=role,
                        )
                    )

            # Entité source réelle de la ligne si renseignée (ex: AALNV dans export ABCCS)
            entity = self._clean_str(row[COL_ENTITE]) if len(row) > COL_ENTITE else None
            if entity and entity != entity_code:
                logger.warning(
                    "Ligne %d pour %s (saison %s) a une entité source différente: %s",
                    row_idx + 1,
                    entity_code,
                    season,
                    entity,
                )

            match_info = MatchRecord(
                code=code_match,
                entity=entity,
                a_team=equipe_a_nom,
                b_team=equipe_b_nom,
                a_club_code=club_a_code,
                b_club_code=club_b_code,
                date=date_match,
                time=heure,
                score=set_result,
                venue=salle,
                sets=sets or None,
                referees=referees or None,
                marqueurs=marqueurs or None,
                journee=journee,
            )

            matches.append(match_info)
        return matches
