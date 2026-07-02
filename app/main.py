"""
Vigie — Main entry point for the Slack Bolt application.

This module starts the Slack bot that listens for events, slash commands,
and Block Kit interactions in the workspace sandbox.

Usage:
    vigie-bot
    # or
    python -m app.main

The bot uses Socket Mode for development (no public URL needed) and
can switch to HTTP request URL for production.
"""

from __future__ import annotations

import signal
import sys
from typing import Any

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.utils.config import get_config
from app.utils.logging import setup_logging

# Initialize logging FIRST, before anything else
log = setup_logging()


def create_app() -> App:
    """
    Create and configure the Slack Bolt app.

    All handlers are registered here. The app is returned (not started)
    so it can be tested or wrapped if needed.
    """
    cfg = get_config()

    log.info(
        "vigie.app.creating",
        workspace=cfg.slack.workspace_name,
        num_sectors=cfg.slack.num_sectors,
    )

    app = App(
        token=cfg.slack.bot_token.get_secret_value(),
        signing_secret=cfg.slack.signing_secret.get_secret_value(),
        # Token rotation and other options can be enabled here
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


def _register_handlers(app: App) -> None:
    """
    Register all event, command, and action handlers.

    Handlers are imported lazily to avoid circular imports.
    Each handler module is responsible for its own registration.
    """
    # Lazy imports to avoid circular deps
    from app.handlers import actions, commands, events, views

    events.register(app)
    commands.register(app)
    actions.register(app)
    views.register(app)

    log.debug("vigie.handlers.registered")


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

    # Graceful shutdown handler
    def shutdown(signum: int, frame: Any) -> None:
        log.info("vigie.shutdown.signal", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if cfg.slack.app_token:
        # Socket Mode (development)
        log.info("vigie.socket_mode.starting")
        handler = SocketModeHandler(
            app_token=cfg.slack.app_token.get_secret_value(),
            app=app,
        )
        handler.start()
    else:
        # Production: use the Bolt adapter (requires public URL)
        log.info("vigie.http_mode.starting", port=cfg.deployment.port)
        from slack_bolt.adapter.fastapi import SlackRequestHandler

        handler = SlackRequestHandler(app)
        # In production, mount this handler on a FastAPI/Flask app
        # For now, log a warning
        log.warning(
            "vigie.http_mode.not_configured",
            hint="Set SLACK_APP_TOKEN for Socket Mode, or configure a web framework adapter",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
