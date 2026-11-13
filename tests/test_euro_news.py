import json
from datetime import UTC, datetime

import pytest
from mistralai.client.models import ConversationResponse, ConversationUsageInfo, MessageOutputEntry, TextChunk
from mistralai.workflows import testing as workflows_testing
from mistralai.workflows.plugins.mistralai.models import mistralai_models as mm
from temporalio.testing import WorkflowEnvironment

import mistralai.workflows as workflows
from mistralai.workflows.plugins.mistralai.connectors.run_as import RunAs
from worker.workflows.countries import COUNTRIES, COUNTRY_BATCHES, flag_emoji
from worker.workflows.euro_news import EuroNewsUpdateWorkflow, parse_batch_stories
from worker.workflows.models import NewsletterInput
from worker.workflows.rendering import build_subject, render_newsletter_html, render_newsletter_text


BATCH_JSON = json.dumps(
    {
        "countries": [
            {
                "country": "France",
                "stories": [
                    {
                        "headline": "Senate passes budget",
                        "summary": "The French Senate approved the budget overnight.",
                        "source": "Le Monde",
                        "url": "https://example.com/1",
                    },
                    {
                        "headline": "Rail strike called off",
                        "summary": "Unions cancelled next week's rail strike.",
                        "source": "Le Figaro",
                        "url": "https://example.com/2",
                    },
                ],
            },
            {
                "country": "Germany",
                "stories": [
                    {"headline": "Coalition talks resume", "summary": "Talks resumed in Berlin."},
                    {"headline": "Bundesliga record", "summary": "A new attendance record was set."},
                ],
            },
            {"country": "Atlantis", "stories": [{"headline": "Should be dropped", "summary": "Not a real country."}]},
        ]
    }
)


def test_flag_emoji() -> None:
    assert flag_emoji("FR") == "\U0001f1eb\U0001f1f7"
    assert flag_emoji("GB") == "\U0001f1ec\U0001f1e7"


def test_country_batches_cover_all_countries() -> None:
    assert len(COUNTRIES) >= 44
    assert sum(len(batch) for batch in COUNTRY_BATCHES) == len(COUNTRIES)


def test_parse_batch_stories_filters_unknown_countries() -> None:
    batch = parse_batch_stories(BATCH_JSON, ["France", "Germany"])
    assert [entry.country for entry in batch.countries] == ["France", "Germany"]
    assert all(len(entry.stories) <= 2 for entry in batch.countries)


def test_parse_batch_stories_handles_markdown_fence() -> None:
    fenced = f"```json\n{BATCH_JSON}\n```"
    batch = parse_batch_stories(fenced, ["France"])
    assert batch.countries[0].country == "France"


def test_parse_batch_stories_rejects_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_batch_stories("not json", ["France"])


def _sample_sections() -> list[tuple[str, list]]:
    from worker.workflows.countries import REGIONS

    batch = parse_batch_stories(BATCH_JSON, ["France", "Germany"])
    by_name = {entry.country: entry for entry in batch.countries}
    sections = []
    for region in ["British Isles & Western Europe", "Central Europe"]:
        entries = [
            (country, by_name[country.name])
            for country in REGIONS[region]
            if country.name in by_name
        ]
        sections.append((region, entries))
    return sections


def test_render_newsletter_html() -> None:
    sections = _sample_sections()
    html = render_newsletter_html("Monday 01 January 2026", "morning", sections)
    assert "Senate passes budget" in html
    assert 'href="https://example.com/1"' in html
    assert "Le Monde" in html
    assert "Central Europe" in html


def test_render_newsletter_text() -> None:
    sections = _sample_sections()
    text = render_newsletter_text("Monday 01 January 2026", "morning", sections)
    assert "Senate passes budget" in text
    assert "Le Monde" in text


def test_build_subject() -> None:
    subject = build_subject("Monday 01 January 2026", "morning", 44)
    assert "Monday 01 January 2026" in subject
    assert "44 countries" in subject


@pytest.fixture
async def temporal_env():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


