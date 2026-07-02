"""
Vigie — Modal view submission handlers (async).

Handles modal submissions (view submissions) for structured data entry,
and exposes the modal-open actions that build them.
"""

from __future__ import annotations

import json

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from app.blocks.modals import (
    build_anomaly_modal,
    build_checkin_modal,
    build_escalate_modal,
    build_reassign_modal,
)
from app.orchestrator import VigieOrchestrator
from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.handlers.views")


def _get_orchestrator() -> VigieOrchestrator:
    cfg = get_config()
    client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
    return VigieOrchestrator(slack_client=client)


def register(app: AsyncApp) -> None:
    """Register all view submission handlers + modal-open actions."""

    # ============================================================
    # Modal openers (triggered by buttons / shortcuts)
    # ============================================================

    @app.action("vigie_view_beneficiary")
    async def handle_open_checkin_modal(ack: AsyncAck, action: dict, body: dict, client) -> None:
        """Volunteer clicked 'Full profile' / wants to submit a structured check-in."""
        await ack()
        beneficiary_id = action.get("value", "")
        if not beneficiary_id:
            return

        user_id = body["user"]["id"]
        log.info("vigie.modal.open_checkin", user=user_id, beneficiary=beneficiary_id)

        # In a real deploy we'd fetch the beneficiary from MCP for name + sector.
        # For now use the ID as a fallback display.
        modal = build_checkin_modal(
            beneficiary_id=beneficiary_id,
            beneficiary_name=beneficiary_id,
            sector=None,
        )
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.shortcut("vigie_signal_anomaly")
    async def handle_shortcut_anomaly(ack: AsyncAck, shortcut: dict, body: dict, client) -> None:
        """User triggered the 'Report an anomaly' shortcut on a message."""
        await ack()
        message_ts = shortcut.get("message", {}).get("ts", "")
        channel = shortcut.get("channel", {}).get("id", "")
        log.info("vigie.shortcut.anomaly", channel=channel, ts=message_ts)

        modal = build_anomaly_modal(trigger_message_ts=message_ts, trigger_channel=channel)
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.shortcut("vigie_reassign")
    async def handle_shortcut_reassign(ack: AsyncAck, shortcut: dict, body: dict, client) -> None:
        """User triggered the 'Reassign this beneficiary' shortcut."""
        await ack()
        # The shortcut is triggered from a message — try to extract a beneficiary ID
        text = shortcut.get("message", {}).get("text", "")
        from app.orchestrator import _extract_beneficiary_id

        beneficiary_id = _extract_beneficiary_id(text) or "B???"
        log.info("vigie.shortcut.reassign", beneficiary=beneficiary_id)

        modal = build_reassign_modal(beneficiary_id=beneficiary_id)
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.action("vigie_open_escalate_modal")
    async def handle_open_escalate_modal(ack: AsyncAck, action: dict, body: dict, client) -> None:
        """Volunteer clicked a button that opens the manual escalation modal."""
        await ack()
        raw_value = action.get("value", "{}")
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            payload = {}
        beneficiary_id = payload.get("beneficiary_id", "B???")

        modal = build_escalate_modal(beneficiary_id=beneficiary_id)
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    # ============================================================
    # View submissions
    # ============================================================

    @app.view("vigie_modal_checkin")
    async def handle_checkin_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """Volunteer submitted the check-in modal."""
        state = view["state"]["values"]
        metadata = view.get("private_metadata", "")
        beneficiary_id = metadata.split(":", 1)[1] if ":" in metadata else "?"

        # Extract fields
        state_value = (
            state.get("state_block", {}).get("state", {}).get("selected_option", {}).get("value", "ok")
        )
        notes = state.get("notes_block", {}).get("notes", {}).get("value", "")
        action = (
            state.get("action_block", {}).get("action", {}).get("selected_option", {}).get("value")
        )

        user_id = body["user"]["id"]
        log.info(
            "vigie.view.checkin_submitted",
            user=user_id,
            beneficiary=beneficiary_id,
            state=state_value,
            action=action,
        )

        # Build a synthetic transcript that Vigie can understand
        transcript = f"{beneficiary_id}: {state_value}"
        if notes:
            transcript += f" — {notes}"

        # Route through the orchestrator
        orch = _get_orchestrator()
        result = await orch.process_volunteer_message(
            volunteer_id=user_id,
            text=transcript,
        )

        if result.get("status") != "ok":
            log.warning("vigie.view.checkin_failed", result=result)
            await ack(response_action="errors", errors={
                "state_block": "Error while saving. Try again or contact a coordinator.",
            })
            return

        await ack()

    @app.view("vigie_modal_anomaly")
    async def handle_anomaly_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the anomaly report modal."""
        state = view["state"]["values"]
        beneficiary_id = state.get("beneficiary_block", {}).get("beneficiary_id", {}).get("value", "")
        level_str = (
            state.get("level_block", {}).get("level", {}).get("selected_option", {}).get("value", "1")
        )
        reason = state.get("reason_block", {}).get("reason", {}).get("value", "")

        try:
            level = int(level_str)
        except ValueError:
            level = 1

        user_id = body["user"]["id"]
        log.info(
            "vigie.view.anomaly_submitted",
            user=user_id,
            beneficiary=beneficiary_id,
            level=level,
        )

        if not beneficiary_id:
            await ack(response_action="errors", errors={
                "beneficiary_block": "Beneficiary ID is required.",
            })
            return

        orch = _get_orchestrator()
        await orch.trigger_escalation(
            beneficiary_id=beneficiary_id,
            level=level,
            triggered_by=user_id,
            reason=reason,
        )
        await ack()

    @app.view("vigie_modal_reassign")
    async def handle_reassign_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the reassignment modal."""
        state = view["state"]["values"]
        metadata = view.get("private_metadata", "")
        beneficiary_id = metadata.split(":", 1)[1] if ":" in metadata else "?"
        new_volunteer = state.get("volunteer_block", {}).get("volunteer_id", {}).get("value", "")
        reason = state.get("reason_block", {}).get("reason", {}).get("value", "")

        user_id = body["user"]["id"]
        log.info(
            "vigie.view.reassign_submitted",
            user=user_id,
            beneficiary=beneficiary_id,
            new_volunteer=new_volunteer,
        )

        if not new_volunteer:
            await ack(response_action="errors", errors={
                "volunteer_block": "New volunteer ID is required.",
            })
            return

        # In a real deploy we'd call MCP to update the assignment.
        # For now, log it.
        log.info("vigie.reassign.recorded", beneficiary=beneficiary_id, new_volunteer=new_volunteer, reason=reason)
        await ack()

    @app.view("vigie_modal_escalate")
    async def handle_escalate_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the manual escalation modal."""
        state = view["state"]["values"]
        metadata = view.get("private_metadata", "")
        beneficiary_id = metadata.split(":", 1)[1] if ":" in metadata else "?"
        level_str = (
            state.get("level_block", {}).get("level", {}).get("selected_option", {}).get("value", "1")
        )
        reason = state.get("reason_block", {}).get("reason", {}).get("value", "")

        try:
            level = int(level_str)
        except ValueError:
            level = 1

        user_id = body["user"]["id"]
        log.info(
            "vigie.view.escalate_submitted",
            user=user_id,
            beneficiary=beneficiary_id,
            level=level,
        )

        orch = _get_orchestrator()
        await orch.trigger_escalation(
            beneficiary_id=beneficiary_id,
            level=level,
            triggered_by=user_id,
            reason=reason,
        )
        await ack()

    log.debug("vigie.views.registered")
