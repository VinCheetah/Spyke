# Spyke — Architecture et plan directeur du projet

## 1. Objet du document

Ce document définit l’architecture de référence du projet Spyke, une plateforme complète de collecte, normalisation, stockage, analyse et exploration des données de volleyball issues principalement des sources FFVolley, avec prise en charge de plusieurs formats de feuilles de match électronique (FDME), dont FFVB et LNV.

L’objectif n’est pas seulement de construire un scraper, mais de disposer d’un système capable de :

- récupérer massivement des données depuis les sources fédérales ;
- conserver les documents et réponses brutes afin de pouvoir les retraiter ;
- parser des formats hétérogènes de FDME ;
- transformer ces données en modèle canonique cohérent ;
- résoudre les identités des personnes, clubs, équipes, licences, compétitions et lieux ;
- stocker l’ensemble dans une base relationnelle adaptée aux requêtes analytiques et géographiques ;
- calculer des statistiques au niveau du match, de la saison et de l’ensemble de la carrière ;
- exposer ces données par une API propre ;
- fournir une interface web riche pour explorer les données ;
- proposer une CLI complète pour les imports, le retraitement, les statistiques, la maintenance et le serveur ;
- mesurer précisément les performances et les goulots d’étranglement ;
- préserver la provenance et la version des données et des calculs.

Le principe architectural fondamental est :

> **Source → Archive brute → Parsing → Normalisation → Résolution d’entités → Données canoniques → Faits de match → Statistiques → API / Web / CLI**

---

# 2. Vision globale

Spyke est organisé comme un **monolithe modulaire**. Il ne s’agit pas au départ d’un ensemble de microservices indépendants.

Cette décision est importante : les différents domaines partagent énormément de données, notamment PostgreSQL, et les opérations doivent souvent être atomiques ou fortement coordonnées. Une architecture distribuée introduirait donc une complexité inutile au début.

Le projet peut néanmoins être exécuté sous plusieurs processus :

```text
                    ┌──────────────────────────────┐
                    │          Sources externes     │
                    │       FFVolley / LNV / etc.  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │        Acquisition            │
                    │ HTTP / téléchargement / PDF  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      Archive des sources      │
                    │ HTML / JSON / PDF / métadonnées│
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Parsing / détection FDME      │
                    │ FFVB / LNV / futurs formats   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Normalisation + validation    │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Résolution des entités        │
                    │ Personnes / clubs / équipes   │
                    │ licences / salles / etc.      │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      PostgreSQL + PostGIS     │
                    │  modèle canonique relationnel │
                    └──────────────┬───────────────┘
                                   │
                       ┌───────────┴───────────┐
                       │                       │
                       ▼                       ▼
            ┌─────────────────────┐  ┌─────────────────────┐
            │ Faits de match       │  │ Géolocalisation     │
            │ sets / rotations /   │  │ clubs / salles      │
            │ remplacements / etc. │  │                     │
            └──────────┬──────────┘  └─────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ Statistiques         │
            │ match / saison /     │
            │ carrière             │
            └──────────┬──────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      ┌───────────────┐   ┌───────────────┐
      │      API      │   │      CLI      │
      │    FastAPI    │   │     Typer     │
      └───────┬───────┘   └───────────────┘
              │
              ▼
      ┌─────────────────────┐
      │     Application Web │
      │ React / TypeScript   │
      └─────────────────────┘
```

---

# 3. Principes architecturaux

## 3.1. Séparation des responsabilités

Chaque composant doit avoir une responsabilité claire.

Un parser ne doit pas enregistrer directement une ligne SQL. Une route FastAPI ne doit pas parser un PDF. Une page web ne doit pas connaître le HTML FFVolley. Le système de statistiques ne doit pas dépendre d’une URL externe.

La chaîne principale est donc organisée ainsi :

```text
domain
   ↑
application
   ↑
infrastructure
```

Les interfaces utilisateur (`api`, `cli`, `web`) appellent la couche application et ne contiennent pas la logique métier profonde.

## 3.2. Données brutes, canoniques et dérivées

Il faut distinguer trois catégories :

### Données brutes

Ce que la source fournit réellement :

- HTML ;
- JSON ;
- PDF ;
- URL ;
- métadonnées HTTP ;
- date de récupération ;
- empreinte cryptographique.

### Données canoniques

Le modèle propre à Spyke :

- Club ;
- Team ;
- Person ;
- License ;
- Match ;
- Competition ;
- Venue ;
- etc.

### Données dérivées

Calculs effectués par Spyke :

- statistiques de match ;
- statistiques saisonnières ;
- statistiques carrière ;
- agrégats de club ;
- métriques avancées ;
- indicateurs géographiques.

Cette séparation rend possible le retraitement d’une source sans la retélécharger.

## 3.3. Idempotence

Un import doit pouvoir être exécuté plusieurs fois sans dupliquer les données.

Cela repose notamment sur :

- identifiants externes ;
- contraintes `UNIQUE` ;
- `UPSERT` ;
- hash des documents ;
- checkpoints d’import ;
- possibilité de reprise après échec.