async def test_workflow_sends_newsletter(temporal_env) -> None:
    sent: list[dict] = []

    async def remote_agent() -> mm.Agent:
        now = datetime.now(UTC)
        return mm.Agent(
            id="agent-1",
            name="euro-news-searcher-test",
            model="mistral-small-latest",
            version=1,
            versions=[1],
            created_at=now,
            updated_at=now,
            deployment_chat=False,
            source="sdk",
        )

    @workflows.activity(name="mistralai_create_agent")
    async def mock_create_agent(params: mm.CreateAgentRequest, run_as: RunAs = RunAs.AUTO) -> mm.Agent:
        return await remote_agent()

    @workflows.activity(name="mistralai_start_conversation")
    async def mock_start_conversation(params: mm.ConversationRequest, run_as: RunAs = RunAs.AUTO) -> ConversationResponse:
        return ConversationResponse(
            conversation_id="conv-1",
            outputs=[MessageOutputEntry(content=[TextChunk(text=BATCH_JSON)])],
            usage=ConversationUsageInfo(),
        )

    @workflows.activity(name="send-newsletter-email")
    async def mock_send_newsletter_email(subject: str, html: str, text: str, recipients: list[str]) -> str:
        sent.append({"subject": subject, "html": html, "text": text, "recipients": recipients})
        return '{"id": "msg-1"}'

    activities = [mock_create_agent, mock_start_conversation, mock_send_newsletter_email]

    async with workflows_testing.create_test_worker(
        temporal_env,
        [EuroNewsUpdateWorkflow],
        activities=activities,
        task_queue=workflows_testing.DEFAULT_TEST_TASK_QUEUE,
    ) as worker:
        result = await temporal_env.client.execute_workflow(
            EuroNewsUpdateWorkflow.run,
            NewsletterInput(edition="morning", dry_run=False, recipients=["reader@example.com"]),
            id="euro-news-update-test-send",
            task_queue=workflows_testing.DEFAULT_TEST_TASK_QUEUE,
        )

    assert result["sent"] is True
    assert result["countries_covered"] == 2
    assert result["stories_collected"] == 4
    assert len(sent) == 1
    assert sent[0]["recipients"] == ["reader@example.com"]
    assert "Senate passes budget" in sent[0]["html"]


async def test_workflow_dry_run_skips_email(temporal_env) -> None:
    sent: list[dict] = []

    @workflows.activity(name="mistralai_create_agent")
    async def mock_create_agent(params: mm.CreateAgentRequest, run_as: RunAs = RunAs.AUTO) -> mm.Agent:
        now = datetime.now(UTC)
        return mm.Agent(
            id="agent-1",
            name="euro-news-searcher-test",
            model="mistral-small-latest",
            version=1,
            versions=[1],
            created_at=now,
            updated_at=now,
            deployment_chat=False,
            source="sdk",
        )

    @workflows.activity(name="mistralai_start_conversation")
    async def mock_start_conversation(params: mm.ConversationRequest, run_as: RunAs = RunAs.AUTO) -> ConversationResponse:
        return ConversationResponse(
            conversation_id="conv-1",
            outputs=[MessageOutputEntry(content=[TextChunk(text=BATCH_JSON)])],
            usage=ConversationUsageInfo(),
        )

    @workflows.activity(name="send-newsletter-email")
    async def mock_send_newsletter_email(subject: str, html: str, text: str, recipients: list[str]) -> str:
        sent.append({"subject": subject})
        return "ok"

    activities = [mock_create_agent, mock_start_conversation, mock_send_newsletter_email]

    async with workflows_testing.create_test_worker(
        temporal_env,
        [EuroNewsUpdateWorkflow],
        activities=activities,
        task_queue=workflows_testing.DEFAULT_TEST_TASK_QUEUE,
    ) as worker:
        result = await temporal_env.client.execute_workflow(
            EuroNewsUpdateWorkflow.run,
            NewsletterInput(edition="evening", dry_run=True),
            id="euro-news-update-test-dry",
            task_queue=workflows_testing.DEFAULT_TEST_TASK_QUEUE,
        )

    assert result["sent"] is False
    assert result["countries_covered"] == 2
    assert sent == []
    assert result["html_preview"] is not None
