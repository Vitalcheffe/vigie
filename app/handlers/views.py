"""
Vigie — Modal view submission handlers (async).

Handles modal submissions (view submissions) for structured data entry.
"""

from __future__ import annotations

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck

from app.utils.logging import get_logger

log = get_logger("vigie.handlers.views")


def register(app: AsyncApp) -> None:
    """Register all view submission handlers."""

    @app.view("vigie_modal_checkin")
    async def handle_checkin_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """Volunteer submitted the check-in modal."""
        state = view["state"]["values"]
        log.info("vigie.view.checkin_submitted", state=state)
        await ack()

    @app.view("vigie_modal_anomaly")
    async def handle_anomaly_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the anomaly report modal."""
        state = view["state"]["values"]
        log.info("vigie.view.anomaly_submitted", state=state)
        await ack()

    @app.view("vigie_modal_reassign")
    async def handle_reassign_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the reassignment modal."""
        state = view["state"]["values"]
        log.info("vigie.view.reassign_submitted", state=state)
        await ack()

    @app.view("vigie_modal_escalate")
    async def handle_escalate_submission(ack: AsyncAck, view: dict, body: dict) -> None:
        """User submitted the manual escalation modal."""
        state = view["state"]["values"]
        log.info("vigie.view.escalate_submitted", state=state)
        await ack()

    log.debug("vigie.views.registered")
