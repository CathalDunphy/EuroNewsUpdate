import html as html_module

from worker.workflows.countries import Country, flag_emoji
from worker.workflows.models import CountryStories, Story


def build_subject(date_label: str, edition: str, countries_covered: int) -> str:
    return f"Europe Update — {date_label} ({edition.capitalize()} edition): top stories from {countries_covered} countries"


def _escape(value: str | None) -> str:
    return html_module.escape(value) if value else ""


def _story_html(story: Story) -> str:
    headline = _escape(story.headline)
    if story.url:
        headline = f'<a href="{_escape(story.url)}" style="color: #1a3c6e; text-decoration: none;">{headline}</a>'
    source = f' <span style="color: #8a94a6; font-size: 12px;">— {_escape(story.source)}</span>' if story.source else ""
    return (
        f'<li style="margin-bottom: 10px;">'
        f'<strong style="font-size: 14px;">{headline}</strong>{source}'
        f'<div style="color: #3d4757; font-size: 13px; margin-top: 2px;">{_escape(story.summary)}</div>'
        f"</li>"
    )


def _country_html(country: Country, stories: CountryStories) -> str:
    items = "".join(_story_html(story) for story in stories.stories)
    return (
        f'<tr><td style="padding: 8px 0; border-bottom: 1px solid #e4e8ee;">'
        f'<div style="font-size: 15px; font-weight: 700; color: #1a3c6e;">'
        f"{flag_emoji(country.iso2)} {_escape(country.name)}</div>"
        f'<ul style="margin: 6px 0 0; padding-left: 18px;">{items}</ul>'
        f"</td></tr>"
    )


def render_newsletter_html(
    date_label: str,
    edition: str,
    sections: list[tuple[str, list[tuple[Country, CountryStories]]]],
) -> str:
    rows: list[str] = []
    for region, entries in sections:
        if not entries:
            continue
        rows.append(
            f'<tr><td style="padding: 18px 0 4px; font-size: 13px; font-weight: 700; '
            f'letter-spacing: 1px; text-transform: uppercase; color: #8a94a6;">{_escape(region)}</td></tr>'
        )
        for country, stories in entries:
            rows.append(_country_html(country, stories))
    body = "".join(rows)
    return (
        '<div style="font-family: Arial, Helvetica, sans-serif; max-width: 680px; margin: 0 auto;">'
        '<div style="background: #1a3c6e; color: #ffffff; padding: 20px 24px; border-radius: 8px 8px 0 0;">'
        '<div style="font-size: 22px; font-weight: 800;">🇪🇺 Europe Update</div>'
        f'<div style="font-size: 13px; margin-top: 4px; color: #cdd9ec;">{_escape(date_label)} · '
        f"{_escape(edition.capitalize())} edition</div>"
        "</div>"
        '<table style="border-collapse: collapse; width: 100%; background: #ffffff; '
        'border: 1px solid #e4e8ee; border-top: none;">'
        f"{body}"
        "</table>"
        '<div style="color: #8a94a6; font-size: 11px; padding: 12px 4px;">'
        "Compiled automatically from national news sources. Summaries may contain errors — follow the links for full articles."
        "</div>"
        "</div>"
    )


def render_newsletter_text(
    date_label: str,
    edition: str,
    sections: list[tuple[str, list[tuple[Country, CountryStories]]]],
) -> str:
    lines = [f"EUROPE UPDATE — {date_label} ({edition.capitalize()} edition)", ""]
    for region, entries in sections:
        if not entries:
            continue
        lines.append(region.upper())
        for country, stories in entries:
            lines.append(f"  {country.name}")
            for story in stories.stories:
                source = f" ({story.source})" if story.source else ""
                lines.append(f"    - {story.headline}{source}")
                lines.append(f"      {story.summary}")
                if story.url:
                    lines.append(f"      {story.url}")
        lines.append("")
    return "\n".join(lines)
