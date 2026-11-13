from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_RECIPIENTS = ["cathaldunphy@gmail.com"]


class Story(BaseModel):
    headline: str
    summary: str
    source: str | None = None
    url: str | None = None


class CountryStories(BaseModel):
    country: str
    stories: list[Story] = Field(default_factory=list)


class BatchStories(BaseModel):
    countries: list[CountryStories] = Field(default_factory=list)


class NewsletterInput(BaseModel):
    edition: Literal["morning", "evening"] = "morning"
    dry_run: bool = False
    recipients: list[str] = Field(default_factory=lambda: list(DEFAULT_RECIPIENTS))


class NewsletterResult(BaseModel):
    subject: str
    countries_covered: int
    stories_collected: int
    sent: bool
    missing_countries: list[str] = Field(default_factory=list)
    html_preview: str | None = None
