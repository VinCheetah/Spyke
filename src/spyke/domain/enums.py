"""
Énumérations métier pour PyVolley.
"""

from enum import StrEnum


class Gender(StrEnum):
    """Genre de la compétition ou de l'équipe."""

    MASCULIN = "MASCULIN"
    FEMININ = "FEMININ"
    MIXTE = "MIXTE"


class Category(StrEnum):
    """Catégorie d'âge FFVB."""

    SENIOR = "SENIOR"
    M21 = "M21"
    M18 = "M18"
    M15 = "M15"
    M13 = "M13"
    M11 = "M11"
    JEUNES = "JEUNES"
    VETERAN = "VETERAN"


class Division(StrEnum):
    """Niveau d'échelon de compétition."""

    PRO_A = "PRO A"
    PRO_B = "PRO B"
    ELITE = "ELITE"
    ELITE_AVENIR = "ELITE AVENIR"
    NATIONALE_1 = "NATIONALE 1"
    NATIONALE_2 = "NATIONALE 2"
    NATIONALE_3 = "NATIONALE 3"
    NATIONALE = "NATIONALE"
    COUPE_DE_FRANCE = "COUPE DE FRANCE"
    COUPE_DE_FRANCE_BEACH = "COUPE DE FRANCE BEACH"
    COUPE_DE_FRANCE_ASSIS = "COUPE DE FRANCE ASSIS"
    COUPE_DE_FRANCE_SOURD = "COUPE DE FRANCE SOURD"
    COUPE_DE_FRANCE_JEUNES = "COUPE DE FRANCE JEUNES"
    PRE_NATIONALE = "PRE_NATIONALE"
    REGIONALE_1 = "REGIONALE 1"
    REGIONALE = "REGIONALE"
    REGIONALE_2 = "REGIONALE 2"
    REGIONALE_3 = "REGIONALE 3"
    REGIONALE_4 = "REGIONALE 4"
    JEUNES_ELITE = "JEUNES ELITE"
    JEUNES_REGIONALE = "JEUNES REGIONALE"
    PRE_REGIONALE = "PRE_REGIONALE"
    DEPARTEMENTALE_1 = "DEPARTEMENTALE 1"
    DEPARTEMENTALE = "DEPARTEMENTALE"
    DEPARTEMENTALE_2 = "DEPARTEMENTALE 2"
    DEPARTEMENTALE_3 = "DEPARTEMENTALE 3"
    DEPARTEMENTALE_4 = "DEPARTEMENTALE 4"
    JEUNES_DEPARTEMENTALE = "JEUNES DEPARTEMENTALE"
    LOISIR = "LOISIR"
    UNKNOW = "UNKNOWN"


class Echelon(StrEnum):
    INTERNATIONAL = "INTERNATIONAL"
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    DEPARTEMENTAL = "DEPARTEMENTAL"


class TypeSanction(StrEnum):
    """Type de sanction sportive FFVB."""

    AVERTISSEMENT = "A"  # Carton jaune
    PENALITE = "P"  # Carton rouge = point adverse
    EXPULSION = "E"  # Exclusion du set
    DISQUALIFICATION = "D"  # Exclusion du match


class RoleReferee(StrEnum):
    """Rôle de l'arbitre sur une feuille de match."""

    PREMIER = "1er"
    SECOND = "2ème"
    MARQUEUR = "Marqueur"
    MARQUEUR_ASSISTANT = "Marqueur assistant"
    RESPONSABLE_SALLE = "Responsable de salle"
    JUGE_LIGNE = "Juge de ligne"


class RolePlayer(StrEnum):
    """Rôles officiels et tactiques d'un joueur de volleyball."""

    PASSEUR = "PASSEUR"
    POINTU = "POINTU"
    CENTRAL = "CENTRAL"
    RECEPTIONNEUR_ATTAQUANT = "RECEPTIONNEUR_ATTAQUANT"
    LIBERO = "LIBERO"
    POLYVALENT = "POLYVALENT"
    INDETERMINE = "INDETERMINE"


class RoleCoach(StrEnum):
    """Rôle de l'entraîneur sur une feuille de match."""

    ENTRAINEUR = "ENTRAINEUR"
    ASSISTANT = "ASSISTANT"


class Side(StrEnum):
    """Côté d'une équipe sur le terrain."""

    A = "A"
    B = "B"


class MatchStatus(StrEnum):
    """Statut d'un match de volleyball."""

    SCHEDULED = "SCHEDULED"
    PLAYED = "PLAYED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    FORFEIT = "FORFEIT"
    DOUBLE_FORFEIT = "DOUBLE_FORFEIT"
    UNKNOWN = "UNKNOWN"


class PlayFormat(StrEnum):
    """Format de jeu d'une compétition de volleyball."""

    SIX_VS_SIX = "6x6"
    FOUR_VS_FOUR = "4x4"
    THREE_VS_THREE = "3x3"
    TWO_VS_TWO = "2x2"


class PlayVariant(StrEnum):
    """Variante de jeu d'une compétition de volleyball."""

    STANDARD = "Standard"
    SOURD = "Sourd"
    ASSIS = "Assis"
    BEACH = "Beach"
