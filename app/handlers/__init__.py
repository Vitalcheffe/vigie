"""Vigie handlers package — Slack event, command, and action handlers."""

from __future__ import annotations

from slack_bolt import App

from app.utils.logging import get_logger

log = get_logger("vigie.handlers")

__all__ = ["register_all"]


def register_all(app: App) -> None:
    """
    Register all Vigie handlers on the Bolt app.

    This is the single entry point called from app.main.create_app().
    Each submodule (events, commands, actions, views) exposes its own
    `register(app)` function.
    """
    # Lazy import to avoid circular deps
    from app.handlers import actions, commands, events, views

    events.register(app)
    commands.register(app)
    actions.register(app)
    views.register(app)

    log.debug("vigie.handlers.all_registered")