## 3.4. Provenance

Chaque entité importante doit pouvoir être reliée à sa source d’origine.

Exemple :

```text
Club interne #3812
      ↓
ExternalIdentifier
      ↓
FFVB ID = 1234
      ↓
SourceDocument
      ↓
URL / date / hash / version du parser
```

Cette information est essentielle lorsqu’une donnée est contestée, corrigée ou retraitée.

## 3.5. Versionnement

Les parsers et les algorithmes statistiques doivent être versionnés.

Exemples :

```text
parser_version = "fdme-ffvb-2.1"
statistics_version = "2026.1"
```

Une modification de la logique de calcul ne doit pas mélanger silencieusement les anciennes et nouvelles statistiques.

---

# 4. Structure du dépôt

Structure de référence :

```text
spyke/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
│
├── src/
│   └── spyke/
│       ├── config/
│       │   ├── settings.py
│       │   ├── logging.py
│       │   └── constants.py
│       │
│       ├── domain/
│       │   ├── enums.py
│       │   ├── entities/
│       │   ├── value_objects/
│       │   ├── rules/
│       │   └── exceptions.py
│       │
│       ├── application/
│       │   ├── imports/
│       │   ├── statistics/
│       │   ├── geocoding/
│       │   ├── database/
│       │   └── maintenance/
│       │
│       ├── infrastructure/
│       │   ├── ffvb/
│       │   │   ├── client.py
│       │   │   ├── endpoints.py
│       │   │   ├── parsers/
│       │   │   ├── dto/
│       │   │   └── mappers/
│       │   │
│       │   ├── fdme/
│       │   │   ├── base.py
│       │   │   ├── registry.py
│       │   │   ├── detection.py
│       │   │   ├── ffvb.py
│       │   │   └── lnv.py
│       │   │
│       │   ├── geocoding/
│       │   ├── database/
│       │   │   ├── models/
│       │   │   ├── repositories/
│       │   │   ├── queries/
│       │   │   └── session.py
│       │   ├── storage/
│       │   └── observability/
│       │
│       ├── analytics/
│       │   ├── match/
│       │   ├── player/
│       │   ├── team/
│       │   ├── club/
│       │   ├── coach/
│       │   ├── referee/
│       │   ├── competition/
│       │   ├── league/
│       │   └── aggregation/
│       │
│       ├── api/
│       │   ├── app.py
│       │   ├── dependencies.py
│       │   ├── routes/
│       │   └── schemas/
│       │
│       ├── cli/
│       │   ├── app.py
│       │   ├── commands/
│       │   └── output.py
│       │
│       └── observability/
│           ├── timing.py
│           ├── metrics.py
│           ├── tracing.py
│           └── profiling.py
│
├── frontend/
├── migrations/
├── tests/
├── fixtures/
├── docs/
└── docker/
```

---

# 5. Module `config`

## Objectif

Centraliser la configuration globale :

- base de données ;
- chemins de stockage ;
- configuration HTTP ;
- Redis ;
- géocodeur ;
- concurrence ;
- logs ;
- paramètres de l’environnement.

## Liens directs

```text
config → tous les composants d’exécution
```

La configuration est consommée par l’infrastructure et les applications, mais ne doit pas contenir de logique métier.

## Limites

Le module ne doit pas devenir un fourre-tout contenant des règles métier ou des paramètres propres à une seule fonctionnalité.

---

# 6. Module `domain`

Le domaine contient le vocabulaire et les règles métier de Spyke indépendamment de la technique.

## 6.1. Entités

Principales entités :

```text
Season
Federation
League
Committee
Club
Team
Venue
Person
License
Competition
CompetitionPhase
CompetitionGroup
Match
MatchSet
```

## 6.2. Modèle important : Club ≠ Team

Un club peut posséder plusieurs équipes et une équipe est contextualisée par une saison.

```text
Club
  └── Team
        └── TeamSeason
```

Exemple : une équipe senior masculine peut évoluer de N3 à N2 sans que son identité de club change.

## 6.3. Person ≠ License

Une personne est une identité interne. Une licence est une identité sportive/source contextualisée.

```text
Person
  └── License
```

Une même personne peut être joueuse, entraîneuse ou officielle selon le contexte.

## 6.4. Match

Le match est le centre du modèle sportif :

```text
Match
├── competition
├── phase
├── group
├── season
├── venue
├── datetime
├── teams
└── fdme/source
```

## 6.5. Faits détaillés d’un match

Les données détaillées sont séparées afin d’éviter un modèle `Match` gigantesque :

```text
Match
├── MatchTeam
├── MatchSet
├── MatchPlayer
├── MatchCoach
├── MatchOfficial
├── Rotation
├── Substitution
├── Timeout
├── Sanction
└── ServiceRun
```

## Limites du domaine

Le domaine ne doit pas :

- effectuer de requêtes HTTP ;
- dépendre de SQLAlchemy ;
- parser un PDF ;
- construire une réponse FastAPI ;
- dessiner une carte.

Il doit pouvoir être testé isolément.

---

