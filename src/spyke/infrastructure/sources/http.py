from asyncio.log import logger
from dataclasses import dataclass
from time import sleep
from types import TracebackType
from typing import Self, Any
import re
from bs4 import BeautifulSoup
import httpx
from spyke.domain.enums import RawDataCategory
from spyke.domain.entities import Season, Entity


class SourceHttpError(RuntimeError):
    """Raised when a source cannot be fetched successfully."""


@dataclass(frozen=True)
class HttpDocument:
    url: str
    body: bytes
    status_code: int
    content_type: str
    etag: str
    params: dict[str, Entity | Season | str]
    last_modified: str | None

    def build_storage_key(self, category: RawDataCategory) -> str:
        match category:
            case RawDataCategory.FDME:
                base = "fdme"
                components = ["season", "entity", "competition", "code"]
            case RawDataCategory.CALENDAR:
                base = "calendar"
                components = ["season", "entity"]
            case RawDataCategory.CLUBS:
                base = "clubs"
                components = ["season", "entity"]
            case _:
                raise ValueError(f"Unsupported category: {category}")

        return f"{base}/" + "/".join(
            map(self._safe_component, map(str, (self.get_params(components))))
        )

    def get_params(self, params_list: list[str]) -> list[Entity | Season | str]:
        if any(param not in self.params for param in params_list):
            raise ValueError(f"Missing required parameters: {params_list} in {self.params.keys()}")
        else:
            return [self.params[param] for param in params_list]

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
    """Small, deterministic HTTP client with timeout and bounded retries."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retries: int = 3,
        backoff_seconds: float = 0.5,
        user_agent: str = "Spyke/0.1 (+https://github.com/spyke-project)",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if retries < 0:
            raise ValueError("retries must be non-negative")
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

    @property
    def base_url(self) -> str:
        """Configured source base URL without a trailing slash."""
        return str(self._client.base_url).rstrip("/")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch(
        self, path: str, *, params: dict[str, str | Entity | Season] | None = None
    ) -> HttpDocument:
        """Fetch one document, retrying transport and transient HTTP failures."""
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(path, params=url_params_to_str(params))
                if response.status_code in {408, 429} or response.status_code >= 500:
                    response.raise_for_status()
                    raise SourceHttpError(f"Transient source response: {response.status_code}")
                response.raise_for_status()
                return HttpDocument(
                    url=str(response.url),
                    body=response.content,
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type"),
                    etag=response.headers.get("etag"),
                    params=params,
                    last_modified=response.headers.get("last-modified"),
                )
            except (httpx.HTTPError, SourceHttpError) as error:
                last_error = error
                if attempt == self._retries:
                    break
                sleep(self._backoff_seconds * (2**attempt))
        raise SourceHttpError(f"Unable to fetch {path}") from last_error

    def post(
        self, path: str, *, params: dict[str, str | Entity | Season] | None = None
    ) -> HttpDocument:
        """Post one document, retrying transport and transient HTTP failures."""
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.post(path, data=url_params_to_str(params))
                if response.status_code in {408, 429} or response.status_code >= 500:
                    response.raise_for_status()
                    raise SourceHttpError(f"Transient source response: {response.status_code}")
                response.raise_for_status()
                return HttpDocument(
                    url=str(response.url),
                    body=response.content,
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type"),
                    etag=response.headers.get("etag"),
                    params=params,
                    last_modified=response.headers.get("last-modified"),
                )
            except (httpx.HTTPError, SourceHttpError) as error:
                last_error = error
                if attempt == self._retries:
                    break
                sleep(self._backoff_seconds * (2**attempt))
        raise SourceHttpError(f"Unable to post to {path}") from last_error

    def get_soup(self, document: HttpDocument) -> BeautifulSoup:
        """Récupère et parse une page HTML."""
        return BeautifulSoup(document.body, "html.parser")

    def safe_get_soup(self, document: HttpDocument) -> BeautifulSoup | None:
        """Récupère et parse une page HTML, retourne None en cas d'erreur."""
        try:
            return self.get_soup(document)
        except Exception as e:
            logger.warning("Impossible de récupérer %s : %s", document.url, e)
            return None


def url_params_to_str(params: dict[str, str | Entity | Season] | None) -> dict[str, str] | None:
    if params is None:
        return None
    return {key: str(value) for key, value in params.items()}
