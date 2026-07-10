"""News Collector module for the football AI agent."""

from news_collector.collector import NewsCollector
from news_collector.models import NewsArticle
from news_collector.parser import RssParser

__all__ = ["NewsArticle", "NewsCollector", "RssParser"]
