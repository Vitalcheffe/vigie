"""
Vigie — Main entry point for the Slack Bolt application (async).

Starts the Slack bot that listens for events, slash commands, and Block Kit
interactions. Uses AsyncApp so handlers can call the MCP client, Slack AI,
and RTS service without blocking.

Usage:
    vigie-bot
    # or
    python -m app.main

The bot uses Socket Mode for development (no public URL needed) and
can switch to HTTP request URL for production.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from app.health import start_health_server
from app.orchestrator import VigieOrchestrator
from app.scheduler import start_scheduler
from app.utils.config import get_config
from app.utils.logging import setup_logging

# Initialize logging FIRST, before anything else
log = setup_logging()


def create_app() -> AsyncApp:
    """
    Create and configure the Slack Bolt async app.

    All handlers are registered here. The app is returned (not started)
    so it can be tested or wrapped if needed.
    """
    cfg = get_config()

    log.info(
        "vigie.app.creating",
        workspace=cfg.slack.workspace_name,
        num_sectors=cfg.slack.num_sectors,
    )

    app = AsyncApp(
        token=cfg.slack.bot_token.get_secret_value(),
        signing_secret=cfg.slack.signing_secret.get_secret_value(),
        ignoring_self_events_enabled=True,
        ssl_check_enabled=True,
        url_verification_enabled=True,
        raise_error_for_unhandled_request=False,
    )

    # Register all handlers
    _register_handlers(app)

    log.info("vigie.app.created")
    return app


def _register_handlers(app: AsyncApp) -> None:
    """Register all event, command, and action handlers."""
    from app.handlers import actions, commands, events, views

    events.register(app)
    commands.register(app)
    actions.register(app)
    views.register(app)

    log.debug("vigie.handlers.registered")


def get_orchestrator(app: AsyncApp) -> VigieOrchestrator:
    """Build the Vigie orchestrator with the app's async Slack client."""
    client = AsyncWebClient(token=get_config().slack.bot_token.get_secret_value())
    return VigieOrchestrator(slack_client=client)


def main() -> None:
    """Start the Vigie Slack bot."""
    cfg = get_config()

    log.info(
        "vigie.starting",
        workspace=cfg.slack.workspace_name,
        port=cfg.deployment.port,
        socket_mode=bool(cfg.slack.app_token),
    )

    # VLM boot self-check — verifies z-ai vision CLI is reachable and that
    # a real screenshot can be analyzed. Non-blocking: failures are logged
    # but do not prevent the bot from starting.
    import asyncio as _asyncio
    from app.services.vlm import boot_self_check

    vlm_probe_path = os.environ.get("VIGIE_VLM_BOOT_IMAGE", "")
    try:
        vlm_check = _asyncio.run(boot_self_check(vlm_probe_path or None))
        if vlm_check.get("ok"):
            log.info("vigie.vlm.boot.ok", step=vlm_check.get("step"))
        else:
            log.warning(
                "vigie.vlm.boot.failed",
                step=vlm_check.get("step"),
                error=vlm_check.get("error"),
            )
    except Exception as e:
        log.warning("vigie.vlm.boot.exception", error=str(e))

    app = create_app()

    # Start the health endpoint (skip on Railway to avoid port conflicts)
    if not os.environ.get("MCP_IN_PROCESS", "false").lower() in ("true", "1", "yes"):
        start_health_server()
    else:
        log.info("vigie.health.skipped_railway")

    # Build the orchestrator and start the background scheduler
    orchestrator = get_orchestrator(app)
    # Only start scheduler if not on Railway (saves memory)
    if not os.environ.get("MCP_IN_PROCESS", "false").lower() in ("true", "1", "yes"):
        scheduler = start_scheduler(orchestrator)
    else:
        log.info("vigie.scheduler.skipped_railway")

    # Graceful shutdown handler
    def shutdown(signum: int, frame: Any) -> None:
        log.info("vigie.shutdown.signal", signal=signum)
        try:
            from app.scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if cfg.slack.app_token:
        # Socket Mode (development)
        log.info("vigie.socket_mode.starting")

        async def _run() -> None:
            # Start scheduler only if not on Railway (saves ~20MB RAM)
            if not os.environ.get("MCP_IN_PROCESS", "false").lower() in ("true", "1", "yes"):
                scheduler.start()
                log.info("vigie.scheduler.started")
            handler = AsyncSocketModeHandler(
                app_token=cfg.slack.app_token.get_secret_value(),
                app=app,
            )
            await handler.start_async()

        asyncio.run(_run())
    else:
        # Production: use the Bolt adapter (requires public URL)
        log.info("vigie.http_mode.starting", port=cfg.deployment.port)
        log.warning(
            "vigie.http_mode.not_configured",
            hint="Set SLACK_APP_TOKEN for Socket Mode, or configure a web framework adapter",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
