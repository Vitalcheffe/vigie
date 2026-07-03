# Vigie — production image
# Multi-stage build: slim Python 3.11 base, install deps, copy source

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for httpx, structlog, mcp
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY mcp_server ./mcp_server
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd -r -u 1000 -g root vigie && chown -R vigie:root /app
USER vigie

EXPOSE 3000 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run the Bolt app. Override with `command: vigie-mcp` for MCP server.
CMD ["python", "-m", "app.main"]
