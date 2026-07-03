"""
Vigie — Block Kit action handlers (async).

Handles interactive button clicks, modal submissions, and other
Block Kit interactions.
"""

from __future__ import annotations

import json

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from app.orchestrator import VigieOrchestrator
from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.handlers.actions")


def _get_orchestrator() -> VigieOrchestrator:
    cfg = get_config()
    client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
    return VigieOrchestrator(slack_client=client)


def register(app: AsyncApp) -> None:
    """Register all Block Kit action handlers."""

    @app.action("vigie_start_calls")
    async def handle_start_calls(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer clicked 'Start calls' in their DM."""
        await ack()
        user_id = body["user"]["id"]
        log.info("vigie.action.start_calls", user=user_id)

    @app.action("vigie_quick_checkin")
    async def handle_quick_checkin(ack: AsyncAck, action: dict, body: dict, client) -> None:
        """Volunteer clicked 'Check-in' next to a beneficiary name.

        Opens a human-friendly modal with the beneficiary's name pre-filled
        and 4 big buttons (OK / Weak signal / No answer / Critical).
        No IDs to type.
        """
        await ack()
        user_id = body["user"]["id"]
        raw_value = action.get("value", "{}")
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            payload = {}

        beneficiary_id = payload.get("beneficiary_id", "")
        beneficiary_name = payload.get("beneficiary_name", beneficiary_id)

        log.info("vigie.action.quick_checkin", user=user_id, beneficiary=beneficiary_id)

        from app.blocks.quick_checkin import build_quick_checkin_modal
        modal = build_quick_checkin_modal(
            beneficiary_id=beneficiary_id,
            beneficiary_name=beneficiary_name,
        )
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    # Quick check-in state buttons (inside the modal)
    @app.action("vigie_state_ok")
    async def handle_state_ok(ack: AsyncAck, action: dict, body: dict, client) -> None:
        await ack()
        await _process_quick_state(action, body, client, state="ok")

    @app.action("vigie_state_weak")
    async def handle_state_weak(ack: AsyncAck, action: dict, body: dict, client) -> None:
        await ack()
        await _process_quick_state(action, body, client, state="weak")

    @app.action("vigie_state_unreachable")
    async def handle_state_unreachable(ack: AsyncAck, action: dict, body: dict, client) -> None:
        await ack()
        await _process_quick_state(action, body, client, state="unreachable")

    @app.action("vigie_state_critical")
    async def handle_state_critical(ack: AsyncAck, action: dict, body: dict, client) -> None:
        await ack()
        await _process_quick_state(action, body, client, state="critical")

    @app.action("vigie_view_my_checkins")
    async def handle_view_my_checkins(ack: AsyncAck, body: dict, client) -> None:
        await ack()
        user_id = body["user"]["id"]
        log.info("vigie.action.view_my_checkins", user=user_id)

    @app.action("vigie_view_cellule_crise")
    async def handle_view_cellule_crise(ack: AsyncAck, body: dict, client) -> None:
        await ack()
        log.info("vigie.action.view_cellule_crise", user=body["user"]["id"])

    @app.action("vigie_record_checkin")
    async def handle_record_checkin(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer submitted a check-in note (modal or inline)."""
        await ack()

    @app.action("vigie_escalate_1")
    async def handle_escalate_1(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalate level 1' (weak signal)."""
        await ack()
        await _do_escalate(action, body, level=1)

    @app.action("vigie_escalate_2")
    async def handle_escalate_2(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalate level 2' (coordinator)."""
        await ack()
        await _do_escalate(action, body, level=2)

    @app.action("vigie_escalate_3")
    async def handle_escalate_3(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalate level 3' (critical, SAMU)."""
        await ack()
        await _do_escalate(action, body, level=3)

    @app.action("vigie_close_checkin")
    async def handle_close_checkin(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer clicked 'Close' (check-in OK, no escalation)."""
        await ack()
        log.info("vigie.action.close_checkin", action_value=action.get("value"))

    @app.action("vigie_confirm_pharmacy")
    async def handle_confirm_pharmacy(ack: AsyncAck, action: dict, body: dict) -> None:
        """Volunteer confirmed the suggested pharmacy."""
        await ack()
        log.info("vigie.action.confirm_pharmacy", action_value=action.get("value"))

    @app.action("vigie_call_samu")
    async def handle_call_samu(ack: AsyncAck, action: dict, body: dict) -> None:
        """Someone clicked the SAMU call button."""
        await ack()
        log.warning("vigie.action.call_samu", user=body["user"]["id"], action_value=action.get("value"))

    @app.action("vigie_resolve_escalation")
    async def handle_resolve_escalation(ack: AsyncAck, action: dict, body: dict) -> None:
        """Coordinator clicked 'Mark as resolved' on an escalation."""
        await ack()
        log.info("vigie.action.resolve_escalation", user=body["user"]["id"])

        # Try to resolve in the state store
        raw_value = action.get("value", "{}")
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            payload = {}
        escalation_id = payload.get("escalation_id")
        if escalation_id:
            from app.state import get_state
            get_state().resolve_escalation(escalation_id)

    log.debug("vigie.actions.registered")


async def _do_escalate(action: dict, body: dict, *, level: int) -> None:
    """Common escalation handler used by all three escalation buttons."""
    user_id = body["user"]["id"]
    raw_value = action.get("value", "{}")
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        payload = {}

    beneficiary_id = payload.get("beneficiary_id")
    if not beneficiary_id:
        log.warning("vigie.escalate.no_beneficiary_in_payload", value=raw_value)
        return

    orch = _get_orchestrator()
    result = await orch.trigger_escalation(
        beneficiary_id=beneficiary_id,
        level=level,
        triggered_by=user_id,
    )

    if result.get("status") != "ok":
        log.warning("vigie.escalate.failed", result=result)


async def _process_quick_state(action: dict, body: dict, client, *, state: str) -> None:
    """Process a quick check-in state button click from the modal.

    Called when the volunteer clicks OK / Weak signal / No answer / Critical
    in the quick check-in modal. Routes through the orchestrator.
    """
    user_id = body["user"]["id"]
    raw_value = action.get("value", "{}")
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        payload = {}

    beneficiary_id = payload.get("beneficiary_id")
    if not beneficiary_id:
        log.warning("vigie.quick_state.no_beneficiary", value=raw_value)
        return

    # Map state to transcript + anomaly level
    state_map = {
        "ok": ("All good, no issues.", 0),
        "weak": ("Weak signal: tired, requests help.", 1),
        "unreachable": ("No answer after 3 calls.", 2),
        "critical": ("Critical: on the ground, unconscious.", 3),
    }
    transcript, anomaly_level = state_map.get(state, ("Unknown state.", 0))

    log.info("vigie.quick_state", beneficiary=beneficiary_id, state=state, user=user_id)

    # If critical, trigger escalation directly
    if anomaly_level == 3:
        orch = _get_orchestrator()
        await orch.trigger_escalation(
            beneficiary_id=beneficiary_id,
            level=3,
            triggered_by=user_id,
            reason=transcript,
        )
        # Close the modal
        await client.views_update(
            view_id=body["view"]["id"],
            view={
                "type": "modal",
                "callback_id": "vigie_modal_checkin",
                "title": {"type": "plain_text", "text": "Done"},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":rotating_light: *Critical escalation triggered for {beneficiary_id}.*\n\nCheck #cellule-crise for the SAMU alert.",
                        },
                    }
                ],
            },
        )
        return

    # For non-critical states, process as a check-in
    orch = _get_orchestrator()
    result = await orch.process_volunteer_message(
        volunteer_id=user_id,
        text=f"{beneficiary_id}: {transcript}",
    )

    # Update the modal to show confirmation
    if result.get("status") == "ok":
        await client.views_update(
            view_id=body["view"]["id"],
            view={
                "type": "modal",
                "callback_id": "vigie_modal_checkin",
                "title": {"type": "plain_text", "text": "Done"},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":white_check_mark: *Check-in recorded for {beneficiary_id}.*\n\nState: {state}\nAnomaly level: {result.get('anomaly_level', 0)}\n\nMessage posted in the sector channel.",
                        },
                    }
                ],
            },
        )
    else:
        await client.views_update(
            view_id=body["view"]["id"],
            view={
                "type": "modal",
                "callback_id": "vigie_modal_checkin",
                "title": {"type": "plain_text", "text": "Error"},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":warning: Could not process check-in: {result.get('message', 'unknown error')}",
                        },
                    }
                ],
            },
        )
