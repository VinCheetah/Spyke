# Spyke

Spyke is a volleyball data collection, analysis and exploration platform.

## Archive des sources

Les réponses brutes sont conservées dans `data/archive` par défaut. Le chemin
est organisé par source, saison, entité et type de document :

```text
data/archive/ffvb/2025-2026/LIIDF/calendars/<sha256>.csv
data/archive/ffvb/2025-2026/LIIDF/clubs/<sha256>.json
data/archive/fdme/2025-2026/LIIDF/matches/<sha256>.pdf
```

`RawArchive` stocke indifféremment les octets de documents PDF, CSV, HTML ou
JSON. Le hash SHA-256 rend l'écriture idempotente et `SourceArchiveService`
associe chaque fichier à ses métadonnées HTTP dans `source_document`.