# 7. Module `infrastructure.ffvb`

## Objectif

Encapsuler tout ce qui est spécifique aux pages et endpoints de la FFVolley.

## Responsabilités

### `client.py`

Gestion :

- HTTP ;
- timeout ;
- retries ;
- sessions ;
- limitations de débit ;
- erreurs réseau ;
- cache brut éventuel.

### `endpoints.py`

Centralisation des points d’entrée externes connus.

### `parsers/`

Transformation de HTML/JSON externe en objets de données intermédiaires.

### `mappers/`

Transformation des données intermédiaires vers le modèle canonique/application.

## Liens directs

```text
FFVB client
    ↓
raw source archive
    ↓
FFVB parsers
    ↓
application import
```

## Limites

Cette couche doit rester spécifique aux sources externes. Elle ne doit pas décider du fonctionnement global de la base ou des statistiques.

Si FFVolley change son HTML, le projet doit idéalement modifier principalement cette couche et ses tests de non-régression.

---

# 8. Module `infrastructure.fdme`

## Objectif

Supporter plusieurs formats de feuilles de match électronique sans imposer leur structure au reste du projet.

## Architecture

```text
FdmeParser
   ├── FFVBParser
   ├── LNVParser
   └── FutureParser
```

Avec un registre :

```text
FdmeRegistry
```

et une détection :

```text
PDF
 ↓
Detection
 ↓
FFVB / LNV / Unknown
 ↓
Parser spécialisé
 ↓
ParsedFdme
```

## Contrat conceptuel

Chaque parser doit fournir :

```text
identifier/detect
parse
capabilities
version
```

## Modèle canonique

Tous les formats sont convertis vers une structure commune :

```text
ParsedFdme
├── match
├── teams
├── players
├── coaches
├── officials
├── sets
├── lineups
├── rotations
├── substitutions
├── timeouts
├── sanctions
└── service sequences
```

## Gestion des différences de formats

Un format peut fournir plus ou moins d’information. La capacité du parser doit donc être explicite.

Exemple :

```text
rotations = true
service_sequence = true
detailed_rally = false
```

## Limites

Il ne faut jamais forcer une donnée absente dans un format à une valeur inventée.

Une information indisponible est différente de :

- zéro ;
- faux ;
- vide ;
- valeur par défaut.

---

# 9. Archive des sources et stockage brut

## Objectif

Conserver les documents originaux afin d’éviter les téléchargements répétés et de permettre le retraitement.

## Principe

Chaque document reçoit une empreinte SHA-256.

```text
URL
 ↓
DOWNLOAD
 ↓
HASH
 ↓
Document déjà présent ?
 ├── oui → réutilisation
 └── non → archivage
```

## Métadonnées recommandées

```text
SourceDocument
├── source_system
├── url
├── content_hash
├── content_type
├── size
├── fetched_at
├── http_status
├── etag
├── last_modified
├── storage_key
├── parser_type
└── parser_version
```

## Limites

L’archive brute n’est pas la base applicative. Il ne faut pas tenter de faire fonctionner l’interface directement sur les PDF et HTML archivés.

---

# 10. Module `application.imports`

Cette couche orchestre les cas d’utilisation d’importation.

## Cas d’utilisation

```text
ImportLeagues
ImportClubs
ImportCompetitions
ImportCalendars
ImportFdme
ImportAll
```

## Structure d’un import

Chaque pipeline suit idéalement :

```text
Discover
→ Fetch
→ Archive
→ Detect
→ Parse
→ Normalize
→ Validate
→ Resolve
→ Persist
→ Derive
→ Aggregate
```

## Principes

### Idempotence

Relancer l’import ne crée pas de doublons.

### Reprise

Une exécution interrompue doit pouvoir reprendre au niveau pertinent.

### Isolation des erreurs

Une FDME invalide ne doit pas arrêter l’intégralité de l’import.

## Résultat d’un import

Exemple :

```text
Import #182
├── 10 000 documents vus
├── 9 942 réussis
├── 37 warnings
├── 21 échecs
└── statut = PARTIAL_SUCCESS
```

---

# 11. Résolution d’entités

## Objectif

Relier une représentation externe à une entité canonique.

Exemple :

```text
"AS VILLEURBANNAISE"
"AS. VILLEURBANNAISE"
"AS VILLEURBANNAISE VB"
```

doivent éventuellement converger vers le même club.

## Ordre de résolution recommandé

```text
1. identifiant externe exact
2. correspondance historique connue
3. identifiants secondaires
4. nom normalisé + contexte
5. ville / département / comité
6. correspondance candidate
7. intervention manuelle si nécessaire
```

## Important

Le nom seul ne doit pas être considéré comme une clé fiable.

## Limites

La résolution automatique doit accepter l’incertitude.

Le système doit pouvoir produire :

```text
MATCH
PROBABLE
AMBIGUOUS
UNRESOLVED
```

plutôt que de créer silencieusement une mauvaise identité.

---

# 12. Base de données

## Choix

```text
PostgreSQL
+
PostGIS
```

avec :

```text
SQLAlchemy
Alembic
```

