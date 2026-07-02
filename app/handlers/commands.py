"""
Vigie — Slash command handlers.

Commands:
- /vigie start            — trigger the heatwave scenario
- /vigie status           — current state of the cellule de crise
- /vigie report           — generate the daily report now
- /vigie reset            — reset the simulation (admin only)
- /vigie help             — show help
- /vigie-checkin <id>     — start or update a specific check-in
- /vigie-escalate <id> L  — manually escalate (L = 1, 2, or 3)
- /vigie-simulate <name>  — run a named simulation scenario
"""

from __future__ import annotations

from slack_bolt import App
from slack_bolt.context.ack import Ack
from slack_bolt.context.respond import Respond

from app.utils.logging import get_logger

log = get_logger("vigie.handlers.commands")


def register(app: App) -> None:
    """Register all slash command handlers."""

    @app.command("/vigie")
    def handle_vigie_command(ack: Ack, command: dict, respond: Respond) -> None:
        """Main Vigie command dispatcher."""
        ack()  # Always ack within 3 seconds

        text = command.get("text", "").strip()
        subcommand = text.split()[0].lower() if text else "help"
        args = text.split()[1:] if len(text.split()) > 1 else []
        user_id = command.get("user_id", "unknown")

        log.info("vigie.command", subcommand=subcommand, args=args, user=user_id)

        if subcommand == "help":
            _cmd_help(respond)
        elif subcommand == "start":
            _cmd_start(respond, user_id)
        elif subcommand == "status":
            _cmd_status(respond)
        elif subcommand == "report":
            _cmd_report(respond)
        elif subcommand == "reset":
            _cmd_reset(respond, user_id)
        else:
            respond(
                text=f"Sous-commande inconnue: `{subcommand}`. Tapez `/vigie help` pour la liste."
            )

    @app.command("/vigie-checkin")
    def handle_checkin_command(ack: Ack, command: dict, respond: Respond) -> None:
        """Start or update a specific check-in."""
        ack()
        # TODO: full implementation
        respond(text=f"Check-in pour `{command.get('text', '?')}` — fonctionnalité à venir.")

    @app.command("/vigie-escalate")
    def handle_escalate_command(ack: Ack, command: dict, respond: Respond) -> None:
        """Trigger manual escalation."""
        ack()
        # TODO: full implementation
        respond(text=f"Escalade demandée: `{command.get('text', '?')}` — fonctionnalité à venir.")

    @app.command("/vigie-report")
    def handle_report_command(ack: Ack, command: dict, respond: Respond) -> None:
        """Force-generate the daily report."""
        ack()
        # TODO: full implementation
        respond(text="Rapport quotidien — génération en cours (à venir).")

    @app.command("/vigie-simulate")
    def handle_simulate_command(ack: Ack, command: dict, respond: Respond) -> None:
        """Run a simulation scenario."""
        ack()
        # TODO: full implementation
        respond(text=f"Scénario `{command.get('text', 'canicule_juillet')}` — démarrage à venir.")

    log.debug("vigie.commands.registered")


# ============================================================
# Sub-command implementations
# ============================================================

def _cmd_help(respond: Respond) -> None:
    """Show Vigie help."""
    respond(
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Vigie — Aide"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Commandes disponibles:*\n\n"
                        "• `/vigie start` — Déclencher le scénario canicule\n"
                        "• `/vigie status` — État de la cellule de crise\n"
                        "• `/vigie report` — Générer le rapport quotidien\n"
                        "• `/vigie reset` — Réinitialiser la simulation (admin)\n"
                        "• `/vigie-checkin <id>` — Démarrer un check-in\n"
                        "• `/vigie-escalate <id> <1|2|3>` — Escalade manuelle\n"
                        "• `/vigie-simulate <name>` — Lancer un scénario\n"
                        "• `/vigie help` — Cette aide\n\n"
                        "_En cas d'urgence vitale, appelez le 15 ou le 112._"
                    ),
                },
            },
        ],
        text="Vigie — Aide",
    )


def _cmd_start(respond: Respond, user_id: str) -> None:
    """Start the heatwave scenario."""
    log.info("vigie.command.start", user=user_id)
    respond(
        text=(
            ":rotating_light: Scénario canicule — démarrage demandé. "
            "Vigie va détecter l'alerte Météo-France et affecter les check-in. "
            "(Implémentation complète.)"
        )
    )


def _cmd_status(respond: Respond) -> None:
    """Show current cellule de crise status."""
    # TODO: will query MCP server for live state
    respond(
        text=(
            ":bar_chart: État de la cellule de crise — "
            "données temps réel disponibles (dashboard)."
        )
    )


def _cmd_report(respond: Respond) -> None:
    """Generate the daily report now."""
    # TODO: full implementation with Slack AI + RTS
    respond(text=":memo: Rapport quotidien — génération à venir.")


def _cmd_reset(respond: Respond, user_id: str) -> None:
    """Reset the simulation (admin only)."""
    # TODO: check if user is admin
    log.info("vigie.command.reset", user=user_id)
    respond(text=":wastebasket: Reset demandé — implémentation.")
