"""
Vigie — Health endpoint server.

A tiny FastAPI app exposing /health for Docker / Railway health checks.
Runs alongside the Bolt app in the same process (separate thread).

Endpoints:
  GET /health  — returns 200 OK with JSON status
  GET /metrics — returns the live KPIs (when bot is running)
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.health")

app = FastAPI(
    title="Vigie — Health",
    description="Health endpoint for Docker / Railway",
    version="0.0.1",
)

_live_metrics: dict[str, Any] = {}


def update_metrics(metrics: dict[str, Any]) -> None:
    """Called by the Bolt app to refresh the live metrics."""
    global _live_metrics
    _live_metrics = metrics


@app.get("/health")
async def health() -> JSONResponse:
    """Liveness/readiness probe."""
    cfg = get_config()
    return JSONResponse(
        {
            "status": "ok",
            "service": "vigie",
            "workspace": cfg.slack.workspace_name,
            "version": "0.0.1",
        }
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return the last published live metrics (or empty dict if not running)."""
    return JSONResponse({"metrics": _live_metrics})


def start_health_server(port: int | None = None) -> threading.Thread:
    """Start the health server in a daemon thread. Non-blocking."""
    import uvicorn

    cfg = get_config()
    actual_port = port or cfg.deployment.port

    def _run() -> None:
        try:
            uvicorn.run(app, host="0.0.0.0", port=actual_port, log_level="warning")
        except Exception as e:
            log.error("health.server_failed", error=str(e))

    thread = threading.Thread(target=_run, daemon=True, name="vigie-health")
    thread.start()
    log.info("health.started", port=actual_port)
    return thread
