from collections.abc import Iterable

from spyke.infrastructure.fdme.base import FdmeParser
from spyke.infrastructure.fdme.models import ParsedFdme


class UnknownFdmeFormat(ValueError):
    """Raised when no registered parser recognizes a document."""


class FdmeRegistry:
    """Ordered parser registry; specific parsers should be registered first."""

    def __init__(self, parsers: Iterable[FdmeParser] = ()) -> None:
        self._parsers: list[FdmeParser] = list(parsers)

    def register(self, parser: FdmeParser) -> None:
        if any(existing.parser_type == parser.parser_type for existing in self._parsers):
            raise ValueError(f"Parser already registered: {parser.parser_type}")
        self._parsers.append(parser)

    def detect(self, text: str) -> FdmeParser:
        for parser in self._parsers:
            if parser.detect(text):
                return parser
        raise UnknownFdmeFormat("No FDME parser recognized the document")

    def parse(self, text: str) -> ParsedFdme:
        return self.detect(text).parse(text)
