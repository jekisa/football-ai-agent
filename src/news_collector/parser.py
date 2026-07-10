"""RSS and Atom feed parsing into normalized news records."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping, cast

import feedparser
from pydantic import ValidationError

from news_collector.models import NewsArticle

LOGGER = logging.getLogger(__name__)


class RssParser:
    """Parse RSS XML bytes into normalized news article metadata."""

    def parse(self, rss_xml: bytes | str, *, source: str) -> list[NewsArticle]:
        """Return normalized news records from RSS 2.0 or Atom XML."""

        if not rss_xml:
            LOGGER.warning("Received empty RSS payload from %s.", source)
            return []

        try:
            parsed_feed = feedparser.parse(rss_xml)
        except Exception:
            LOGGER.exception("RSS parsing failed for %s.", source)
            return []

        if parsed_feed.bozo:
            LOGGER.warning(
                "RSS parsing warning for %s: %s",
                source,
                parsed_feed.bozo_exception,
            )
            if not parsed_feed.entries:
                return []

        feed = cast(Mapping[str, Any], parsed_feed.feed)
        entries = cast(Iterable[Mapping[str, Any]], parsed_feed.entries)
        articles: list[NewsArticle] = []

        for entry in entries:
            article = self._parse_entry(entry, feed=feed, source=source)
            if article is not None:
                articles.append(article)

        LOGGER.info("Parsed %d articles from %s.", len(articles), source)
        return articles

    def _parse_entry(
        self,
        entry: Mapping[str, Any],
        *,
        feed: Mapping[str, Any],
        source: str,
    ) -> NewsArticle | None:
        title = self._string_or_none(entry.get("title"))
        url = self._entry_url(entry)

        if not title or not url:
            LOGGER.warning("Skipping invalid RSS entry from %s.", source)
            return None

        try:
            return NewsArticle(
                id=self._article_id(url),
                source=source,
                title=title,
                summary=self._string_or_none(
                    entry.get("summary") or entry.get("description")
                ),
                url=url,
                published_at=self._parse_published_at(entry),
                language=self._string_or_none(
                    entry.get("language") or feed.get("language")
                ),
                category=self._category(entry),
                image_url=self._image_url(entry, feed),
                author=self._author(entry),
            )
        except ValidationError as exc:
            LOGGER.warning("Skipping invalid RSS entry from %s: %s", source, exc)
            return None

    @staticmethod
    def _article_id(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _author(entry: Mapping[str, Any]) -> str | None:
        author = RssParser._string_or_none(entry.get("author"))
        if author:
            return author

        authors = entry.get("authors")
        if isinstance(authors, list) and authors:
            first_author = authors[0]
            if isinstance(first_author, Mapping):
                return RssParser._string_or_none(first_author.get("name"))
        return None

    @staticmethod
    def _category(entry: Mapping[str, Any]) -> str | None:
        category = RssParser._string_or_none(entry.get("category"))
        if category:
            return category

        tags = entry.get("tags")
        if isinstance(tags, list) and tags:
            first_tag = tags[0]
            if isinstance(first_tag, Mapping):
                return RssParser._string_or_none(first_tag.get("term"))
        return None

    @staticmethod
    def _entry_url(entry: Mapping[str, Any]) -> str | None:
        link = RssParser._string_or_none(entry.get("link"))
        if link:
            return link

        links = entry.get("links")
        if not isinstance(links, list):
            return None

        for item in links:
            if isinstance(item, Mapping) and item.get("rel") in (None, "alternate"):
                href = RssParser._string_or_none(item.get("href"))
                if href:
                    return href
        return None

    @staticmethod
    def _image_url(entry: Mapping[str, Any], feed: Mapping[str, Any]) -> str | None:
        media_thumbnail = RssParser._first_media_url(entry.get("media_thumbnail"))
        if media_thumbnail:
            return media_thumbnail

        media_content = RssParser._first_media_url(entry.get("media_content"))
        if media_content:
            return media_content

        links = entry.get("links")
        if isinstance(links, list):
            for link in links:
                image_url = RssParser._image_link_url(link)
                if image_url:
                    return image_url

        image = feed.get("image")
        if isinstance(image, Mapping):
            return RssParser._string_or_none(image.get("href") or image.get("url"))
        return None

    @staticmethod
    def _image_link_url(link: object) -> str | None:
        if not isinstance(link, Mapping):
            return None
        mime_type = RssParser._string_or_none(link.get("type"))
        if mime_type and mime_type.startswith("image/"):
            return RssParser._string_or_none(link.get("href"))
        return None

    @staticmethod
    def _first_media_url(media_items: object) -> str | None:
        if not isinstance(media_items, list) or not media_items:
            return None
        first_item = media_items[0]
        if isinstance(first_item, Mapping):
            return RssParser._string_or_none(first_item.get("url"))
        return None

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

    @staticmethod
    def _string_or_none(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
