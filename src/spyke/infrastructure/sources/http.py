import logging
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Self

import httpx
from bs4 import BeautifulSoup

from spyke.domain.entities import Entity, Season
from spyke.domain.enums import RawDataCategory

from charset_normalizer import from_bytes
logger = logging.getLogger(__name__)

ParameterValue = str | Entity | Season
ParameterMapping = Mapping[str, ParameterValue]


class SourceHttpError(RuntimeError):
    """Raised when a source cannot be fetched successfully."""


@dataclass(frozen=True)
class HttpDocument:
    """The immutable result of a source request."""

    url: str
    body: bytes
    status_code: int
    content_type: str | None
    etag: str | None
    params: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    last_modified: str | None = None
    
    @classmethod
    def build_storage_key(cls, category: RawDataCategory, params: ParameterMapping) -> str:
        category_paths: dict[RawDataCategory, tuple[str, list[str]]] = {
            RawDataCategory.FDME: ("fdme", ["season", "entity", "competition", "code"]),
            RawDataCategory.CALENDAR: ("calendar", ["season", "entity"]),
            RawDataCategory.CLUBS: ("clubs", ["entity"]),
            RawDataCategory.ENTITIES: ("entities", []),
            RawDataCategory.ENTITY: ("entities", ["entity_type", "entity_code"]),
        }
        try:
            base, components = category_paths[category]
        except KeyError as error:
            raise ValueError(f"Unsupported category: {category}") from error

        return f"{base}/" + "/".join(
            cls._safe_component(str(value)) for value in cls._get_params(components, params)
        )
        
    def storage_key(self, category: RawDataCategory) -> str:
        """Return a unique storage key for this document based on its category and parameters."""
        return self.build_storage_key(category, self.params)
        
    @classmethod
    def _get_params(cls, names: Sequence[str], params: ParameterMapping) -> list[ParameterValue]:
        if missing := [name for name in names if name not in params]:
            raise ValueError(f"Missing required parameters: {missing}")
        return [params[name] for name in names]

    def get_params(self, names: Sequence[str]) -> list[ParameterValue]:
        return self._get_params(names, self.params)

    @staticmethod
    def _safe_component(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
        if not normalized or normalized in {".", ".."}:
            raise ValueError("archive path components must contain a visible name")
        return normalized.strip(".-") or "unnamed"

    @staticmethod
    def _safe_suffix(suffix: str) -> str:
        normalized = suffix.lstrip(".").lower()
        if not re.fullmatch(r"[a-z0-9]+", normalized):
            raise ValueError("archive suffix must contain only letters and digits")
        return normalized


class SourceHttpClient:
    """Small HTTP client with timeouts, redirects, and bounded retries."""

    _TRANSIENT_STATUS_CODES = frozenset({408, 429})

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retries: int = 3,
        backoff_seconds: float = 0.5,
        user_agent: str = "Spyke/0.1 (+https://github.com/spyke-project)",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if retries < 0:
            raise ValueError("retries must be non-negative")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds must be non-negative")

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
            transport=transport,
        )
        self._retries = retries
        self._backoff_seconds = backoff_seconds

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        *_args: object,
    ) -> None:
        del _args
        self.close()

    @property
    def base_url(self) -> str:
        """Configured source base URL without a trailing slash."""
        return str(self._client.base_url).rstrip("/")

    def close(self) -> None:
        self._client.close()

    def fetch(self, path: str, *, params: ParameterMapping | None = None) -> HttpDocument:
        """Fetch a document, retrying transport and transient HTTP failures."""
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        params: ParameterMapping | None = None,
        **kwargs: Any,
    ) -> HttpDocument:
        """Post form data, retrying transport and transient HTTP failures."""
        return self._request("POST", path, params=params, **kwargs)

    def get_soup(self, document: HttpDocument) -> BeautifulSoup:
        """Parse a document body as HTML."""
        return BeautifulSoup(document.body, "html.parser")

    def safe_get_soup(self, document: HttpDocument) -> BeautifulSoup | None:
        """Parse HTML and return ``None`` when the document body is invalid."""
        try:
            return self.get_soup(document)
        except (TypeError, ValueError) as error:
            logger.warning("Unable to parse %s as HTML: %s", document.url, error)
            return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: ParameterMapping | None,
        **kwargs: Any,
    ) -> HttpDocument:
        request_params = url_params_to_str(params)
        last_error: Exception | None = None

        for attempt in range(self._retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    params=request_params if method == "GET" else None,
                    data=request_params if method == "POST" else None,
                    **kwargs,
                )
                if self._is_transient(response):
                    last_error = SourceHttpError(
                        f"Transient source response: {response.status_code}"
                    )
                    if attempt < self._retries:
                        self._sleep_before_retry(attempt)
                        continue
                    break

                response.raise_for_status()
                return self._document(response, request_params or {})
            except httpx.TransportError as error:
                last_error = error
                if attempt < self._retries:
                    self._sleep_before_retry(attempt)
                    continue
                break
            except httpx.HTTPStatusError as error:
                raise SourceHttpError(
                    f"Source returned HTTP {error.response.status_code} for {method} {path}"
                ) from error

        raise SourceHttpError(
            f"Unable to {method.lower()} {path} after {self._retries + 1} attempt(s)"
        ) from last_error

    @classmethod
    def _is_transient(cls, response: httpx.Response) -> bool:
        return response.status_code in cls._TRANSIENT_STATUS_CODES or response.status_code >= 500

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = self._backoff_seconds * (2**attempt)
        if delay:
            time.sleep(delay)

    @staticmethod
    def _document(response: httpx.Response, params: dict[str, str]) -> HttpDocument:
        detection = from_bytes(response.content).best()
        if detection is not None:
            response.encoding = detection.encoding
        else:
            response.encoding = "utf-8"
        return HttpDocument(
            url=str(response.url),
            body=response.content,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            etag=response.headers.get("etag"),
            params=params,
            last_modified=response.headers.get("last-modified"),
        )


def url_params_to_str(params: ParameterMapping | None) -> dict[str, str] | None:
    """Convert domain values to strings accepted by ``httpx``."""
    if params is None:
        return None
    if isinstance(params, Mapping):
        return {key: str(value) for key, value in params.items()}
    return {key: str(value) for key, value in params}
