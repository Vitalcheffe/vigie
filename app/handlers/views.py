"""
Vigie — Modal view submission handlers.

Handles modal submissions (view submissions) for structured data entry:

- vigie_modal_checkin       — volunteer submits a structured check-in
- vigie_modal_anomaly       — user submits an anomaly report
- vigie_modal_reassign      — user submits a reassignment
- vigie_modal_escalate      — user submits manual escalation details
"""

from __future__ import annotations

from slack_bolt import App
from slack_bolt.context.ack import Ack

from app.utils.logging import get_logger

log = get_logger("vigie.handlers.views")


def register(app: App) -> None:
    """Register all view submission handlers."""

    @app.view("vigie_modal_checkin")
    def handle_checkin_submission(ack: Ack, view: dict, body: dict) -> None:
        """Volunteer submitted the check-in modal."""
        # Validate inputs
        state = view["state"]["values"]
        log.info("vigie.view.checkin_submitted", state=state)
        # TODO: extract fields, route to Slack AI + MCP
        ack()

    @app.view("vigie_modal_anomaly")
    def handle_anomaly_submission(ack: Ack, view: dict, body: dict) -> None:
        """User submitted the anomaly report modal."""
        state = view["state"]["values"]
        log.info("vigie.view.anomaly_submitted", state=state)
        # TODO: route to MCP escalate
        ack()

    @app.view("vigie_modal_reassign")
    def handle_reassign_submission(ack: Ack, view: dict, body: dict) -> None:
        """User submitted the reassignment modal."""
        state = view["state"]["values"]
        log.info("vigie.view.reassign_submitted", state=state)
        # TODO: MCP update volunteer assignment
        ack()

    @app.view("vigie_modal_escalate")
    def handle_escalate_submission(ack: Ack, view: dict, body: dict) -> None:
        """User submitted the manual escalation modal."""
        state = view["state"]["values"]
        log.info("vigie.view.escalate_submitted", state=state)
        # TODO: MCP escalate with custom reason
        ack()

    log.debug("vigie.views.registered")
