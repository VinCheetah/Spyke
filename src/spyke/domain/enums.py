"""
Énumérations métier pour PyVolley.
"""

from enum import Enum


class Gender(str, Enum):
    """Genre de la compétition ou de l'équipe."""
    MASCULIN = "MASCULIN"
    FEMININ = "FEMININ"
    MIXTE = "MIXTE"


class Category(str, Enum):
    """Catégorie d'âge FFVB."""
    SENIOR = "SENIOR"
    M21 = "M21"
    M20 = "M20"
    M18 = "M18"
    M15 = "M15"
    M13 = "M13"
    M11 = "M11"
    M9 = "M9"
    JEUNES = "JEUNES"
    VETERAN = "VETERAN"


class Division(str, Enum):
    """Niveau d'échelon de compétition."""
    PRO_A = "PRO A"
    PRO_B = "PRO B"
    ELITE = "ELITE"
    ELITE_AVENIR = "ELITE AVENIR"
    NATIONALE_2 = "NATIONALE 2"
    NATIONALE_3 = "NATIONALE 3"
    COUPE_DE_FRANCE = "COUPE DE FRANCE"
    COUPE_DE_FRANCE_BEACH = "COUPE DE FRANCE BEACH"
    COUPE_DE_FRANCE_ASSIS = "COUPE DE FRANCE ASSIS"
    COUPE_DE_FRANCE_SOURD = "COUPE DE FRANCE SOURD"
    COUPE_DE_FRANCE_JEUNES = "COUPE DE FRANCE JEUNES"
    PRE_NATIONALE = "PRE_NATIONALE"
    REGIONALE_1 = "REGIONALE 1"
    REGIONALE = "REGIONALE"
    REGIONALE_2 = "REGIONALE 2"
    PRE_REGIONALE = "PRE_REGIONALE"
    DEPARTEMENTALE_1 = "DEPARTEMENTALE 1"
    DEPARTEMENTALE = "DEPARTEMENTALE"
    DEPARTEMENTALE_2 = "DEPARTEMENTALE 2"
    DEPARTEMENTALE_3 = "DEPARTEMENTALE 3"
    LOISIR = "LOISIR"
    
    
class Echelon(str, Enum):
    INTERNATIONAL = "INTERNATIONAL"
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    DEPARTEMENTAL = "DEPARTEMENTAL"


class TypeSanction(str, Enum):
    """Type de sanction sportive FFVB."""
    AVERTISSEMENT = "A"  # Carton jaune
    PENALITE = "P"       # Carton rouge = point adverse
    EXPULSION = "E"      # Exclusion du set
    DISQUALIFICATION = "D"  # Exclusion du match


class RoleReferee(str, Enum):
    """Rôle de l'arbitre sur une feuille de match."""
    PREMIER = "1er"
    SECOND = "2ème"
    MARQUEUR = "Marqueur"
    MARQUEUR_ASSISTANT = "Marqueur assistant"
    RESPONSABLE_SALLE = "Responsable de salle"
    JUGE_LIGNE = "Juge de ligne"
    
    
class RolePlayer(str, Enum):
    """Rôles officiels et tactiques d'un joueur de volleyball."""
    PASSEUR = "PASSEUR"
    POINTU = "POINTU"
    CENTRAL = "CENTRAL"
    RECEPTIONNEUR_ATTAQUANT = "RECEPTIONNEUR_ATTAQUANT"
    LIBERO = "LIBERO"
    POLYVALENT = "POLYVALENT"
    INDETERMINE = "INDETERMINE"
    

class RoleCoach(str, Enum):
    """Rôle de l'entraîneur sur une feuille de match."""
    ENTRAINEUR = "ENTRAINEUR"
    ASSISTANT = "ASSISTANT"


class Side(str, Enum):
    """Côté d'une équipe sur le terrain."""
    A = "A"
    B = "B"
    
    
class MatchStatus(str, Enum):
    """Statut d'un match de volleyball."""
    SCHEDULED = "SCHEDULED"
    PLAYED = "PLAYED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    FORFEIT = "FORFEIT"
    DOUBLE_FORFEIT = "DOUBLE_FORFEIT"
    UNKNOWN = "UNKNOWN"