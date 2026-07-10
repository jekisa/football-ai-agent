"""Data models for collected football news."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


class NewsArticle(BaseModel):
    """Normalized RSS article record."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable deterministic article identifier.")
    title: str
    url: str
    source_feed_url: str
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("url", "source_feed_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Validate URL fields and store them as JSON-friendly strings."""

        return str(URL_ADAPTER.validate_python(value))
