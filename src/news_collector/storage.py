"""Storage adapters for collected news."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import asyncpg

from news_collector.models import NewsArticle

LOGGER = logging.getLogger(__name__)


async def write_news_json(path: Path, articles: list[NewsArticle]) -> None:
    """Write collected articles to a JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [article.model_dump(mode="json") for article in articles]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Wrote %d articles to %s.", len(articles), path)


class PostgresNewsStore:
    """Persist collected articles in PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def upsert_articles(self, articles: list[NewsArticle]) -> None:
        """Create the news table if needed and upsert collected articles."""

        if not articles:
            LOGGER.info("No articles to persist in PostgreSQL.")
            return

        connection = await asyncpg.connect(self._database_url)
        try:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source_feed_url TEXT NOT NULL,
                    summary TEXT,
                    author TEXT,
                    published_at TIMESTAMPTZ,
                    collected_at TIMESTAMPTZ NOT NULL
                )
                """)
            await connection.executemany(
                """
                INSERT INTO news_articles (
                    id, title, url, source_feed_url, summary, author,
                    published_at, collected_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    source_feed_url = EXCLUDED.source_feed_url,
                    summary = EXCLUDED.summary,
                    author = EXCLUDED.author,
                    published_at = EXCLUDED.published_at,
                    collected_at = EXCLUDED.collected_at
                """,
                [
                    (
                        article.id,
                        article.title,
                        str(article.url),
                        str(article.source_feed_url),
                        article.summary,
                        article.author,
                        article.published_at,
                        article.collected_at,
                    )
                    for article in articles
                ],
            )
            LOGGER.info("Upserted %d articles into PostgreSQL.", len(articles))
        finally:
            await connection.close()
