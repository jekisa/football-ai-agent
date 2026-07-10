"""Data models for normalized football news."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


class NewsArticle(BaseModel):
    """Normalized internal news record parsed from RSS or Atom metadata."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable deterministic article identifier.")
    source: str
    title: str
    summary: str | None = None
    url: str
    published_at: datetime | None = None
    language: str | None = None
    category: str | None = None
    image_url: str | None = None
    author: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("url", "image_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Validate URL fields and store them as JSON-friendly strings."""

        if value is None:
            return None
        return str(URL_ADAPTER.validate_python(value))