## Pourquoi

Le projet possède :

- beaucoup de relations ;
- des contraintes d’intégrité ;
- des historiques ;
- des requêtes analytiques ;
- des jointures ;
- des agrégations ;
- des besoins géographiques.

## Principaux groupes de tables

### Référentiel

```text
season
federation
league
committee
```

### Organisations

```text
club
team
venue
```

### Participants

```text
person
license
person_license
```

### Compétitions

```text
competition
competition_phase
competition_group
```

### Matches

```text
match
match_team
match_set
match_player
match_coach
match_official
rotation
substitution
timeout
sanction
service_run
```

### Provenance

```text
source_document
external_identifier
```

### Imports

```text
import_run
import_step
import_error
```

### Statistiques

```text
statistic_definition
player_match_stats
team_match_stats
coach_match_stats
official_match_stats
player_season_stats
team_season_stats
club_season_stats
coach_season_stats
official_season_stats
league_season_stats
competition_season_stats
```

### Géocodage

```text
geocoding_request
geocoding_candidate
```

## Limites

Il faut éviter le modèle EAV générique de type :

```text
entity_id / stat_name / value
```

pour toutes les statistiques. Il serait très flexible, mais pénaliserait l’intégrité, la lisibilité et les performances.

---

# 13. Géolocalisation

## Objectif

Obtenir des coordonnées cohérentes pour les clubs et salles.

## Modèle

```text
Venue / Club
├── address
├── postal_code
├── city
├── latitude
├── longitude
├── geometry
├── geocoder
├── geocoder_query
├── geocoder_score
├── geocoder_confidence
└── geocoder_verified
```

## Stratégie

Le géocodage ne doit pas être une simple conversion :

```text
adresse → coordonnées
```

Il doit exploiter le contexte :

- commune ;
- code postal ;
- département ;
- comité ;
- éventuelles coordonnées déjà connues.

Le service de résolution doit comparer plusieurs candidats et conserver le score et la justification du choix.

## Cas manuels

Un mécanisme de correction manuelle doit exister pour les salles problématiques.

## Limites

Aucun géocodeur ne garantit des coordonnées parfaites dans tous les cas. La qualité doit donc être mesurable et vérifiable plutôt que supposée.

---

# 14. Faits de match et modèle événementiel

## Objectif

Conserver assez d’information pour reconstruire les statistiques.

Il faut privilégier les données structurantes et les événements plutôt que de n’enregistrer que des statistiques déjà calculées.

Exemple :

```text
MatchSet
  ↓
Rotation
  ↓
ServiceRun
  ↓
Substitution / Timeout / Sanction
```

Cela permet d’étudier :

- la position des joueurs ;
- la présence sur le terrain ;
- les rotations ;
- les séries au service ;
- les remplacements ;
- les temps morts ;
- les sanctions.

## Limites

Il faut distinguer ce qui est réellement reconstructible à partir d’une FDME de ce qui ne l’est pas. La granularité « rallye par rallye » ne doit être ajoutée que lorsque les sources la permettent de manière fiable.

---

# 15. Système de statistiques

## Philosophie

Les statistiques sont des **données dérivées**, pas des faits sources.

Chaîne :

```text
FDME / faits canoniques
        ↓
calcul match
        ↓
agrégation saison
        ↓
agrégation carrière / multi-saisons
```

## Niveau match

Exemples :

- présence ;
- sets joués ;
- position ;
- séries de service ;
- durée de présence ;
- issue du match ;
- nombre de sets gagnés/perdus selon le niveau d’information disponible.

## Niveau saison

Exemples :

- nombre de matchs ;
- ratio victoire/défaite ;
- fréquence de présence ;
- moyenne par match ;
- répartition par compétition ;
- performances par équipe.

## Niveau carrière / global

Même logique, agrégée sur plusieurs saisons.

## Registre des statistiques

Chaque métrique possède une définition :

```text
StatisticDefinition
├── code
├── name
├── description
├── entity_type
├── scope
├── unit
├── aggregation
└── version
```

Exemple :

```text
SERVE_RUN_WINS
entity = PLAYER
scope = MATCH
aggregation = SUM
```

## Limites

Une statistique doit toujours être accompagnée de son périmètre et de sa définition. Il faut éviter les indicateurs dont la définition varie implicitement selon la source.

---

# 16. Analyse et agrégation

Le dossier `analytics/` contient les algorithmes de calcul, indépendamment des endpoints web.

Structure :

```text
analytics/
├── match/
├── player/
├── team/
├── club/
├── coach/
├── referee/
├── competition/
├── league/
└── aggregation/
```

## Exemple de flux

```text
player_match_stats
      ↓
player_season_stats
      ↓
player_career_stats
```

Le calcul peut être entièrement rejoué à partir des faits canoniques.

---

# 17. Système de qualité des données

## Objectif

Détecter les incohérences plutôt que de les laisser contaminer la base.

Exemples :

```text
score global = 3-0
mais 4 sets trouvés
→ ERROR
```

```text
joueur présent sur FDME
mais absence dans la licence saison
→ WARNING
```

