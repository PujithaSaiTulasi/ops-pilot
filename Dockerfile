# syntax=docker/dockerfile:1
# OpsPilot API image — local/simulated use only, no production credentials.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN useradd --create-home --uid 10001 opspilot

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scenarios ./scenarios
COPY data/runbooks ./data/runbooks
COPY evals/cases.json ./evals/cases.json
COPY ops/mcp/servers.json ./ops/mcp/servers.json

RUN pip install --no-cache-dir . \
    && mkdir -p /app/data /app/evals/results \
    && chown -R opspilot:opspilot /app/data /app/evals/results

USER opspilot

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" || exit 1

CMD ["uvicorn", "opspilot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
