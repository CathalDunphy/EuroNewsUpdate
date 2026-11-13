FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --frozen --no-dev

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "--no-dev", "python", "-m", "worker.entrypoints.worker"]
