"""
Vigie — Event handlers.

Subscribes to Slack events:
- app_mention: when someone @-mentions Vigie
- app_home_opened: when a volunteer opens Vigie's App Home
- message.im: when a volunteer sends a DM to Vigie (check-in notes)
- file_shared: when a volunteer shares a voice note in DM
- reaction_added: quick "OK" reaction on a check-in message
- member_joined_channel: welcome + orientation for new volunteers
- team_join: same for workspace-wide joins
"""

from __future__ import annotations

from slack_bolt import App
from slack_bolt.context.say import Say

from app.utils.logging import get_logger

log = get_logger("vigie.handlers.events")


def register(app: App) -> None:
    """Register all event handlers on the Bolt app."""

    @app.event("app_mention")
    def handle_app_mention(event: dict, say: Say) -> None:
        """Vigie was @-mentioned — respond with help."""
        log.info("vigie.event.app_mention", user=event.get("user"))
        say(
            text=(
                "Bonjour, je suis Vigie. "
                "Tapez `/vigie help` pour voir les commandes disponibles. "
                "En cas d'urgence vitale, appelez le 15 ou le 112."
            )
        )

    @app.event("app_home_opened")
    def handle_app_home_opened(event: dict, client) -> None:
        """Volunteer opened Vigie's App Home — render the dashboard."""
        user_id = event["user"]
        log.info("vigie.event.app_home_opened", user=user_id)

        from app.blocks.dashboard import build_app_home

        home_view = build_app_home(user_id=user_id)
        client.views_publish(user_id=user_id, view=home_view)

    @app.event("message")
    def handle_message(event: dict, say: Say) -> None:
        """
        A DM was sent to Vigie. This is the main entry point for
        volunteer check-in notes (text or voice transcription).

        For now, this is a stub. The full implementation will:
        1. Detect if the message is in a DM with Vigie
        2. Route to Slack AI for transcription (if voice) + extraction
        3. Update the beneficiary record via MCP `record_checkin` tool
        4. Generate a structured message in the sector channel
        """
        # TODO: full implementation
        log.debug("vigie.event.message", channel=event.get("channel"))

    @app.event("file_shared")
    def handle_file_shared(event: dict, say: Say) -> None:
        """A file (likely voice note) was shared with Vigie."""
        # TODO: Slack AI transcription
        log.info("vigie.event.file_shared", file_id=event.get("file_id"))

    @app.event("reaction_added")
    def handle_reaction_added(event: dict) -> None:
        """Quick check-in OK via reaction (e.g., :white_check_mark:)."""
        # TODO: future enhancement
        log.debug("vigie.event.reaction_added", reaction=event.get("reaction"))

    @app.event("member_joined_channel")
    def handle_member_joined(event: dict, say: Say) -> None:
        """Welcome new volunteer joining a sector channel."""
        # TODO: orientation flow
        log.info(
            "vigie.event.member_joined_channel",
            channel=event.get("channel"),
            user=event.get("user"),
        )

    log.debug("vigie.events.registered")