## Tables

```text
DataQualityIssue
```

avec notamment :

```text
severity
entity_type
entity_id
message
source_document
import_run
```

## Limites

Les règles de qualité ne doivent pas être utilisées pour « corriger » silencieusement les données sources. Elles doivent signaler l’anomalie, et éventuellement déclencher une règle de normalisation explicitement définie.

---

# 18. API

## Choix

```text
FastAPI
+
Pydantic
```

## Responsabilité

L’API expose des objets et opérations applicatifs stables, sans exposer directement le schéma SQL.

Exemples :

```text
GET /api/v1/players/{id}
GET /api/v1/players/{id}/stats
GET /api/v1/clubs/{id}
GET /api/v1/matches/{id}
GET /api/v1/competitions/{id}
GET /api/v1/statistics/...
```

## Pagination et filtres

Les endpoints de listes doivent gérer explicitement :

- pagination ;
- tri ;
- filtres ;
- saison ;
- compétition ;
- club ;
- niveau ;
- sexe ;
- localisation lorsque pertinent.

## Limites

Les routes ne doivent pas contenir de logique métier complexe. Une route orchestre la validation, les autorisations éventuelles et l’appel au cas d’utilisation approprié.

---

# 19. Interface Web

## Choix

```text
React
TypeScript
Vite
TanStack Query
ECharts
MapLibre
```

## Pages principales

### Accueil

- recherche globale ;
- statistiques générales ;
- saisons disponibles ;
- activité récente des données.

### Joueur

- identité ;
- licences ;
- clubs ;
- équipes ;
- historique ;
- matchs ;
- statistiques.

### Club

- identité ;
- localisation ;
- équipes ;
- historique ;
- joueurs ;
- entraîneurs ;
- compétitions ;
- statistiques.

### Match

- score ;
- équipes ;
- composition ;
- compétition ;
- salle ;
- arbitres ;
- détail par set ;
- rotations ;
- remplacements ;
- temps morts ;
- sanctions ;
- statistiques ;
- FDME source.

### Exploration

- joueurs ;
- clubs ;
- équipes ;
- compétitions ;
- ligues ;
- comités ;
- salles ;
- matchs.

### Carte

- clubs ;
- salles ;
- filtres géographiques ;
- saison ;
- niveau ;
- sexe ;
- compétition.

## Limites

Le frontend ne doit jamais dépendre de la structure interne de PostgreSQL ou de la logique des scrapers.

---

# 20. CLI

Le CLI est une interface d’administration et d’exploitation.

```text
spyke db
    init
    migrate
    downgrade
    backup
    restore
    check

spyke import
    leagues
    clubs
    competitions
    calendars
    fdme
    all

spyke parse
    fdme

spyke stats
    match
    season
    career
    all

spyke geocode
    clubs
    venues
    all

spyke data
    validate
    duplicates
    quality

spyke cache
    inspect
    clean
    stats

spyke benchmark
    import
    parsing
    database
    statistics

spyke server
    start
```

Options transverses :

```text
--season
--competition
--from
--to
--limit
--concurrency
--force
--dry-run
--resume
--retry-failed
```

## Limites

Le CLI doit déclencher les mêmes cas d’utilisation que l’API ou les workers. Il ne faut pas dupliquer l’algorithme d’importation dans les commandes CLI.

---

# 21. Cache et réutilisation des données

Il faut distinguer trois mécanismes.

## 21.1. Archive brute

Conserve les HTML, JSON et PDF de manière durable.

## 21.2. Cache applicatif

Peut être utilisé pour accélérer les requêtes fréquemment répétées.

Exemple : Redis.

## 21.3. Données dérivées persistantes

Les statistiques saisonnières ou autres agrégats stockés en base ne doivent pas être confondus avec un cache.

## Limites

Un cache ne doit jamais devenir la seule copie d’une donnée nécessaire au fonctionnement du système.

---

# 22. Chronométrage, logs et observabilité

## Objectif

Mesurer le pipeline avant d’optimiser.

Exemple de rapport :

```text
Import 2025/2026

Download                 18.3 min
Parse FDME                7.1 min
Normalization             2.4 min
Entity resolution        11.8 min
Database writes            9.2 min
Statistics                 4.7 min
Geocoding                  3.8 min
---------------------------------
Total                     57.3 min
```

## Architecture

```text
observability/
├── timing.py
├── metrics.py
├── tracing.py
└── profiling.py
```

## Niveau de mesure

Les grandes étapes doivent être mesurées :

```text
IMPORT
 ├── DOWNLOAD
 ├── PARSE
 ├── NORMALIZE
 ├── DATABASE
 ├── STATISTICS
 └── GEOCODING
```

Puis du profiling plus précis est activé uniquement lorsqu’un goulot a été identifié.

## Limites

L’instrumentation ne doit pas elle-même devenir un coût significatif dans les imports massifs.

---

# 23. Tests

Le projet doit posséder plusieurs niveaux de tests.

## Unit tests

Pour :

- parsers ;
- normalisation ;
- règles métier ;
- statistiques ;
- score de géocodage.

