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
