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
import signal
import sys
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from app.health import start_health_server
from app.orchestrator import VigieOrchestrator
from app.scheduler import start_scheduler, stop_scheduler
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
        token_verification_enabled=True,
        request_verification_enabled=True,
        ignoring_self_events_enabled=True,
        ssl_check_enabled=True,
        url_verification_enabled=True,
        process_before_response=False,
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

    app = create_app()

    # Start the health endpoint in a daemon thread
    start_health_server()

    # Build the orchestrator and start the background scheduler
    orchestrator = get_orchestrator(app)
    scheduler = start_scheduler(orchestrator)

    # Graceful shutdown handler
    def shutdown(signum: int, frame: Any) -> None:
        log.info("vigie.shutdown.signal", signal=signum)
        stop_scheduler()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if cfg.slack.app_token:
        # Socket Mode (development)
        log.info("vigie.socket_mode.starting")

        async def _run() -> None:
            # Start the scheduler in the same event loop as the bot
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