## Integration tests

Pour :

- PostgreSQL ;
- PostGIS ;
- SQLAlchemy ;
- imports complets.

## Contract tests

Particulièrement importants pour les sources externes.

Exemple :

```text
fixtures/ffvb/club_001.html
fixtures/fdme/ffvb/fdme_001.pdf
fixtures/fdme/lnv/fdme_001.pdf
```

Les sorties attendues doivent être connues et vérifiées.

## End-to-end tests

Pour :

```text
source fixture
→ import
→ base
→ API
→ frontend
```

## Limites

Une couverture élevée ne remplace pas des fixtures représentatives. Pour les parsers, la diversité des documents est particulièrement importante.

---

# 24. CI et qualité du code

Une pipeline CI doit exécuter au minimum :

```text
format
lint
type-check
unit tests
integration tests
migration checks
```

Il faut également traiter les fixtures des parsers comme des données de non-régression.

---

# 25. Dépendances technologiques de référence

| Domaine | Choix |
|---|---|
| Langage | Python |
| Gestion projet | uv + pyproject.toml |
| Base | PostgreSQL |
| Géospatial | PostGIS |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| HTTP | HTTPX |
| HTML | selectolax / lxml |
| PDF | PyMuPDF |
| Validation | Pydantic |
| API | FastAPI |
| CLI | Typer |
| Cache | Redis |
| Stockage brut | filesystem puis objet type S3/MinIO si nécessaire |
| Géocodage France | Géoplateforme / BAN |
| Frontend | React + TypeScript |
| Graphiques | ECharts |
| Cartographie | MapLibre |
| Tests | pytest |
| Observabilité | OpenTelemetry |
| Logs | structlog |
| Conteneurisation | Docker Compose |
| CI | GitHub Actions |

Ces choix sont volontairement classiques et remplaçables. L’architecture ne doit pas dépendre du fournisseur d’une technologie précise lorsqu’un contrat abstrait suffit.

---

# 26. Ordre précis de construction

L’ordre de construction est essentiel. Le projet ne doit pas être développé « par écran » ni « par scraper » indépendamment du modèle de données.

## Étape 0 — cadrage et invariants

Définir :

- vocabulaire métier ;
- saisons ;
- genres ;
- niveaux de compétition ;
- types de compétition ;
- statuts de match ;
- rôles joueur/entraîneur/officiel ;
- types de FDME ;
- règles d’identification.

**Livrable :** dictionnaire métier + premières énumérations + conventions.

---

## Étape 1 — squelette du dépôt

Créer :

```text
src/spyke
pyproject.toml
README.md
tests/
docs/
```

Configurer :

- uv ;
- lint ;
- format ;
- type checking ;
- pytest ;
- CI minimale.

**Livrable :** projet installable et tests exécutables.

---

## Étape 2 — domaine et constantes

Construire les premières entités et énumérations :

```text
Season
Gender
CompetitionLevel
CompetitionType
MatchStatus
PersonRole
FdmeType
```

Puis :

```text
Club
Team
Person
License
Venue
Competition
Match
```

Ne pas implémenter encore les scrapers.

**Livrable :** modèle métier testable sans base.

---

## Étape 3 — PostgreSQL + migrations

Mettre en place :

- PostgreSQL ;
- PostGIS ;
- SQLAlchemy ;
- Alembic ;
- migrations initiales ;
- contraintes et index essentiels.

**Livrable :** base pouvant être créée depuis zéro par une commande.

---

## Étape 4 — provenance et archive brute

Créer :

```text
SourceDocument
ExternalIdentifier
ImportRun
ImportStep
ImportError
```

Implémenter :

- téléchargement ;
- hash ;
- stockage ;
- métadonnées ;
- déduplication.

**Livrable :** un document externe peut être récupéré et retrouvé sans reparcours Internet.

---

## Étape 5 — client FFVolley minimal

Construire le client HTTP avec :

- session ;
- timeout ;
- retries ;
- gestion des erreurs ;
- logs ;
- limitation de débit si nécessaire.

Ajouter un premier endpoint réel.

**Livrable :** acquisition fiable d’une page FFVolley.

---

## Étape 6 — import des référentiels simples

Commencer par :

```text
leagues
clubs
competitions
```

Puis :

```text
calendar / matches
```

À chaque étape :

```text
source
→ parse
→ normalize
→ validate
→ persist
```

**Livrable :** première base canonique avec référentiels et matchs.

---

## Étape 7 — résolution d’identités

Introduire :

- external IDs ;
- normalisation des noms ;
- correspondances historiques ;
- états d’ambiguïté ;
- outils de contrôle.

**Livrable :** deux imports successifs ne produisent pas deux clubs identiques.

---

## Étape 8 — modèle FDME abstrait

Définir :

```text
FdmeParser
FdmeRegistry
ParserCapabilities
ParsedFdme
```

Sans encore couvrir tous les détails.

**Livrable :** un contrat stable pour les futurs parsers.

---

## Étape 9 — parser FFVB FDME

Construire d’abord un parser couvrant les informations les plus robustes :

