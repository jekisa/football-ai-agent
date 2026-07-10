"""Asynchronous RSS news collection."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import httpx

from news_collector.models import NewsArticle
from news_collector.parser import RssParser

LOGGER = logging.getLogger(__name__)


class NewsCollector:
    """Collect and normalize articles from RSS feeds."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
        parser: RssParser | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._parser = parser or RssParser()

    async def __aenter__(self) -> NewsCollector:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP client."""

        if self._owns_client:
            await self._client.aclose()

    async def collect(self, feed_urls: Iterable[str]) -> list[NewsArticle]:
        """Fetch RSS feeds concurrently and return normalized article metadata."""

        urls = list(feed_urls)
        if not urls:
            raise ValueError("At least one RSS feed URL is required.")

        LOGGER.info("Collecting news from %d RSS feeds.", len(urls))
        results = await asyncio.gather(
            *(self._collect_feed(url) for url in urls),
            return_exceptions=True,
        )
        articles: list[NewsArticle] = []

        for result in results:
            if isinstance(result, BaseException):
                LOGGER.exception("RSS feed collection failed.", exc_info=result)
                continue
            articles.extend(result)

        LOGGER.info("Collected %d articles.", len(articles))
        return sorted(
            articles,
            key=lambda item: item.published_at or item.created_at,
            reverse=True,
        )

    async def _collect_feed(self, feed_url: str) -> list[NewsArticle]:
        content = await self._fetch_with_retry(feed_url)
        articles = self._parser.parse(content, source=feed_url)
        LOGGER.info("Collected %d articles from %s.", len(articles), feed_url)
        return articles

    async def _fetch_with_retry(self, feed_url: str) -> bytes:
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.get(feed_url)
                response.raise_for_status()
                return response.content
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                LOGGER.warning(
                    "RSS fetch failed for %s on attempt %d/%d: %s",
                    feed_url,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(
                        self._retry_backoff_seconds * (2 ** (attempt - 1))
                    )

        raise RuntimeError(
            f"Failed to fetch RSS feed after retries: {feed_url}"
        ) from last_error
