"""Storage adapters for collected news."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from news_collector.models import NewsArticle

LOGGER = logging.getLogger(__name__)


async def write_news_json(path: Path, articles: list[NewsArticle]) -> None:
    """Write collected articles to a JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [article.model_dump(mode="json") for article in articles]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Wrote %d articles to %s.", len(articles), path)