- équipes ;
- joueurs ;
- entraîneurs ;
- officiels ;
- résultat ;
- sets.

Ensuite ajouter progressivement :

- rotations ;
- remplacements ;
- temps morts ;
- sanctions ;
- service sequence.

Créer une fixture par cas important.

**Livrable :** parsing reproductible et testé des FDME FFVB ciblées.

---

## Étape 10 — parser LNV

Ajouter le parser LNV uniquement après stabilisation du modèle canonique FFVB.

Le parser LNV remplit le même contrat :

```text
ParsedFdme
```

mais avec des capacités différentes si nécessaire.

**Livrable :** plusieurs formats externes convergent vers un seul modèle métier.

---

## Étape 11 — intégration complète Match

Relier la FDME à :

- match ;
- équipes ;
- personnes ;
- licences ;
- compétition ;
- saison ;
- salle.

Créer les données de faits :

```text
MatchSet
Rotation
Substitution
Timeout
Sanction
ServiceRun
```

**Livrable :** un match de la base peut être inspecté à son niveau de détail maximal disponible.

---

## Étape 12 — qualité des données

Créer les contrôles :

- cohérence scores ;
- nombre de sets ;
- présence des joueurs ;
- licences ;
- dates ;
- compétition ;
- affiliations ;
- cohérences entre sources.

**Livrable :** les imports produisent des rapports d’anomalies exploitables.

---

## Étape 13 — statistiques de match

Commencer par produire des statistiques sur un seul match.

Puis vérifier manuellement plusieurs cas connus.

**Livrable :** `player_match_stats`, `team_match_stats`, etc.

---

## Étape 14 — agrégations saisonnières

Construire :

```text
player_season_stats
team_season_stats
club_season_stats
coach_season_stats
official_season_stats
competition_season_stats
league_season_stats
```

Ajouter les versions de calcul.

**Livrable :** une saison complète peut être recalculée à partir des faits.

---

## Étape 15 — agrégations multi-saisons

Construire les vues/statistiques carrière ou globales.

**Livrable :** analyse longitudinale sur plusieurs saisons.

---

## Étape 16 — géolocalisation

Ajouter :

- géocodeur ;
- score de correspondance ;
- candidats ;
- validation ;
- corrections manuelles ;
- stockage PostGIS.

Commencer par les salles, puis les clubs si nécessaire.

**Livrable :** chaque localisation utilisable sur une carte dispose d’un niveau de confiance.

---

## Étape 17 — API

Exposer les premiers domaines :

```text
players
clubs
teams
matches
competitions
seasons
statistics
venues
```

Ajouter :

- pagination ;
- filtres ;
- tri ;
- OpenAPI ;
- erreurs structurées.

**Livrable :** toute la donnée importante est accessible sans accès direct à la base.

---

## Étape 18 — CLI complète

Construire les commandes d’administration autour des use cases existants.

**Livrable :** tout le pipeline peut être exécuté sans interface web.

---

## Étape 19 — frontend

Commencer par :

```text
layout global
recherche
saisons
clubs
joueurs
matchs
```

Puis ajouter :

```text
statistiques
cartes
exploration avancée
```

**Livrable :** exploration interactive des données.

---

## Étape 20 — observabilité avancée

Instrumenter :

- imports ;
- parsers ;
- base ;
- géocodage ;
- statistiques ;
- API.

Ajouter profiling ciblé.

**Livrable :** temps par étape, débit, p50/p95/p99, erreurs et goulots.

---

## Étape 21 — cache applicatif et optimisation

Seulement après mesure réelle.

Actions possibles :

- index SQL ;
- batch inserts ;
- `COPY` PostgreSQL pour certains flux ;
- cache Redis ;
- parallélisation contrôlée ;
- pré-calculs ;
- vues matérialisées ;
- requêtes spécialisées.

**Livrable :** optimisation basée sur des mesures et non sur des suppositions.

---

## Étape 22 — industrialisation

Ajouter si nécessaire :

- workers ;
- scheduler ;
- stockage objet ;
- déploiement distant ;
- monitoring ;
- sauvegardes automatiques ;
- restauration testée.

Ces éléments doivent être introduits uniquement lorsque le volume ou les besoins les justifient.

---

# 27. Ordre des dépendances fonctionnelles

Le projet doit respecter au minimum cette hiérarchie :

```text
1. conventions métier
        ↓
2. domaine
        ↓
3. base + migrations
        ↓
4. archive / provenance
        ↓
5. acquisition
        ↓
6. parsers référentiels
        ↓
7. résolution d'entités
        ↓
8. FDME
        ↓
9. faits de match
        ↓
10. qualité
        ↓
11. statistiques
        ↓
12. géographie
        ↓
13. API
        ↓
14. CLI complète
        ↓
15. Web
        ↓
16. optimisation / industrialisation
```

Il est déconseillé d’inverser radicalement cet ordre.

En particulier :

```text
Frontend avant modèle de données = mauvais ordre
Statistiques avant faits de match = mauvais ordre
FDME avant modèle canonique = mauvais ordre
Optimisation avant instrumentation = mauvais ordre
Microservices avant validation du monolithe = mauvais ordre
```

