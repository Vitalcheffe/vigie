# Vigie — production image (Railway-compatible)

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps (keep curl for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all source files
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY mcp_server ./mcp_server
COPY scripts ./scripts
COPY start.py ./
COPY sandbox_channels.json ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd -r -u 1000 -g root vigie && chown -R vigie:root /app
USER vigie

# No HEALTHCHECK — Socket Mode uses WebSocket
CMD ["python", "start.py"]
