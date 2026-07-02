"""Vigie handlers package — Slack event, command, and action handlers (async)."""

from __future__ import annotations

from slack_bolt.async_app import AsyncApp

from app.utils.logging import get_logger

log = get_logger("vigie.handlers")

__all__ = ["register_all"]


def register_all(app: AsyncApp) -> None:
    """
    Register all Vigie handlers on the Bolt async app.

    Single entry point called from app.main.create_app().
    Each submodule exposes its own `register(app)` function.
    """
    from app.handlers import actions, commands, events, views

    events.register(app)
    commands.register(app)
    actions.register(app)
    views.register(app)

    log.debug("vigie.handlers.all_registered")
