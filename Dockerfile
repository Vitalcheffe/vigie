# Vigie — production image (Railway-compatible)
# Uses Socket Mode (no HTTP health endpoint needed)

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all source files
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY mcp_server ./mcp_server
COPY scripts ./scripts
COPY start.py ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd -r -u 1000 -g root vigie && chown -R vigie:root /app
USER vigie

# No HEALTHCHECK — Socket Mode uses WebSocket, not HTTP
# No EXPOSE — Socket Mode doesn't need inbound HTTP

# Start the app via the startup wrapper
CMD ["python", "start.py"]
