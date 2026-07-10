"""Asynchronous RSS news collection."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping, cast

import feedparser
import httpx

from news_collector.models import NewsArticle

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
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

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
            key=lambda item: item.published_at or item.collected_at,
            reverse=True,
        )

    async def _collect_feed(self, feed_url: str) -> list[NewsArticle]:
        content = await self._fetch_with_retry(feed_url)
        parsed = feedparser.parse(content)

        if parsed.bozo:
            LOGGER.warning(
                "Feed parsing warning for %s: %s", feed_url, parsed.bozo_exception
            )

        entries = cast(Iterable[Mapping[str, Any]], parsed.entries)
        articles = [
            article
            for entry in entries
            if (article := self._entry_to_article(feed_url, entry)) is not None
        ]
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

    def _entry_to_article(
        self, feed_url: str, entry: Mapping[str, Any]
    ) -> NewsArticle | None:
        if not entry.get("title") or not entry.get("link"):
            return None

        url = str(entry.get("link"))
        title = str(entry.get("title")).strip()
        published_at = self._parse_published_at(entry)

        return NewsArticle(
            id=self._article_id(url),
            title=title,
            url=url,
            source_feed_url=feed_url,
            summary=entry.get("summary"),
            author=entry.get("author"),
            published_at=published_at,
        )

    @staticmethod
    def _article_id(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_published_at(entry: Mapping[str, Any]) -> datetime | None:
        for key in ("published", "updated", "created"):
            value = entry.get(key)
            if not value:
                continue
            try:
                parsed = parsedate_to_datetime(str(value))
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=UTC)
                return parsed.astimezone(UTC)
            except (TypeError, ValueError):
                LOGGER.warning("Invalid RSS date value ignored: %s", value)
        return None
