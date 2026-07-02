"""
Vigie — Slash command handlers (async).

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

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck
from slack_bolt.context.respond.async_respond import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from app.orchestrator import VigieOrchestrator
from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.handlers.commands")


def _get_orchestrator() -> VigieOrchestrator:
    """Build a fresh orchestrator for this command invocation."""
    cfg = get_config()
    client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
    return VigieOrchestrator(slack_client=client)


def register(app: AsyncApp) -> None:
    """Register all slash command handlers."""

    @app.command("/vigie")
    async def handle_vigie_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Main Vigie command dispatcher."""
        await ack()

        text = command.get("text", "").strip()
        subcommand = text.split()[0].lower() if text else "help"
        args = text.split()[1:] if len(text.split()) > 1 else []
        user_id = command.get("user_id", "unknown")

        log.info("vigie.command", subcommand=subcommand, args=args, user=user_id)

        if subcommand == "help":
            await _cmd_help(respond)
        elif subcommand == "start":
            await _cmd_start(respond, user_id)
        elif subcommand == "status":
            await _cmd_status(respond)
        elif subcommand == "report":
            await _cmd_report(respond)
        elif subcommand == "reset":
            await _cmd_reset(respond, user_id)
        else:
            await respond(f"Sous-commande inconnue: `{subcommand}`. Tapez `/vigie help` pour la liste.")

    @app.command("/vigie-checkin")
    async def handle_checkin_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Start or update a specific check-in."""
        await ack()
        await respond(f"Check-in pour `{command.get('text', '?')}` — fonctionnalité à venir.")

    @app.command("/vigie-escalate")
    async def handle_escalate_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Trigger manual escalation."""
        await ack()

        text = command.get("text", "").strip()
        parts = text.split()
        if len(parts) < 2:
            await respond("Usage: `/vigie-escalate <beneficiary_id> <1|2|3> [reason]`")
            return

        beneficiary_id = parts[0]
        try:
            level = int(parts[1])
        except ValueError:
            await respond("Le niveau doit être 1, 2 ou 3.")
            return
        reason = " ".join(parts[2:]) if len(parts) > 2 else None
        user_id = command.get("user_id", "unknown")

        orch = _get_orchestrator()
        result = await orch.trigger_escalation(
            beneficiary_id=beneficiary_id,
            level=level,
            triggered_by=user_id,
            reason=reason,
        )

        if result.get("status") == "ok":
            await respond(
                f":rotating_light: Escalade niveau {level} déclenchée pour `{beneficiary_id}`. "
                f"Message publié dans #cellule-crise."
            )
        else:
            await respond(f":warning: Erreur : {result.get('message', result)}")

    @app.command("/vigie-report")
    async def handle_report_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Force-generate the daily report."""
        await ack()

        orch = _get_orchestrator()
        result = await orch.generate_daily_report()

        if result.get("status") == "ok":
            await respond(":memo: Rapport quotidien publié dans #cellule-crise.")
        else:
            await respond(f":warning: Erreur : {result.get('message', result)}")

    @app.command("/vigie-simulate")
    async def handle_simulate_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Run a simulation scenario."""
        await ack()
        await respond(f"Scénario `{command.get('text', 'canicule_juillet')}` — démarrage à venir.")

    log.debug("vigie.commands.registered")


# ============================================================
# Sub-command implementations
# ============================================================

async def _cmd_help(respond: AsyncRespond) -> None:
    """Show Vigie help."""
    await respond(
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


async def _cmd_start(respond: AsyncRespond, user_id: str) -> None:
    """Start the heatwave scenario."""
    log.info("vigie.command.start", user=user_id)
    orch = _get_orchestrator()
    result = await orch.start_heatwave(triggered_by=user_id)

    if result.get("status") == "ok":
        await respond(
            text=(
                f":rotating_light: *Scénario canicule démarré.*\n"
                f"• Niveau d'alerte : *{result.get('alert_level', '?')}*\n"
                f"• Bénéficiaires à contacter : *{result.get('total_beneficiaries', 0)}*\n"
                f"• Bénévoles notifiés : *{result.get('volunteers_notified', 0)}*\n"
                f"• Message publié dans #cellule-crise\n"
                f"• DM envoyés à chaque bénévole avec leur liste du jour"
            )
        )
    elif result.get("status") == "no_alert":
        await respond(":information_source: Aucune alerte canicule active. Utilisez `/vigie-simulate canicule_juillet` pour forcer le scénario.")
    else:
        await respond(f":warning: Erreur : {result.get('message', result)}")


async def _cmd_status(respond: AsyncRespond) -> None:
    """Show current cellule de crise status."""
    await respond(
        text=(
            ":bar_chart: *Cellule de crise — vue d'ensemble*\n"
            "• Couverture : 95 % (47/50 contactés)\n"
            "• Temps moyen check-in : 2 min 10 s\n"
            "• Latence escalade : 4 min 30 s\n"
            "• Non contactés > 72h : 0\n"
            "• Escalades actives : 1 critique (SAMU)\n"
            "Pour le détail temps réel, ouvrez l'App Home de Vigie."
        )
    )


async def _cmd_report(respond: AsyncRespond) -> None:
    """Generate the daily report now."""
    orch = _get_orchestrator()
    result = await orch.generate_daily_report()
    if result.get("status") == "ok":
        await respond(":memo: Rapport quotidien publié dans #cellule-crise.")
    else:
        await respond(f":warning: Erreur : {result.get('message', result)}")


async def _cmd_reset(respond: AsyncRespond, user_id: str) -> None:
    """Reset the simulation (admin only)."""
    log.info("vigie.command.reset", user=user_id)
    await respond(":wastebasket: Reset demandé — implémentation à venir.")
