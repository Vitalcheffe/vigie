"""
Vigie — Block Kit action handlers.

Handles interactive button clicks, modal submissions, and other
Block Kit interactions.

Callback IDs handled:
- vigie_start_calls       — volunteer starts their daily calls
- vigie_record_checkin    — volunteer submits a check-in note
- vigie_escalate_<level>  — escalate a beneficiary to level 1/2/3
- vigie_close_checkin     — close a check-in as OK
- vigie_signal_anomaly    — global shortcut to report an anomaly
- vigie_reassign          — reassign a beneficiary to another volunteer
"""

from __future__ import annotations

from slack_bolt import App
from slack_bolt.context.ack import Ack

from app.utils.logging import get_logger

log = get_logger("vigie.handlers.actions")


def register(app: App) -> None:
    """Register all Block Kit action handlers."""

    @app.action("vigie_start_calls")
    def handle_start_calls(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer clicked 'Démarrer les appels' in their DM."""
        ack()
        user_id = body["user"]["id"]
        log.info("vigie.action.start_calls", user=user_id)
        # TODO: open modal with the beneficiary list

    @app.action("vigie_record_checkin")
    def handle_record_checkin(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer submitted a check-in note (modal or inline)."""
        ack()
        # TODO: route to Slack AI + MCP record_checkin

    @app.action("vigie_escalate_1")
    def handle_escalate_1(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalader niveau 1' (signal faible)."""
        ack()
        log.info("vigie.action.escalate_1", action=action)
        # TODO: MCP escalate(beneficiary_id, level=1)

    @app.action("vigie_escalate_2")
    def handle_escalate_2(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalader niveau 2' (coordinator)."""
        ack()
        log.info("vigie.action.escalate_2", action=action)
        # TODO: MCP escalate(beneficiary_id, level=2)

    @app.action("vigie_escalate_3")
    def handle_escalate_3(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer clicked 'Escalader niveau 3' (critical, SAMU)."""
        ack()
        log.info("vigie.action.escalate_3", action=action)
        # TODO: MCP escalate(beneficiary_id, level=3) + SAMU button

    @app.action("vigie_close_checkin")
    def handle_close_checkin(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer clicked 'Clôturer' (check-in OK, no escalation)."""
        ack()
        log.info("vigie.action.close_checkin", action=action)
        # TODO: MCP record_checkin + close

    @app.action("vigie_confirm_pharmacy")
    def handle_confirm_pharmacy(ack: Ack, action: dict, body: dict) -> None:
        """Volunteer confirmed the suggested pharmacy for medication delivery."""
        ack()
        log.info("vigie.action.confirm_pharmacy", action=action)
        # TODO: MCP update + notify pharmacy channel

    # Global shortcuts
    @app.shortcut("vigie_signal_anomaly")
    def handle_shortcut_anomaly(ack: Ack, shortcut: dict) -> None:
        """User triggered the 'Signaler une anomalie' shortcut on a message."""
        ack()
        log.info("vigie.shortcut.anomaly", shortcut=shortcut)
        # TODO: open modal to capture anomaly details

    @app.shortcut("vigie_reassign")
    def handle_shortcut_reassign(ack: Ack, shortcut: dict) -> None:
        """User triggered the 'Réassigner ce bénéficiaire' shortcut."""
        ack()
        log.info("vigie.shortcut.reassign", shortcut=shortcut)
        # TODO: open modal to select a new volunteer

    log.debug("vigie.actions.registered")
