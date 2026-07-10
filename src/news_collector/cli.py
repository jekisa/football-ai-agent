"""Command-line entry point for collecting RSS news."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from news_collector.collector import NewsCollector
from news_collector.config import NewsCollectorSettings
from news_collector.storage import write_news_json


class JsonLogFormatter(logging.Formatter):
    """Format log records as JSON for container-friendly structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON log line."""

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure structured logging for containers and local runs."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


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
