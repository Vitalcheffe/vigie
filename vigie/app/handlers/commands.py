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
    async def handle_checkin_command(ack: AsyncAck, command: dict, respond: AsyncRespond, body: dict, client) -> None:
        """Open the structured check-in modal for a beneficiary."""
        await ack()
        beneficiary_id = command.get("text", "").strip()
        if not beneficiary_id:
            await respond("Usage: `/vigie-checkin <beneficiary_id>` (ex: `/vigie-checkin B023`)")
            return

        from app.blocks.modals import build_checkin_modal

        modal = build_checkin_modal(
            beneficiary_id=beneficiary_id,
            beneficiary_name=beneficiary_id,
            sector=None,
        )
        try:
            await client.views_open(trigger_id=body["trigger_id"], view=modal)
        except Exception as e:
            await respond(f":warning: Impossible d'ouvrir le modal : {e}")

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
        """Run a simulation scenario by replaying the canicule events in Slack.

        Uses force_alert=True so the scenario can run even without a real
        Météo-France canicule alert. The alert banner is clearly labeled
        "SCÉNARIO DÉMO" to avoid any confusion with real data.
        """
        await ack()
        scenario_name = command.get("text", "").strip() or "canicule_juillet"
        user_id = command.get("user_id", "unknown")
        log.info("vigie.command.simulate", scenario=scenario_name, user=user_id)

        # Trigger the heatwave scenario with force_alert=True
        orch = _get_orchestrator()
        result = await orch.start_heatwave(triggered_by=user_id, force_alert=True)

        if result.get("status") == "ok":
            await respond(
                f":movie_camera: Scénario `{scenario_name}` démarré (mode démo — alerte clairement étiquetée).\n"
                f"• Bénéficiaires affectés : *{result.get('total_beneficiaries', 0)}*\n"
                f"• Bénévoles notifiés : *{result.get('volunteers_notified', 0)}*\n\n"
                f"Pour simuler un check-in, envoyez-moi un DM : `B023: Mme Dupont fatiguée`.\n"
                f"Pour simuler une escalade : `/vigie-escalate B003 3 \"Au sol, inconsciente\"`.\n"
                f"Pour générer le rapport : `/vigie report`."
            )
        else:
            await respond(f":warning: Erreur : {result.get('message', result)}")

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
    """Start the heatwave scenario using REAL Météo-France alerts.

    If no canicule alert is currently active, the user is invited to use
    /vigie-simulate to force the demo scenario (clearly labeled as such).
    """
    log.info("vigie.command.start", user=user_id)
    orch = _get_orchestrator()
    # force_alert=False: only trigger if a real Météo-France alert is active
    result = await orch.start_heatwave(triggered_by=user_id, force_alert=False)

    if result.get("status") == "ok":
        await respond(
            text=(
                f":rotating_light: *Canicule réelle détectée — scénario démarré.*\n"
                f"• Niveau d'alerte : *{result.get('alert_level', '?')}* (source : Météo-France)\n"
                f"• Bénéficiaires à contacter : *{result.get('total_beneficiaries', 0)}*\n"
                f"• Bénévoles notifiés : *{result.get('volunteers_notified', 0)}*\n"
                f"• Message publié dans #cellule-crise\n"
                f"• DM envoyés à chaque bénévole avec leur liste du jour"
            )
        )
    elif result.get("status") == "no_alert":
        await respond(
            ":information_source: Aucune alerte canicule active détectée par Météo-France. "
            "Pour démarrer le scénario de démo, tapez `/vigie-simulate canicule_juillet`."
        )
    else:
        await respond(f":warning: Erreur : {result.get('message', result)}")


async def _cmd_status(respond: AsyncRespond) -> None:
    """Show current cellule de crise status."""
    from app.state import get_state

    state = get_state()
    metrics = state.get_metrics()
    active_esc = state.get_active_escalations()

    if not metrics.get("scenario_active"):
        await respond(
            ":bar_chart: *Aucun scénario actif.* Tapez `/vigie start` pour déclencher une alerte canicule simulée."
        )
        return

    await respond(
        text=(
            f":bar_chart: *Cellule de crise — vue d'ensemble*\n"
            f":rotating_light: Alerte : *{metrics['alert']['level']}* ({metrics['alert'].get('phenomenon', 'canicule')})\n"
            f":busts_in_silhouette: Bénéficiaires assignés : *{metrics['total_assigned']}*\n"
            f":white_check_mark: Contactés : *{metrics['contacted']}* ({metrics['coverage_pct']}%)\n"
            f":large_green_circle: Check-in OK : *{metrics['ok_count']}*\n"
            f":large_yellow_circle: Signaux faibles : *{metrics['weak_count']}*\n"
            f":large_orange_circle: Escalades coordinateur : *{metrics['coord_escalations']}*\n"
            f":red_circle: Escalades SAMU : *{metrics['samu_escalations']}*\n"
            f":stopwatch: Temps moyen check-in : *{metrics['avg_checkin_time']}*\n"
            f":stopwatch: Latence escalade : *{metrics['avg_escalade_latency']}*\n"
            f":warning: Non contactés > 72h : *{metrics['unreachable_72h']}*\n"
            f":hourglass: Escalades actives non résolues : *{len(active_esc)}*\n\n"
            f"Pour le détail, ouvrez l'App Home de Vigie."
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
    orch = _get_orchestrator()
    result = await orch.reset_scenario(triggered_by=user_id)
    if result.get("status") == "ok":
        await respond(":wastebasket: Cellule de crise réinitialisée. État remis à zéro.")
    else:
        await respond(f":warning: Erreur : {result.get('message', result)}")
