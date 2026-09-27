from dataclasses import dataclass
from time import sleep
from types import TracebackType
from typing import Self

import httpx


class SourceHttpError(RuntimeError):
    """Raised when a source cannot be fetched successfully."""


@dataclass(frozen=True)
class HttpDocument:
    """Successful HTTP response data needed by acquisition and archiving."""

    url: str
    body: bytes
    status_code: int
    content_type: str | None
    etag: str | None
    last_modified: str | None


class SourceHttpClient:
    """Small, deterministic HTTP client with timeout and bounded retries."""

    def __init__(
        self,
        *,
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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch(self, path: str) -> HttpDocument:
        """Fetch one document, retrying transport and transient HTTP failures."""
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(path)
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
                    last_modified=response.headers.get("last-modified"),
                )
            except (httpx.HTTPError, SourceHttpError) as error:
                last_error = error
                if attempt == self._retries:
                    break
                sleep(self._backoff_seconds * (2**attempt))
        raise SourceHttpError(f"Unable to fetch {path}") from last_error
