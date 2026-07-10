"""Configuration for the News Collector module."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NewsCollectorSettings(BaseSettings):
    """Environment-driven settings for RSS news collection."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    rss_feed_urls_csv: str = Field(default="", alias="RSS_FEED_URLS")
    output_path: Path = Field(default=Path("news.json"), alias="NEWS_OUTPUT_PATH")
    request_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        alias="NEWS_REQUEST_TIMEOUT_SECONDS",
    )
    max_retries: int = Field(default=3, ge=1, alias="NEWS_MAX_RETRIES")
    retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0,
        alias="NEWS_RETRY_BACKOFF_SECONDS",
    )
    user_agent: str = Field(default="football-ai-agent/0.1", alias="NEWS_USER_AGENT")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    @property
    def rss_feed_urls(self) -> list[str]:
        """Parse comma-separated feed URLs from environment variables."""

        return [
            item.strip() for item in self.rss_feed_urls_csv.split(",") if item.strip()
        ]
