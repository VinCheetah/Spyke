"""
Résolution des badges et hiérarchie exhaustive des niveaux de volley-ball FFVB.

Couvre la totalité des échelons administratifs et sportifs :
1. Coupe de France (Senior & Jeunes)
2. Professionnel (Pro A, Pro B)
3. Élite (Elite, Elite Avenir, Jeunes Elite)
4. National (N1, N2, N3, National générique)
5. Régional (Prénat, R1, R2, R3, R4, Régional générique, Jeunes Régional)
6. Départemental (Préreg, D1, D2, D3, D4, Dép générique, Jeunes Dép)
7. Loisir / Brassage / Détente

Fournit une classification multi-niveaux précise :
- Categorie principale (échelon fédéral)
- Division (numéro précis le cas échéant)
- Indicateur Jeunes
- Label affiché et classe CSS pour les badges
- Rang numérique stable de 0 à 18 pour les tris et graphiques
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from spyke.domain.enums import Division, Category, PlayFormat, PlayVariant, Echelon
from spyke.domain.entities.organisation import League
from spyke.domain.rules.categorisation import is_youth_category, normalize_text_upper


@dataclass(frozen=True)
class CompetitionInfo:
    """Structure descriptive et sportive complète du niveau d'une compétition/poule/équipe."""

    division: Division
    format: PlayFormat = PlayFormat.SIX_VS_SIX
    variant: PlayVariant = PlayVariant.STANDARD


