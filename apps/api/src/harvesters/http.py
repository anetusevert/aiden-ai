"""HTTP client utilities for polite web scraping.

This module provides an httpx-based HTTP client with:
- Configurable user-agent
- Rate limiting (minimum delay between requests)
- Retries with exponential backoff for transient errors
- Optional disk cache keyed by sha256(url)
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

DEFAULT_USER_AGENT = "gcc-harvester/0.1.0 (+https://github.com/gcc-harvester)"


class HttpClientError(Exception):
    """Exception raised when HTTP request fails after all retries."""

    def __init__(self, url: str, message: str, last_status: int | None = None) -> None:
        self.url = url
        self.message = message
        self.last_status = last_status
        super().__init__(f"HTTP request failed for {url}: {message}")


class HttpClient:
    """HTTP client wrapper with rate limiting, retries, and disk caching."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        rate: float = 1.0,
        cache_dir: Path | None = None,
        user_agent: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.rate = rate
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.verify_ssl = verify_ssl

        self._min_delay = 1.0 / rate if rate > 0 else 0.0
        self._last_request_time: float = 0.0

        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
            verify=verify_ssl,
        )

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("HTTP cache enabled at: %s", self.cache_dir)

        if not verify_ssl:
            logger.warning("SSL verification disabled - connections may be insecure")

    def _cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _get_cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / f"{self._cache_key(url)}.bin"

    def _read_cache(self, url: str) -> bytes | None:
        cache_path = self._get_cache_path(url)
        if cache_path and cache_path.exists():
            logger.info("Cache HIT: %s", url)
            return cache_path.read_bytes()
        return None

    def _write_cache(self, url: str, data: bytes) -> None:
        cache_path = self._get_cache_path(url)
        if cache_path:
            cache_path.write_bytes(data)
            logger.debug("Cached response for: %s", url)

    def _enforce_rate_limit(self) -> None:
        if self._min_delay <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_delay:
            sleep_time = self._min_delay - elapsed
            logger.debug("Rate limiting: sleeping %.3fs", sleep_time)
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()

    def _calculate_backoff(self, attempt: int) -> float:
        base_delay: float = 2.0 ** attempt
        jitter: float = random.uniform(0, base_delay * 0.5)  # noqa: S311
        return base_delay + jitter

    def _is_retryable_error(self, exc: Exception) -> bool:
        return isinstance(
            exc,
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            ),
        )

    def get(self, url: str) -> bytes:
        """Fetch content from a URL with rate limiting, retries, and caching."""
        cached = self._read_cache(url)
        if cached is not None:
            return cached

        if self.cache_dir:
            logger.info("Cache MISS: %s", url)

        last_error: Exception | None = None
        last_status: int | None = None

        for attempt in range(self.retries + 1):
            self._enforce_rate_limit()

            try:
                response = self._client.get(url)
                last_status = response.status_code

                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.retries:
                        backoff = self._calculate_backoff(attempt)
                        logger.info(
                            "Retry %d/%d for %s (HTTP %d), backoff %.2fs",
                            attempt + 1, self.retries, url,
                            response.status_code, backoff,
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        raise HttpClientError(
                            url,
                            f"HTTP {response.status_code} after {self.retries} retries",
                            last_status=response.status_code,
                        )

                response.raise_for_status()

                content = response.content
                self._write_cache(url, content)
                return content

            except httpx.HTTPStatusError as e:
                logger.info("HTTP error for %s: %s", url, e)
                raise HttpClientError(
                    url,
                    f"HTTP {e.response.status_code}",
                    last_status=e.response.status_code,
                ) from e

            except Exception as e:
                last_error = e
                if self._is_retryable_error(e) and attempt < self.retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.info(
                        "Retry %d/%d for %s (%s), backoff %.2fs",
                        attempt + 1, self.retries, url,
                        type(e).__name__, backoff,
                    )
                    time.sleep(backoff)
                    continue
                elif self._is_retryable_error(e):
                    logger.info("Final failure for %s: %s", url, e)
                    raise HttpClientError(
                        url,
                        f"{type(e).__name__}: {e} after {self.retries} retries",
                        last_status=last_status,
                    ) from e
                else:
                    raise HttpClientError(
                        url,
                        f"{type(e).__name__}: {e}",
                        last_status=last_status,
                    ) from e

        raise HttpClientError(
            url,
            f"Unexpected failure after {self.retries} retries: {last_error}",
            last_status=last_status,
        )

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
