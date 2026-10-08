from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.dto import ArbitreRecord


class FfvbExportError(ValueError):
    """Raised when an FFVB calendar export cannot be interpreted."""


@dataclass(frozen=True)
class ExportMatchRecord:
    """Canonical phase-one match data from ``vbspo_calendrier_export.php``."""

    entity_code: str
    season: str
    match_code: str
    pool_code: str
    round_number: str | None = None
    home_club_code: str | None = None
    home_team_name: str | None = None
    away_club_code: str | None = None
    away_team_name: str | None = None
    set_scores: tuple[tuple[int, int], ...] = ()
    sets_score: str | None = None
    match_date: date | None = None
    match_time: str | None = None
    venue: str | None = None
    referees: tuple[ArbitreRecord, ...] = ()
    line_judges: tuple[str, ...] = ()
    scorers: tuple[str, ...] = ()
    winner: str | None = None
    forfeit: bool = False
    source_url: str | None = None

    @property
    def match_datetime(self) -> datetime | None:
        if self.match_date is None or not self.match_time:
            return None
        try:
            return datetime.fromisoformat(f"{self.match_date.isoformat()}T{self.match_time}")
        except ValueError:
            return None

    @property
    def score(self) -> tuple[int, int] | None:
        if not self.set_scores:
            return None
        home = sum(home_score > away_score for home_score, away_score in self.set_scores)
        away = sum(away_score > home_score for home_score, away_score in self.set_scores)
        return home, away


class FfvbCalendarExportParser:
    """Parse FFVB's semicolon-separated Latin-1 calendar export.

    Headers are resolved by normalized names, while the verified positional
    layout remains a fallback for older exports whose headers are incomplete.
    """

    _columns = {
        "entite": 0,
        "jo": 1,
        "match": 2,
        "date": 3,
        "heure": 4,
        "eqa_no": 5,
        "eqa_nom": 6,
        "eqb_no": 7,
        "eqb_nom": 8,
        "set": 9,
        "score": 10,
        "salle": 12,
        "arb1_lic": 13,
        "arb1_nom": 14,
        "arb1_lr": 15,
        "arb1_cd": 16,
        "arb2_lic": 17,
        "arb2_nom": 18,
        "arb2_lr": 19,
        "arb2_cd": 20,
        "jdl1_nom": 22,
        "jdl2_nom": 24,
        "jdl3_nom": 26,
        "jdl4_nom": 28,
        "mrq1_nom": 30,
        "mrq2_nom": 32,
        "vainqueur": 37,
        "forfait": 38,
    }

    def parse(
        self,
        body: bytes,
        *,
        entity_code: str,
        season: str,
        source_url: str | None = None,
    ) -> list[ExportMatchRecord]:
        text = (
            body.decode("utf-8-sig") if body.startswith(b"\xef\xbb\xbf") else body.decode("latin-1")
        )
        reader = csv.reader(io.StringIO(text), delimiter=";")
        rows = list(reader)
        if not rows:
            return []
        header = self._header_indexes(rows[0])
        records: list[ExportMatchRecord] = []
        for row in rows[1:]:
            if not row or not any(cell.strip() for cell in row):
                continue
            record = self._parse_row(row, header, entity_code, season, source_url)
            if record is not None:
                records.append(record)
        return records

    def parse_from_client(
        self,
        client: FfvbClient,
        *,
        entity_code: str,
        season: str,
        pool_code: str | None = None,
    ) -> list[ExportMatchRecord]:
        document = client.fetch_calendar_export(
            entity_code=entity_code, season=season, pool_code=pool_code
        )
        return self.parse(
            document.body,
            entity_code=entity_code,
            season=season,
            source_url=document.url,
        )

    @classmethod
    def _header_indexes(cls, row: list[str]) -> dict[str, int]:
        indexes = {_normalize_header(value): index for index, value in enumerate(row)}
        resolved: dict[str, int] = {}
        for name, position in cls._columns.items():
            resolved[name] = indexes.get(_normalize_header(name), position)
        return resolved

    def _parse_row(
        self,
        row: list[str],
        indexes: dict[str, int],
        entity_code: str,
        season: str,
        source_url: str | None,
    ) -> ExportMatchRecord | None:
        def value(name: str) -> str:
            return _cell(row, indexes[name])

        match_code = value("match")
        if not match_code or _is_placeholder(value("eqa_nom"), value("eqb_nom")):
            return None
        return ExportMatchRecord(
            entity_code=entity_code,
            season=season,
            match_code=match_code,
            pool_code=_pool_code(match_code),
            round_number=value("jo"),
            home_club_code=value("eqa_no"),
            home_team_name=value("eqa_nom"),
            away_club_code=value("eqb_no"),
            away_team_name=value("eqb_nom"),
            set_scores=tuple(_parse_set_scores(value("score"))),
            sets_score=value("set"),
            match_date=_parse_date(value("date")),
            match_time=value("heure"),
            venue=value("salle"),
            referees=tuple(_parse_referees(row, indexes)),
            line_judges=tuple(
                value(name)
                for name in ("jdl1_nom", "jdl2_nom", "jdl3_nom", "jdl4_nom")
                if value(name)
            ),
            scorers=tuple(value(name) for name in ("mrq1_nom", "mrq2_nom") if value(name)),
            winner=value("vainqueur"),
            forfeit=value("forfait").upper() in {"P", "OUI", "FORFAIT", "1"},
            source_url=source_url,
        )


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", without_accents.lower()).strip("_")


def _cell(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    value = row[index].strip()
    return value


def _pool_code(match_code: str) -> str:
    match = re.match(r"^(.+?)(\d{3})$", match_code.strip())
    return match.group(1) if match else match_code[:3]


def _parse_set_scores(value: str | None) -> list[tuple[int, int]]:
    if not value:
        return []
    scores: list[tuple[int, int]] = []
    for part in value.split(","):
        match = re.fullmatch(r"\s*(\d{1,2})\s*[-/]\s*(\d{1,2})\s*", part)
        if match:
            scores.append((int(match.group(1)), int(match.group(2))))
    return scores


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, format).date()
        except ValueError:
            continue
    return None


def _parse_referees(row: list[str], indexes: dict[str, int]) -> list[ArbitreRecord]:
    referees: list[ArbitreRecord] = []
    for prefix in ("arb1", "arb2"):
        name = _cell(row, indexes[f"{prefix}_nom"])
        if name:
            referees.append(
                ArbitreRecord(
                    licence=_cell(row, indexes[f"{prefix}_lic"]),
                    name=name,
                    league=_cell(row, indexes[f"{prefix}_lr"]),
                    department=_cell(row, indexes[f"{prefix}_cd"]),
                )
            )
    return referees


def _is_placeholder(home: str | None, away: str | None) -> bool:
    placeholders = {"x", "xx", "xxx", "xxxx", "xxxxx", "exempt", "-", "."}
    return (home or "").strip().lower() in placeholders or (
        away or ""
    ).strip().lower() in placeholders
