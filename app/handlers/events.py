"""
Vigie — Event handlers (async).

Subscribes to Slack events:
- app_mention: when someone @-mentions Vigie
- app_home_opened: when a volunteer opens Vigie's App Home
- message.im: when a volunteer sends a DM to Vigie (check-in notes)
- file_shared: when a volunteer shares a voice note in DM
- reaction_added: quick "OK" reaction on a check-in message
- member_joined_channel: welcome + orientation for new volunteers
"""

from __future__ import annotations

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.say.async_say import AsyncSay

from app.orchestrator import VigieOrchestrator
from app.utils.logging import get_logger

log = get_logger("vigie.handlers.events")


def register(app: AsyncApp) -> None:
    """Register all event handlers on the Bolt app."""

    @app.event("app_mention")
    async def handle_app_mention(event: dict, say: AsyncSay) -> None:
        """Vigie was @-mentioned — respond with help."""
        log.info("vigie.event.app_mention", user=event.get("user"))
        await say(
            "Bonjour, je suis Vigie. "
            "Tapez `/vigie help` pour voir les commandes disponibles. "
            "En cas d'urgence vitale, appelez le 15 ou le 112."
        )

    @app.event("app_home_opened")
    async def handle_app_home_opened(event: dict, client) -> None:
        """Volunteer opened Vigie's App Home — render the dashboard."""
        user_id = event["user"]
        log.info("vigie.event.app_home_opened", user=user_id)

        from slack_sdk.web.async_client import AsyncWebClient

        from app.utils.config import get_config

        cfg = get_config()
        slack_client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
        orch = VigieOrchestrator(slack_client=slack_client)

        home_view = await orch.get_dashboard_state(user_id)
        await client.views_publish(user_id=user_id, view=home_view)

    @app.event("message")
    async def handle_message(event: dict, say: AsyncSay) -> None:
        """
        A DM was sent to Vigie. This is the main entry point for
        volunteer check-in notes (text or voice transcription).
        """
        channel_type = event.get("channel_type")
        if channel_type != "im":
            return  # Only handle DMs

        user_id = event.get("user", "")
        text = event.get("text", "")
        bot_id = event.get("bot_id")

        if bot_id:
            return  # Ignore our own messages

        log.info("vigie.event.message.dm", user=user_id, text_preview=text[:80])

        from slack_sdk.web.async_client import AsyncWebClient

        from app.utils.config import get_config

        cfg = get_config()
        slack_client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
        orch = VigieOrchestrator(slack_client=slack_client)

        result = await orch.process_volunteer_message(
            volunteer_id=user_id,
            text=text,
        )

        if result.get("status") == "no_beneficiary_id":
            # Already handled by orchestrator (DM reply sent)
            pass
        elif result.get("status") == "ok":
            log.info(
                "vigie.event.message.processed",
                beneficiary=result.get("beneficiary_id"),
                anomaly=result.get("anomaly_level"),
            )
        else:
            log.warning("vigie.event.message.failed", result=result)
            await say(f":warning: Erreur lors du traitement : {result.get('message', 'unknown')}")

    @app.event("file_shared")
    async def handle_file_shared(event: dict, say: AsyncSay) -> None:
        """A file (likely voice note) was shared with Vigie."""
        # TODO: fetch file content via files.info, then call orchestrator.process_volunteer_message
        log.info("vigie.event.file_shared", file_id=event.get("file_id"))

    @app.event("reaction_added")
    async def handle_reaction_added(event: dict) -> None:
        """Quick check-in OK via reaction (e.g., :white_check_mark:)."""
        log.debug("vigie.event.reaction_added", reaction=event.get("reaction"))

    @app.event("member_joined_channel")
    async def handle_member_joined(event: dict, say: AsyncSay) -> None:
        """Welcome new volunteer joining a sector channel."""
        log.info(
            "vigie.event.member_joined_channel",
            channel=event.get("channel"),
            user=event.get("user"),
        )

    log.debug("vigie.events.registered")
