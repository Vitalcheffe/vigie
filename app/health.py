"""
Vigie — Health endpoint server.

A tiny FastAPI app exposing:
  GET /health  — liveness/readiness probe (checks Slack + MCP reachability)
  GET /metrics — returns the live Vigie KPIs (when bot is running)
  GET /audit   — returns the last 100 audit log entries
  GET /audit/stats — returns summary stats for the audit log

Runs alongside the Bolt app in the same process (separate thread).
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

import httpx
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
    """Liveness/readiness probe.

    Checks:
      - Bolt app is running (this endpoint responding proves it)
      - MCP server is reachable on the configured host:port
    Returns 200 with component statuses, or 503 if MCP is down.
    """
    cfg = get_config()

    # Check MCP server reachability
    mcp_url = f"http://{cfg.mcp.host}:{cfg.mcp.port}/mcp"
    mcp_status = "ok"
    mcp_error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Send a JSON-RPC initialize request; we don't care about
            # the response shape, only that the server responds
            resp = await client.post(
                mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "health-check",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "vigie-health", "version": "0.0.1"},
                    },
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Authorization": f"Bearer {cfg.mcp.server_token.get_secret_value()}",
                },
            )
            if resp.status_code >= 500:
                mcp_status = "error"
                mcp_error = f"MCP returned {resp.status_code}"
    except httpx.ConnectError as e:
        mcp_status = "unreachable"
        mcp_error = str(e)
    except httpx.ReadTimeout:
        mcp_status = "timeout"
        mcp_error = "MCP did not respond within 2s"
    except Exception as e:
        mcp_status = "error"
        mcp_error = str(e)

    overall = "ok" if mcp_status == "ok" else "degraded"

    response_body = {
        "status": overall,
        "service": "vigie",
        "version": "0.0.1",
        "workspace": cfg.slack.workspace_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {
            "bolt_app": {"status": "ok"},
            "mcp_server": {"status": mcp_status, "url": mcp_url, "error": mcp_error},
        },
    }

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(response_body, status_code=status_code)


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return the last published live metrics (or empty dict if not running)."""
    return JSONResponse({"metrics": _live_metrics})


@app.get("/audit")
async def audit_log(limit: int = 100) -> JSONResponse:
    """Return the last `limit` audit log entries (most recent first)."""
    from app.audit import get_audit_log

    entries = get_audit_log(limit=limit)
    return JSONResponse({"count": len(entries), "entries": entries})


@app.get("/audit/stats")
async def audit_stats() -> JSONResponse:
    """Return summary stats for the audit log."""
    from app.audit import get_audit_stats

    return JSONResponse(get_audit_stats())


def start_health_server(port: int | None = None) -> threading.Thread:
    """Start the health server in a daemon thread. Non-blocking."""
    import os
    import uvicorn

    # Use the PORT env var directly (Railway sets this automatically)
    # Fall back to the config value, then to 3000
    actual_port = port or int(os.environ.get("PORT", 0)) or 3000

    def _run() -> None:
        try:
            uvicorn.run(app, host="0.0.0.0", port=actual_port, log_level="warning")
        except Exception as e:
            log.error("health.server_failed", error=str(e))

    thread = threading.Thread(target=_run, daemon=True, name="vigie-health")
    thread.start()
    log.info("health.started", port=actual_port)
    return thread
