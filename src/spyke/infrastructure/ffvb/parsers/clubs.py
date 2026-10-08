from spyke.infrastructure.ffvb.dto import ClubRecord
from spyke.infrastructure.sources.http import HttpDocument
from spyke.infrastructure.ffvb.parsers.shared import get_soup


# logger = logging.getLogger(__name__)

# Entités non listées dans le menu déroulant du site mais accessibles directement
# HIDDEN_ENTITIES = [
#     EntityInfo(code="AALNV", nom="Compétitions Professionnelles LNV", type="nationale"),
#     EntityInfo(code="ACJEUNES", nom="Coupe de France Jeunes", type="nationale"),
# ]


class ClubParser:
    """
    Parser for entities data from the FFVolley system.
    """

    def parse(self, document: HttpDocument) -> list[ClubRecord]:
        """
        Parse the given HTTP document and extract a list of Entity objects.

        Args:
            document (HttpDocument): The HTTP document to parse.

        Returns:
            list[Entity]: A list of Entity objects extracted from the document.
        """
        soup = get_soup(document)
        clubs: list[ClubRecord] = []

        select = soup.find("select", {"name": "sel_entites"})

        if not select:
            raise ValueError("Select 'sel_entites' not found in the document")
        print(f"select: {select}")
        for option in select.find_all("option"):
            val = option.get("value")
            print(f"option: {option}, val: {val}")
            code = val.strip() if isinstance(val, str) else ""
            name = option.text.strip()

            if not code or code == "0" or code.startswith("-"):
                continue

            entities.append(EntityRecord(code_ffvb=code, name=name))

        return entities

    def parse_entity(self, document: HttpDocument, ligue_code: str) -> None:
        """Parse le HTML renvoyé par rech_aff_club.php pour une ligue."""
        soup = get_soup(document)

        # 1. Extraction Ligue
        title_td = soup.find("td", class_="titreblanc_gd")
        ligue_nom = default_ligue_nom
        if title_td:
            t_text = title_td.get_text(strip=True)
            if t_text.lower().startswith("ligue "):
                ligue_nom = t_text[6:].strip()
            elif t_text:
                ligue_nom = t_text

        telephone = None
        email = None
        site_web = None
        adresse_siege = None
        president = None

        for tr in soup.find_all("tr"):
            for td in tr.find_all("td", class_="liengris_pt"):
                label = td.get_text(strip=True).lower()
                val_td = td.find_next_sibling("td")
                if val_td:
                    val = val_td.get_text(strip=True)
                    if "tél" in label or "tel" in label:
                        telephone = _clean_str(val)
                    elif "président" in label or "president" in label:
                        president = _clean_str(val)

        mail_a = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mail_a:
            email = _clean_str(mail_a.get("href", "").replace("mailto:", "").strip())

        site_a = soup.find("a", href=re.compile(r"^https?://", re.I), target="_blank")
        if site_a and "ffvb" not in site_a.get("href", "").lower():
            site_web = _clean_str(site_a.get("href", "").strip())

        ligue_info = ParsedLigue(
            code=ligue_code,
            nom=ligue_nom,
            telephone=telephone,
            email=email,
            site_web=site_web,
            adresse_siege=adresse_siege,
            president=president,
        )

        # 2. Extraction Comités Départementaux
        comites: list[ParsedComite] = []
        seen_comites: set[str] = set()
        for tr in soup.find_all("tr"):
            code_td = tr.find("td", class_="liensuite4_gd", align="center")
            if code_td and re.match(r"^\d{3}$", code_td.get_text(strip=True)):
                c_code = code_td.get_text(strip=True)
                if c_code in seen_comites:
                    continue
                nom_td = code_td.find_next_sibling("td", class_="liensuite4_gd")
                c_nom = nom_td.get_text(strip=True) if nom_td else ""
                c_mail = None
                c_site = None
                m_link = tr.find("a", href=re.compile(r"^mailto:", re.I))
                if m_link:
                    c_mail = _clean_str(m_link.get("href", "").replace("mailto:", ""))
                w_link = tr.find("a", href=re.compile(r"^https?://", re.I))
                if w_link and "ffvb" not in w_link.get("href", "").lower():
                    c_site = _clean_str(w_link.get("href"))

                seen_comites.add(c_code)
                comites.append(
                    ParsedComite(
                        code=c_code,
                        numero_departement=_departement_from_comite_code(c_code),
                        nom=c_nom,
                        ligue_code=ligue_code,
                        email=c_mail,
                        site_web=c_site,
                    )
                )

        # 3. Extraction Clubs
        clubs_dict: dict[str, ParsedClub] = {}
        for tr in soup.find_all("tr"):
            c_code_td = tr.find("td", class_="lienquestion", align="center")
            if not c_code_td:
                continue
            c_code = c_code_td.get_text(strip=True)
            if not re.match(r"^\d{7}$", c_code):
                continue

            nom_td = tr.find(
                lambda tag: (
                    tag.name == "td"
                    and "lienquestion" in tag.get("class", [])
                    and tag.get("align") != "center"
                )
            )
            c_nom = nom_td.get_text(strip=True) if nom_td else ""
            if not c_nom:
                continue

            c_comite = c_code[:3]

            c_mail = None
            m_link = tr.find("a", href=re.compile(r"^mailto:", re.I))
            if m_link:
                c_mail = _clean_str(m_link.get("href", "").replace("mailto:", ""))

            c_site = None
            s_link = tr.find("a", href=re.compile(r"^https?://", re.I))
            if s_link and "ffvb" not in s_link.get("href", "").lower():
                c_site = _clean_str(s_link.get("href"))

            if c_code not in clubs_dict:
                clubs_dict[c_code] = ParsedClub(
                    code_ffvb=c_code,
                    nom=c_nom,
                    ligue_code=ligue_code,
                    comite_code=c_comite,
                    email=c_mail,
                    site_web=c_site,
                )
            else:
                if not clubs_dict[c_code].email and c_mail:
                    clubs_dict[c_code].email = c_mail
                if not clubs_dict[c_code].site_web and c_site:
                    clubs_dict[c_code].site_web = c_site

        return ligue_info, comites, list(clubs_dict.values())
