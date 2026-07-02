"""
Vigie — MCP Server main entry point.

Exposes 3 resources + 3 tools for the Vigie Slack agent:

Resources:
  - beneficiary_registry   (Plan Canicule registry, simulated)
  - weather_alerts         (Météo-France / NWS vigilance)
  - community_pois         (OpenStreetMap pharmacies, water points, hospitals)

Tools:
  - assign_checkins        (assign daily check-in lists to volunteers)
  - record_checkin         (record a volunteer's check-in return)
  - escalate               (escalate a beneficiary to higher urgency level)

Usage:
    vigie-mcp
    # or
    python -m mcp_server.server

Transports:
  - stdio             (local testing, MCP Inspector)
  - streamable-http   (production, used by Slack agent)
"""

from __future__ import annotations

import signal
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.utils.config import get_config
from app.utils.logging import setup_logging

log = setup_logging()


def create_mcp_server() -> FastMCP:
    """
    Create and configure the Vigie MCP server.

    Uses FastMCP for declarative resource/tool registration.
    """
    cfg = get_config()
    log.info(
        "vigie.mcp.creating",
        transport=cfg.mcp.transport,
        host=cfg.mcp.host,
        port=cfg.mcp.port,
    )

    mcp = FastMCP(
        name="vigie-mcp",
        version="0.0.1",
        instructions=(
            "Vigie MCP server — exposes the Plan Canicule beneficiary registry, "
            "real-time weather alerts, and community points of interest "
            "(pharmacies, water points, hospitals). Provides tools to assign "
            "check-ins, record returns, and trigger escalations."
        ),
    )

    # Register resources (lazy import to avoid circular deps)
    from mcp_server.resources import beneficiary_registry, community_pois, weather_alerts

    beneficiary_registry.register(mcp)
    weather_alerts.register(mcp)
    community_pois.register(mcp)

    # Register tools
    from mcp_server.tools import assign_checkins, escalate, record_checkin

    assign_checkins.register(mcp)
    record_checkin.register(mcp)
    escalate.register(mcp)

    log.info("vigie.mcp.created", resources=3, tools=3)
    return mcp


def main() -> None:
    """Start the Vigie MCP server."""
    cfg = get_config()
    log.info("vigie.mcp.starting", transport=cfg.mcp.transport)

    mcp = create_mcp_server()

    # Graceful shutdown
    def shutdown(signum: int, frame: Any) -> None:
        log.info("vigie.mcp.shutdown.signal", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if cfg.mcp.transport == "stdio":
        mcp.run(transport="stdio")
    elif cfg.mcp.transport in ("sse", "streamable-http"):
        mcp.run(
            transport=cfg.mcp.transport,
            host=cfg.mcp.host,
            port=cfg.mcp.port,
        )
    else:
        log.error("vigie.mcp.unknown_transport", transport=cfg.mcp.transport)
        sys.exit(1)


if __name__ == "__main__":
    main()
