import re
from dataclasses import dataclass
from typing import Any, cast

from spyke.infrastructure.fdme.base import ParserCapabilities
from spyke.infrastructure.fdme.models import (
    ParsedFdme,
    ParsedMatch,
    ParsedOfficial,
    ParsedPlayer,
    ParsedSet,
    ParsedTeam,
)


class FfvbFdmeParseError(ValueError):
    """Raised when a FFVB sheet lacks a required robust field."""


@dataclass(frozen=True)
class FfvbTextParser:
    """Parse the normalized text markers emitted by FFVB FDME documents.

    PDF extraction is kept outside this class. This makes the parser deterministic
    and lets contract tests exercise the source mapping without filesystem I/O.
    """

    parser_type: str = "fdme-ffvb"
    parser_version: str = "1.0"
    capabilities: ParserCapabilities = ParserCapabilities(
        teams=True, players=True, coaches=True, officials=True, sets=True
    )

    def detect(self, text: str) -> bool:
        normalized = text.upper()
        return "FFVB" in normalized or ("EQUIPE A:" in normalized and "EQUIPE B:" in normalized)

    def parse(self, text: str) -> ParsedFdme:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        code = self._value(lines, r"^MATCH\s*:\s*(.+)$")
        team_a = self._team(lines, "A")
        team_b = self._team(lines, "B")
        sets = self._sets(lines)
        officials = tuple(self._officials(lines))
        match = ParsedMatch(code, team_a, team_b, sets, officials)
        return ParsedFdme(
            self.parser_type,
            self.parser_version,
            match,
            self.capabilities.as_set(),
        )

    def _team(self, lines: list[str], side: str) -> ParsedTeam:
        name = self._required_value(lines, rf"^EQUIPE\s+{side}\s*:\s*(.+)$", "team name")
        players = tuple(self._players(lines, side))
        coaches = tuple(self._coaches(lines, side))
        return ParsedTeam(name=name, players=players, coaches=coaches)

    def _players(self, lines: list[str], side: str) -> list[ParsedPlayer]:
        pattern = re.compile(rf"^JOUEUR\s+{side}\s*:\s*(?:(\d{{1,2}})\s+)?(.+)$", re.I)
        players: list[ParsedPlayer] = []
        for line in lines:
            match = pattern.match(line)
            if match is None:
                continue
            jersey = int(match.group(1)) if match.group(1) else None
            name = match.group(2).strip()
            captain = name.endswith("*")
            libero = name.endswith("[L]")
            name = name.removesuffix("*").removesuffix("[L]").strip()
            players.append(ParsedPlayer(name, jersey, captain=captain, libero=libero))
        return players

    def _coaches(self, lines: list[str], side: str) -> list[ParsedOfficial]:
        pattern = re.compile(rf"^ENTRAINEUR\s+{side}\s*:\s*(.+)$", re.I)
        return [
            ParsedOfficial(match.group(1).strip(), "coach")
            for line in lines
            if (match := pattern.match(line))
        ]

    @staticmethod
    def _officials(lines: list[str]) -> list[ParsedOfficial]:
        pattern = re.compile(r"^ARBITRE\s+(.+?)\s*:\s*(.+)$", re.I)
        return [
            ParsedOfficial(match.group(2).strip(), f"referee-{match.group(1).strip()}")
            for line in lines
            if (match := pattern.match(line))
        ]

    @staticmethod
    def _sets(lines: list[str]) -> tuple[ParsedSet, ...]:
        line = next((line for line in lines if re.match(r"^SETS?\s*:", line, re.I)), None)
        if line is None:
            raise FfvbFdmeParseError("Missing required sets line")
        raw_scores = re.sub(r"^SETS?\s*:\s*", "", line, flags=re.I)
        scores = re.findall(r"(\d{1,2})\s*[-/]\s*(\d{1,2})", raw_scores)
        if not scores:
            raise FfvbFdmeParseError("No valid set score found")
        return tuple(
            ParsedSet(index, int(score_a), int(score_b))
            for index, (score_a, score_b) in enumerate(scores, 1)
        )

    @staticmethod
    def _value(lines: list[str], pattern: str) -> str | None:
        compiled = re.compile(pattern, re.I)
        for line in lines:
            match = compiled.match(line)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def _required_value(cls, lines: list[str], pattern: str, field_name: str) -> str:
        value = cls._value(lines, pattern)
        if value is None:
            raise FfvbFdmeParseError(f"Missing required {field_name}")
        return value


class FfvbPdfParser:
    """Extract text from a PDF, then delegate all semantics to ``FfvbTextParser``."""

    def __init__(self, text_parser: FfvbTextParser | None = None) -> None:
        self.text_parser = text_parser or FfvbTextParser()

    def parse(self, content: bytes) -> ParsedFdme:
        try:
            import pymupdf
        except ImportError as error:
            raise RuntimeError("PyMuPDF is required to parse FFVB PDF documents") from error
        document = pymupdf.open(stream=content, filetype="pdf")
        try:
            page_texts: list[str] = [cast(str, cast(Any, page).get_text()) for page in document]
            text = "\n".join(page_texts)
        finally:
            document.close()
        return self.text_parser.parse(text)
