"""Command-line entry point for collecting RSS news."""

from __future__ import annotations

import asyncio
import logging

from news_collector.collector import NewsCollector
from news_collector.config import NewsCollectorSettings
from news_collector.storage import PostgresNewsStore, write_news_json


def configure_logging() -> None:
    """Configure structured-enough logging for containers and local runs."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


async def run() -> None:
    """Collect RSS news and persist output."""

    settings = NewsCollectorSettings()
    async with NewsCollector(
        timeout_seconds=settings.request_timeout_seconds,
        max_retries=settings.max_retries,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        user_agent=settings.user_agent,
    ) as collector:
        articles = await collector.collect(settings.rss_feed_urls)

    await write_news_json(settings.output_path, articles)

    if settings.database_url:
        await PostgresNewsStore(settings.database_url).upsert_articles(articles)


def main() -> None:
    """Run the News Collector CLI."""

    configure_logging()
    try:
        asyncio.run(run())
    except Exception:
        logging.getLogger(__name__).exception("News collection failed.")
        raise


if __name__ == "__main__":
    main()
