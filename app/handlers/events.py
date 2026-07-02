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

import contextlib

import httpx
from slack_bolt.async_app import AsyncApp
from slack_bolt.context.say.async_say import AsyncSay
from slack_sdk.web.async_client import AsyncWebClient

from app.orchestrator import VigieOrchestrator
from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.handlers.events")


async def post_dm_safe(client, user_id: str, text: str) -> None:
    """Best-effort DM via the file_shared handler."""
    try:
        resp = await client.conversations_open(users=user_id)
        channel_id = resp.get("channel", {}).get("id")
        if channel_id:
            await client.chat_postMessage(channel=channel_id, text=text)
    except Exception as e:
        log.warning("vigie.post_dm_safe_failed", user=user_id, error=str(e))


def register(app: AsyncApp) -> None:
    """Register all event handlers on the Bolt app."""

    @app.event("app_mention")
    async def handle_app_mention(event: dict, say: AsyncSay) -> None:
        """Vigie was @-mentioned — respond with help."""
        log.info("vigie.event.app_mention", user=event.get("user"))
        await say(
            "Hello, I am Vigie. "
            "Type `/vigie help` to see the available commands. "
            "In case of life-threatening emergency, call 15 or 112."
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
            await say(f":warning: Error while processing: {result.get('message', 'unknown')}")

    @app.event("file_shared")
    async def handle_file_shared(event: dict, client) -> None:
        """A file (likely voice note) was shared with Vigie in DM.

        Fetches the file content, transcribes via Slack AI / Whisper,
        then routes through the orchestrator as a check-in.
        """
        file_id = event.get("file_id")
        user_id = event.get("user_id", "")
        log.info("vigie.event.file_shared", file_id=file_id, user=user_id)

        if not file_id:
            return

        try:
            # Fetch file info
            file_info_resp = await client.files_info(file=file_id)
            file_info = file_info_resp.get("file", {})
            url_private = file_info.get("url_private_download") or file_info.get("url_private")
            if not url_private:
                log.warning("vigie.event.file_shared.no_url", file_id=file_id)
                return

            # Download the file
            cfg = get_config()
            auth_headers = {"Authorization": f"Bearer {cfg.slack.bot_token.get_secret_value()}"}
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(url_private, headers=auth_headers)
                resp.raise_for_status()
                file_bytes = resp.content

            filename = file_info.get("name", "voice-note")

            # Route through the orchestrator
            slack_client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
            orch = VigieOrchestrator(slack_client=slack_client)
            result = await orch.process_volunteer_message(
                volunteer_id=user_id,
                text="",  # Will be filled by transcription
                file_bytes=file_bytes,
                filename=filename,
            )

            log.info(
                "vigie.event.file_shared.processed",
                status=result.get("status"),
                beneficiary=result.get("beneficiary_id"),
            )

        except Exception as e:
            log.error("vigie.event.file_shared.failed", file_id=file_id, error=str(e))
            # DM the user about the failure
            with contextlib.suppress(Exception):
                await post_dm_safe(client, user_id, f":warning: Could not process your voice note: {e}")

    @app.event("reaction_added")
    async def handle_reaction_added(event: dict) -> None:
        """Quick check-in OK via reaction (e.g., :white_check_mark:)."""
        log.debug("vigie.event.reaction_added", reaction=event.get("reaction"))

    @app.event("member_joined_channel")
    async def handle_member_joined(event: dict, say: AsyncSay, client) -> None:
        """Welcome new volunteer joining a sector channel with a warm DM."""
        user_id = event.get("user", "")
        channel = event.get("channel", "")
        log.info("vigie.event.member_joined_channel", channel=channel, user=user_id)

        # Send a warm welcome DM
        from app.tone import WELCOME_VOLUNTEER
        from app.utils.slack_helpers import get_user_info, post_dm

        try:
            user_info = await get_user_info(client, user_id)
            name = user_info.get("real_name") or user_info.get("display_name") or "there"
            first_name = name.split()[0] if name else "there"

            welcome = WELCOME_VOLUNTEER.format(name=first_name)
            await post_dm(client, user_id, text=welcome)
        except Exception as e:
            log.warning("vigie.welcome_failed", user=user_id, error=str(e))

    log.debug("vigie.events.registered")