def determine_competition_info(
    league: League,
    categorie: Category,
    competition_name: str,
    competition_group_name: str,
    poule_code: str,
) -> CompetitionInfo:
    """
    Détermine la division d'une compétition en fonction de ses attributs.

    Retourne un objet CompetitionInfo complet.
    """
    play_format = PlayFormat.SIX_VS_SIX
    play_variant = PlayVariant.STANDARD
    division: Division = Division.UNKNOW

    entity = league.code_ffvb
    echelon = league.echelon

    is_youth: bool = is_youth_category(categorie)

    parts = [competition_name, competition_group_name, poule_code]
    full_text = normalize_text_upper(" ".join(str(p) for p in parts))

    if re.search(r"\b4\s*[xX]\s*4\b", full_text):
        play_format = PlayFormat.FOUR_VS_FOUR
    elif re.search(r"\b3\s*[xX]\s*3\b", full_text):
        play_format = PlayFormat.THREE_VS_THREE
    elif re.search(r"\b2\s*[xX]\s*2\b", full_text):
        play_format = PlayFormat.TWO_VS_TWO

    if entity == "ADPVA" or "ASSIS" in full_text or "VOLLEYASSIS" in full_text:
        play_variant = PlayVariant.ASSIS
    elif entity == "ADPV" or "SOURD" in full_text or "VOLLEYSOURD" in full_text:
        play_variant = PlayVariant.SOURD
    elif entity == "AVBEACH" or "BEACH" in full_text:
        play_variant = PlayVariant.BEACH

    # Neutraliser les formats de jeu (4x4, etc.) pour ne pas fausser la détection
    clean_text = re.sub(r"\b[2346]\s*[xX]\s*[2346]\b", " ", full_text)

    is_prereg = bool(
        re.search(r"\b(PRE\s*-?\s*REG(?:IONAL(?:E|AUX|ES?)?)?|PREREG|PRM|PRF)\b", clean_text)
        or re.search(r"\bACCESSION\s+(?:A\s+LA\s+)?REGIONAL(?:E|AUX|ES?)?\b", clean_text)
        or poule_code.startswith(("PRM", "PRF", "PR"))
    )

    if echelon == Echelon.DEPARTEMENTAL:
        if is_youth:
            division = Division.JEUNES_DEPARTEMENTALE
        elif (
            re.search(r"\b(PRE\s*-?\s*REG(?:IONAL(?:E|AUX|ES?)?)?|PREREG|PRM|PRF)\b", clean_text)
            or re.search(r"\bACCESSION\s+(?:A\s+LA\s+)?REGIONAL(?:E|AUX|ES?)?\b", clean_text)
            or re.search(r"\bACCESSION\s+PREREGIONAL(?:E|AUX|ES?)?\b", clean_text)
            or re.search(r"\bMONTEE\s+REGION\b", clean_text)
            or poule_code.startswith(("PRM", "PRF", "PR"))
        ):
            division = Division.PRE_REGIONALE
        elif re.search(r"\b(DEPARTEMENTALE?\s*1|D1|D1[MF])\b", clean_text):
            division = Division.DEPARTEMENTALE_1
        elif re.search(r"\b(DEPARTEMENTALE?\s*2|D2|D2[MF])\b", clean_text):
            division = Division.DEPARTEMENTALE_2
        elif re.search(r"\b(DEPARTEMENTALE?\s*3|D3|D3[MF])\b", clean_text):
            division = Division.DEPARTEMENTALE_3
        elif re.search(r"\b(DEPARTEMENTALE?\s*4|D4|D4[MF])\b", clean_text):
            division = Division.DEPARTEMENTALE_4
        else:
            division = Division.DEPARTEMENTALE

    elif echelon == Echelon.REGIONAL:
        if is_youth:
            if re.search(r"\b(ELITE|ÉLITE)\b", clean_text):
                division = Division.JEUNES_ELITE
            division = Division.JEUNES_REGIONALE
        elif is_prereg:
            division = Division.PRE_REGIONALE
        elif re.search(
            r"\b(PRE\s*-?\s*NAT(?:IONAL(?:E|AUX|ES?)?)?|PRE_?NAT|PRENAT|PNM|PNF)\b", clean_text
        ):
            division = Division.PRE_NATIONALE
        elif re.search(r"\b(REGIONALE?\s*1|R1|R1[MF])\b", clean_text):
            division = Division.REGIONALE_1
        elif re.search(r"\b(REGIONALE?\s*2|R2|R2[MF])\b", clean_text):
            division = Division.REGIONALE_2
        elif re.search(r"\b(REGIONALE?\s*3|R3|R3[MF])\b", clean_text):
            division = Division.REGIONALE_3
        elif re.search(r"\b(REGIONALE?\s*4|R4|R4[MF])\b", clean_text):
            division = Division.REGIONALE_4
        else:
            division = Division.REGIONALE

    elif echelon == Echelon.NATIONAL:
        is_cdf = (
            "COUPE DE FRANCE" in clean_text
            or bool(re.search(r"\bCDF\b", clean_text))
            or entity in ("ACJEUNES", "APVA", "ADPVA")
        )
        if is_cdf:
            if play_variant == PlayVariant.ASSIS:
                division = Division.COUPE_DE_FRANCE_ASSIS
            elif play_variant == PlayVariant.SOURD:
                division = Division.COUPE_DE_FRANCE_SOURD
            elif play_variant == PlayVariant.BEACH:
                division = Division.COUPE_DE_FRANCE_BEACH
            elif is_youth:
                division = Division.COUPE_DE_FRANCE_JEUNES
            else:
                division = Division.COUPE_DE_FRANCE
        elif entity == "AALNV":
            if re.search(r"\b(PRO\s*B|LIGUE\s*B\b|LBM\b|LBF\b)\b", clean_text):
                division = Division.PRO_B
            if re.search(r"\b(PRO\s*A|LIGUE\s*A\b|LAM\b|LAF\b|MARMARA|SAFORELLE)\b", clean_text):
                division = Division.PRO_A
        elif re.search(r"\b(ELITE|ÉLITE)\b", clean_text) or poule_code.startswith(("EM", "EF")):
            if re.search(r"\b(ELITE|ÉLITE)\s*AVENIR\b", clean_text):
                division = Division.ELITE_AVENIR
            else:
                division = Division.ELITE
        elif re.search(r"\b(NATIONALE?\s*1|N1|1\s*[MF]|NM1|NF1)\b", clean_text):
            division = Division.NATIONALE_1
        elif re.search(r"\b(NATIONALE?\s*2|N2|2\s*[MF]|NM2|NF2|2FA|2MA)\b", clean_text):
            division = Division.NATIONALE_2
        elif re.search(r"\b(NATIONALE?\s*3|N3|3\s*[MF]|NM3|NF3|3FA|3MA)\b", clean_text):
            division = Division.NATIONALE_3
        else:
            division = Division.NATIONALE

    return CompetitionInfo(
        division=division,
        format=play_format,
        variant=play_variant,
    )