---

# 28. Limites structurelles du projet

Même avec une bonne architecture, certaines difficultés resteront intrinsèquement difficiles.

## Sources externes instables

Le HTML, les endpoints ou les PDF peuvent évoluer.

Réponse architecturale : isolation + fixtures + versionnement.

## Identités ambiguës

Deux personnes ou clubs peuvent partager des noms similaires.

Réponse : external IDs + contexte + niveaux de confiance + intervention humaine.

## Données historiques incomplètes

Les anciennes saisons peuvent contenir moins d’information.

Réponse : modèle nullable mais explicite + capacité des sources.

## Statistiques dépendantes des informations disponibles

Une statistique ne doit être calculée que si les données nécessaires existent réellement.

## Coût des imports massifs

Le téléchargement n’est pas forcément le seul goulot. Parsing, résolution d’entités, géocodage et écritures SQL peuvent devenir dominants.

Réponse : instrumentation par étape + profiling.

## Croissance du volume

Des centaines de milliers de feuilles de match peuvent nécessiter un stockage et des imports plus industrialisés.

Réponse : architecture monolithique modulaire d’abord, workers et stockage objet ensuite si nécessaire.

---

# 29. Règles de conception à conserver pendant toute la vie du projet

1. Une source externe n’est jamais le modèle métier.
2. Un parser ne connaît pas la base.
3. L’API ne connaît pas les détails de parsing.
4. Le frontend ne connaît pas SQLAlchemy.
5. Les statistiques sont dérivées des faits canoniques.
6. Les données brutes sont conservées.
7. Les imports sont idempotents.
8. Les identités ont des identifiants externes et une provenance.
9. Les anomalies sont signalées explicitement.
10. Les calculs statistiques sont versionnés.
11. Le modèle `Club` reste distinct du modèle `Team`.
12. `Person` reste distinct de `License`.
13. Les événements sont conservés lorsqu’ils permettent de recalculer les indicateurs.
14. Les limites d’une source doivent être représentées, pas masquées.
15. Le profiling vient avant l’optimisation.
16. Le système de fichiers de code ne doit pas refléter seulement les technologies, mais surtout les responsabilités métier.
17. Une nouvelle source ou un nouveau format doit pouvoir être ajouté sans réécrire l’application.

---

# 30. Définition de « projet terminé »

Le projet peut être considéré comme architecturalement mature lorsque les conditions suivantes sont réunies :

```text
✓ imports FFVolley reproductibles
✓ archive brute persistante
✓ parsing FFVB et LNV
✓ modèle canonique cohérent
✓ résolution d'entités contrôlée
✓ données de match détaillées
✓ qualité et provenance
✓ statistiques match / saison / carrière
✓ géolocalisation fiable et contrôlable
✓ PostgreSQL + PostGIS
✓ API documentée
✓ CLI complète
✓ interface web
✓ tests de non-régression
✓ métriques de performance
✓ possibilité de recalcul complet
✓ sauvegarde / restauration
✓ possibilité d'ajouter de nouvelles sources
```

Le critère le plus important n’est pas seulement que tout fonctionne, mais que les données puissent être **reconstruites, vérifiées, recalculées et étendues**.

---

# 31. Résumé architectural final

Spyke doit être conçu comme une **plateforme de données sportives versionnée et traçable**.

Le cœur de l’architecture est :

```text
             EXTERNAL SOURCES
                    │
                    ▼
             SOURCE ADAPTERS
                    │
                    ▼
              RAW ARCHIVE
                    │
                    ▼
                PARSERS
                    │
                    ▼
              NORMALIZATION
                    │
                    ▼
           ENTITY RESOLUTION
                    │
                    ▼
          CANONICAL DOMAIN DATA
                    │
                    ▼
              MATCH FACTS
                    │
                    ▼
             STATISTICS
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
         API       CLI       ANALYTICS
          │
          ▼
         WEB
```

Cette structure permet de faire évoluer indépendamment :

- les sources FFVolley ;
- les formats de FDME ;
- le schéma relationnel ;
- les algorithmes statistiques ;
- le géocodage ;
- l’API ;
- l’interface web ;
- les mécanismes de calcul parallèle.

Elle donne également une propriété essentielle à Spyke : **la capacité de revenir à la source et de reconstruire les résultats**, ce qui est particulièrement important pour un projet dont les données, les parsers et les définitions statistiques évolueront au fil du temps.

---

# 32. Prochaine spécification à figer

Avant l’implémentation massive des scrapers, la spécification la plus importante à produire est le **modèle relationnel détaillé** :

- diagramme des entités ;
- cardinalités ;
- clés primaires et externes ;
- contraintes uniques ;
- historique des affiliations ;
- modèle exact des matchs et sets ;
- granularité de chaque événement ;
- définition précise de chaque statistique ;
- stratégies d’indexation ;
- provenance et versionnement.

Ce modèle constitue le contrat central entre acquisition, parsing, base, analytics, API et frontend.
