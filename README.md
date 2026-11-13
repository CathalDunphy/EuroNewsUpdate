# EuroNewsUpdate

Bi-daily newsletter with the top two main news stories from every European country, delivered by email at 09:30 and 18:30 UK time.

## How it works

- A Mistral Workflow (`euro-news-update`) covers 49 European countries, split into 7 region-based batches.
- Each batch runs through a Durable Agent with web search (`mistral-medium-latest` + `WebSearchTool`), which researches the last 24 hours of news from major domestic outlets. All headlines and summaries are produced in English.
- Results are parsed, merged, and rendered into an HTML + plain-text newsletter grouped by region, with country flags.
- The newsletter is sent via the Gmail connector to the configured recipients.
- Failed batches are skipped and reported as `missing_countries` in the workflow result rather than failing the whole run.

## Layout

- `src/worker/workflows/euro_news.py` — workflow definition, agent prompts, parsing, email activity
- `src/worker/workflows/countries.py` — the 49 covered countries, regions, and batches
- `src/worker/workflows/models.py` — input/output models
- `src/worker/workflows/rendering.py` — HTML and plain-text rendering
- `src/worker/entrypoints/worker.py` — worker entrypoint (runs all discovered workflows)
- `tests/` — unit tests plus full workflow tests on a Temporal time-skipping test environment

## Development

```bash
uv sync
uv run pytest
```

## Deployment

The Dockerfile at the repo root builds the worker image. The workflow is deployed as a Mistral managed deployment and scheduled with two cron schedules (`30 9 * * *` morning, `30 18 * * *` evening) in the `Europe/London` timezone.
