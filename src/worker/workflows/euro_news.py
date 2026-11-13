import asyncio
import json
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from temporalio import workflow

import mistralai.workflows as workflows
from mistralai.client.models import WebSearchTool
from mistralai.workflows.plugins.mistralai import Agent, Runner

from worker.workflows.countries import COUNTRIES, COUNTRY_BATCHES, REGION_ORDER, REGIONS, Country
from worker.workflows.models import (
    DEFAULT_RECIPIENTS,
    BatchStories,
    CountryStories,
    NewsletterInput,
    NewsletterResult,
)
from worker.workflows.rendering import build_subject, render_newsletter_html, render_newsletter_text

logger = logging.getLogger(__name__)

def _last_sunday(year: int, month: int) -> datetime:
    if month == 12:
        first_next_month = datetime(year + 1, 1, 1)
    else:
        first_next_month = datetime(year, month + 1, 1)
    last_day = first_next_month - timedelta(days=1)
    return last_day - timedelta(days=last_day.weekday())


def _london_now() -> datetime:
    utc_naive = workflow.now().replace(tzinfo=None)
    bst_start = _last_sunday(utc_naive.year, 3)
    bst_end = _last_sunday(utc_naive.year, 10)
    offset = timedelta(hours=1) if bst_start <= utc_naive < bst_end else timedelta(0)
    return utc_naive + offset


SEARCH_MODEL = "mistral-medium-latest"
SEARCH_INSTRUCTIONS = """You are a news researcher compiling a European news digest.

For each country you are asked about, use web search to find the most important news stories
published in the last 24 hours by that country's major domestic news outlets.

Rules:
- Only include stories about or originating in the given country.
- Prefer the country's leading national outlets over international aggregators.
- Write headlines and summaries in English, regardless of the source language.
- Each summary must be 1-2 factual sentences.
- Never invent stories. If you cannot find significant recent news for a country, return an
  empty stories list for it.
- Return exactly 2 stories per country when possible, ordered by importance.

Respond with ONLY a JSON object in this exact shape, with no markdown fences or extra text:
{"countries": [{"country": "<country name>", "stories": [{"headline": "...", "summary": "...", "source": "<outlet name>", "url": "<article url>"}]}]}
"""

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465


def _send_via_gmail_smtp(subject: str, html: str, text: str, recipients: list[str]) -> str:
    sender = os.environ.get("GMAIL_FROM", "cathaldunphy@gmail.com")
    password = os.environ["GMAIL_APP_PASSWORD"]
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)
    return json.dumps({"sent": True, "to": recipients, "from": sender})


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


def parse_batch_stories(raw: str, expected_countries: list[str]) -> BatchStories:
    data = json.loads(_strip_code_fence(raw))
    batch = BatchStories.model_validate(data)
    expected = {name.lower(): name for name in expected_countries}
    kept: list[CountryStories] = []
    for entry in batch.countries:
        canonical = expected.get(entry.country.lower())
        if canonical is None:
            continue
        kept.append(CountryStories(country=canonical, stories=entry.stories[:2]))
    return BatchStories(countries=kept)


def _extract_text(final_outputs: object) -> str:
    parts: list[str] = []
    for chunk in final_outputs or []:
        text = getattr(chunk, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _batch_prompt(countries: list[Country], edition: str, as_of: str) -> str:
    names = ", ".join(country.name for country in countries)
    return (
        f"Today is {as_of} (Europe/London). Compile the {edition} edition of a European news digest.\n"
        f"Cover exactly these countries: {names}.\n"
        f"For each country, return its top 2 news stories from the last 24 hours in the JSON shape from your instructions."
    )


@workflows.activity(
    name="send-newsletter-email",
    start_to_close_timeout=timedelta(minutes=2),
)
async def send_newsletter_email(
    subject: str,
    html: str,
    text: str,
    recipients: list[str],
) -> str:
    return await asyncio.to_thread(_send_via_gmail_smtp, subject, html, text, recipients)


@workflows.workflow.define(
    name="euro-news-update",
    workflow_display_name="Europe Update Newsletter",
    workflow_description="Bi-daily newsletter with the top two news stories from every European country.",
)
class EuroNewsUpdateWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: NewsletterInput) -> NewsletterResult:
        now = _london_now()
        date_label = now.strftime("%A %d %B %Y")
        as_of = now.strftime("%Y-%m-%d")

        async def run_batch(index: int, countries: list[Country]) -> BatchStories | None:
            agent = Agent(
                name=f"euro-news-searcher-{index}",
                model=SEARCH_MODEL,
                instructions=SEARCH_INSTRUCTIONS,
                tools=[WebSearchTool()],
            )
            try:
                outputs = await Runner.run(agent=agent, inputs=_batch_prompt(countries, input.edition, as_of))
                return parse_batch_stories(_extract_text(outputs), [country.name for country in countries])
            except Exception:
                logger.exception("News batch %d failed", index)
                return None

        batches = await asyncio.gather(
            *(run_batch(index, batch) for index, batch in enumerate(COUNTRY_BATCHES))
        )

        stories_by_country: dict[str, CountryStories] = {}
        for batch in batches:
            if batch is None:
                continue
            for entry in batch.countries:
                stories_by_country[entry.country.lower()] = entry

        missing = [
            country.name
            for country in COUNTRIES
            if country.name.lower() not in stories_by_country
        ]

        sections: list[tuple[str, list[tuple[Country, CountryStories]]]] = []
        for region in REGION_ORDER:
            entries: list[tuple[Country, CountryStories]] = []
            for country in REGIONS[region]:
                entry = stories_by_country.get(country.name.lower())
                if entry and entry.stories:
                    entries.append((country, entry))
            sections.append((region, entries))

        countries_covered = sum(len(entries) for _, entries in sections)
        stories_collected = sum(len(entry.stories) for _, entries in sections for _, entry in entries)
        subject = build_subject(date_label, input.edition, countries_covered)
        html = render_newsletter_html(date_label, input.edition, sections)
        text = render_newsletter_text(date_label, input.edition, sections)

        if input.dry_run:
            return NewsletterResult(
                subject=subject,
                countries_covered=countries_covered,
                stories_collected=stories_collected,
                sent=False,
                missing_countries=missing,
                html_preview=html[:2000],
            )

        await send_newsletter_email(
            subject=subject,
            html=html,
            text=text,
            recipients=input.recipients or DEFAULT_RECIPIENTS,
        )
        return NewsletterResult(
            subject=subject,
            countries_covered=countries_covered,
            stories_collected=stories_collected,
            sent=True,
            missing_countries=missing,
        )
