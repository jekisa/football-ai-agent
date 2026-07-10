"""Unit tests for RSS and Atom parsing."""

from news_collector.parser import RssParser

RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Football Feed</title>
    <language>en</language>
    <item>
      <title>Indonesia wins dramatic match</title>
      <link>https://example.com/news/indonesia-win</link>
      <description>Late goal decides the match.</description>
      <pubDate>Fri, 10 Jul 2026 03:00:00 GMT</pubDate>
      <category>International</category>
      <author>desk@example.com</author>
      <enclosure url="https://example.com/image.jpg" type="image/jpeg" />
    </item>
  </channel>
</rss>
"""

ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Football</title>
  <updated>2026-07-10T04:00:00Z</updated>
  <entry>
    <title>Club signs new striker</title>
    <link href="https://example.com/news/new-striker" />
    <summary>Transfer confirmed before preseason.</summary>
    <updated>2026-07-10T04:00:00Z</updated>
    <author><name>Transfer Desk</name></author>
    <category term="Transfers" />
  </entry>
</feed>
"""

INVALID_ENTRY_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Football Feed</title>
    <item>
      <description>Missing title and link.</description>
    </item>
    <item>
      <title>Valid story</title>
      <link>https://example.com/news/valid-story</link>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_2_feed_returns_normalized_news() -> None:
    """RSS 2.0 entries are normalized into the internal schema."""

    articles = RssParser().parse(RSS_FEED, source="https://example.com/rss.xml")

    assert len(articles) == 1
    article = articles[0]
    assert article.id
    assert article.source == "https://example.com/rss.xml"
    assert article.title == "Indonesia wins dramatic match"
    assert article.summary == "Late goal decides the match."
    assert article.url == "https://example.com/news/indonesia-win"
    assert article.published_at is not None
    assert article.language == "en"
    assert article.category == "International"
    assert article.image_url == "https://example.com/image.jpg"
    assert article.author == "desk@example.com"
    assert article.created_at is not None


def test_parse_atom_feed_returns_normalized_news() -> None:
    """Atom entries are normalized where common metadata is available."""

    articles = RssParser().parse(ATOM_FEED, source="https://example.com/atom.xml")

    assert len(articles) == 1
    assert articles[0].title == "Club signs new striker"
    assert articles[0].url == "https://example.com/news/new-striker"
    assert articles[0].summary == "Transfer confirmed before preseason."
    assert articles[0].category == "Transfers"
    assert articles[0].author == "Transfer Desk"


def test_parse_skips_invalid_articles() -> None:
    """Entries without required fields are skipped safely."""

    articles = RssParser().parse(
        INVALID_ENTRY_FEED,
        source="https://example.com/rss.xml",
    )

    assert len(articles) == 1
    assert articles[0].title == "Valid story"


def test_parse_malformed_feed_returns_empty_list() -> None:
    """Malformed feeds never crash the parser."""

    articles = RssParser().parse(
        b"<rss><channel><item><title>Broken",
        source="https://example.com/rss.xml",
    )

    assert articles == []
