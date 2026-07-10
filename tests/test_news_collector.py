"""Unit tests for the News Collector module."""

import httpx
import pytest

from news_collector.config import NewsCollectorSettings
from news_collector.collector import NewsCollector

RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Football Feed</title>
    <item>
      <title>Indonesia wins dramatic match</title>
      <link>https://example.com/news/indonesia-win</link>
      <description>Late goal decides the match.</description>
      <pubDate>Fri, 10 Jul 2026 03:00:00 GMT</pubDate>
      <author>desk@example.com</author>
    </item>
  </channel>
</rss>
"""


def test_settings_accept_comma_separated_rss_urls() -> None:
    """RSS_FEED_URLS accepts normal comma-separated env syntax."""

    settings = NewsCollectorSettings(
        RSS_FEED_URLS="https://example.com/a.xml, https://example.com/b.xml"
    )

    assert settings.rss_feed_urls == [
        "https://example.com/a.xml",
        "https://example.com/b.xml",
    ]


@pytest.mark.asyncio
async def test_collect_returns_normalized_articles() -> None:
    """RSS entries are fetched asynchronously and normalized."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=RSS_FEED, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        collector = NewsCollector(
            timeout_seconds=1,
            max_retries=1,
            retry_backoff_seconds=0,
            user_agent="test",
            client=client,
        )

        articles = await collector.collect(["https://example.com/feed.xml"])

    assert len(articles) == 1
    assert articles[0].title == "Indonesia wins dramatic match"
    assert str(articles[0].url) == "https://example.com/news/indonesia-win"
    assert str(articles[0].source_feed_url) == "https://example.com/feed.xml"
    assert articles[0].published_at is not None


@pytest.mark.asyncio
async def test_collect_retries_failed_request() -> None:
    """Transient HTTP failures are retried before parsing succeeds."""

    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=RSS_FEED, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        collector = NewsCollector(
            timeout_seconds=1,
            max_retries=2,
            retry_backoff_seconds=0,
            user_agent="test",
            client=client,
        )

        articles = await collector.collect(["https://example.com/feed.xml"])

    assert calls == 2
    assert len(articles) == 1


@pytest.mark.asyncio
async def test_collect_deduplicates_articles_by_url() -> None:
    """Repeated links across feeds are emitted once."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=RSS_FEED, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        collector = NewsCollector(
            timeout_seconds=1,
            max_retries=1,
            retry_backoff_seconds=0,
            user_agent="test",
            client=client,
        )

        articles = await collector.collect(
            ["https://example.com/a.xml", "https://example.com/b.xml"]
        )

    assert len(articles) == 1
