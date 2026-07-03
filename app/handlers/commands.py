"""
Vigie — Slash command handlers (async).

Commands:
- /vigie start            — trigger the heatwave scenario
- /vigie status           — current state of the crisis cell
- /vigie report           — generate the daily report now
- /vigie reset            — reset the simulation (admin only)
- /vigie help             — show help
- /vigie-checkin <id>     — start or update a specific check-in
- /vigie-escalate <id> L  — manually escalate (L = 1, 2, or 3)
- /vigie-simulate <name>  — run a named simulation scenario
"""

from __future__ import annotations

import asyncio

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
    async def handle_vigie_command(ack: AsyncAck, command: dict, respond: AsyncRespond, client) -> None:
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
        elif subcommand == "demo":
            await _cmd_demo(respond, user_id)
        elif subcommand == "status":
            await _cmd_status(respond, user_id)
        elif subcommand == "report":
            await _cmd_report(respond)
        elif subcommand == "reset":
            await _cmd_reset(respond, user_id)
        elif subcommand == "inspect":
            await _cmd_inspect(respond, args, client)
        else:
            await respond(f"Unknown subcommand: `{subcommand}`. Type `/vigie help` for the list.")

    @app.command("/vigie-checkin")
    async def handle_checkin_command(ack: AsyncAck, command: dict, respond: AsyncRespond, body: dict, client) -> None:
        """Open the structured check-in modal for a beneficiary."""
        await ack()
        beneficiary_id = command.get("text", "").strip()
        if not beneficiary_id:
            await respond("Usage: `/vigie-checkin <beneficiary_id>` (e.g.: `/vigie-checkin B023`)")
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
            await respond(f":warning: Could not open the modal: {e}")

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
            await respond("The level must be 1, 2, or 3.")
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
                f":rotating_light: Escalation level {level} triggered for `{beneficiary_id}`. "
                f"Message posted in #cellule-crise."
            )
        else:
            await respond(f":warning: Error: {result.get('message', result)}")

    @app.command("/vigie-report")
    async def handle_report_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Force-generate the daily report."""
        await ack()

        orch = _get_orchestrator()
        result = await orch.generate_daily_report()

        if result.get("status") == "ok":
            await respond(":memo: Daily report posted in #cellule-crise.")
        else:
            await respond(f":warning: Error: {result.get('message', result)}")

    @app.command("/vigie-simulate")
    async def handle_simulate_command(ack: AsyncAck, command: dict, respond: AsyncRespond) -> None:
        """Run a simulation scenario by replaying the heatwave events in Slack.

        Uses force_alert=True so the scenario can run even without a real
        Météo-France heatwave alert. The alert banner is clearly labeled
        "DEMO SCENARIO" to avoid any confusion with real data.
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
                f":movie_camera: Scenario `{scenario_name}` started (demo mode — alert clearly labeled).\n"
                f"• Beneficiaries assigned: *{result.get('total_beneficiaries', 0)}*\n"
                f"• Volunteers notified: *{result.get('volunteers_notified', 0)}*\n\n"
                f"To simulate a check-in, send me a DM: `B023: Mrs. Dupont tired`.\n"
                f"To simulate an escalation: `/vigie-escalate B003 3 \"On the ground, unconscious\"`.\n"
                f"To generate the report: `/vigie report`."
            )
        else:
            await respond(f":warning: Error: {result.get('message', result)}")

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
                "text": {"type": "plain_text", "text": "I'm Vigie — here's how I can help", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Quick start for judges:*\n"
                        "• `/vigie demo` — Run the FULL demo (everything in one command)\n\n"
                        "*Individual commands:*\n"
                        "• `/vigie-simulate canicule_juillet` — Start the heatwave scenario\n"
                        "• `/vigie status` — See who's been contacted and who hasn't\n"
                        "• `/vigie report` — Generate today's report with KPIs\n"
                        "• `/vigie inspect <image_path>` — VLM analysis of a dashboard screenshot\n"
                        "• `/vigie reset` — Start over\n"
                        "• `/vigie-escalate B003 3 \"reason\"` — Trigger a SAMU escalation\n\n"
                        "*For volunteers:*\n"
                        "Just wait for my DM — I'll send you a list of people to call with buttons. "
                        "No commands needed.\n\n"
                        "_In a real emergency, call 15 (France) or 112 (EU)._"
                    ),
                },
            },
        ],
        text="Vigie — Help",
    )


async def _cmd_start(respond: AsyncRespond, user_id: str) -> None:
    """Start the heatwave scenario using REAL Météo-France alerts.

    If no heatwave alert is currently active, the user is invited to use
    /vigie-simulate to force the demo scenario (clearly labeled as such).
    """
    log.info("vigie.command.start", user=user_id)
    orch = _get_orchestrator()
    # force_alert=False: only trigger if a real Météo-France alert is active
    result = await orch.start_heatwave(triggered_by=user_id, force_alert=False)

    if result.get("status") == "ok":
        await respond(
            text=(
                f":rotating_light: *Real heatwave detected — scenario started.*\n"
                f"• Alert level: *{result.get('alert_level', '?')}* (source: Météo-France)\n"
                f"• Beneficiaries to contact: *{result.get('total_beneficiaries', 0)}*\n"
                f"• Volunteers notified: *{result.get('volunteers_notified', 0)}*\n"
                f"• Message posted in #cellule-crise\n"
                f"• DMs sent to each volunteer with their list for today"
            )
        )
    elif result.get("status") == "no_alert":
        await respond(
            ":information_source: No active heatwave alert detected by Météo-France. "
            "To start the demo scenario, type `/vigie-simulate canicule_juillet`."
        )
    else:
        await respond(f":warning: Error: {result.get('message', result)}")


async def _cmd_demo(respond: AsyncRespond, user_id: str) -> None:
    """Run the FULL Vigie demo in one command.

    Executes the entire flow:
    1. Reset state
    2. Start heatwave scenario (alert + DM assignments)
    3. Process a simulated volunteer check-in (B023: medication request)
    4. Trigger a critical SAMU escalation (B003: on the ground)
    5. Generate the daily report

    This is the one-command demo for judges.
    """
    log.info("vigie.command.demo", user=user_id)
    await respond(":movie_camera: *Starting full Vigie demo...* This will take ~15 seconds.")

    orch = _get_orchestrator()

    # Step 1: Reset
    await orch.reset_scenario(triggered_by=user_id)
    await asyncio.sleep(1)

    # Step 2: Start heatwave scenario
    await respond(":one: Starting heatwave scenario...")
    result = await orch.start_heatwave(triggered_by=user_id, force_alert=True)
    if result.get("status") != "ok":
        await respond(f":warning: Scenario failed: {result.get('message', result)}")
        return

    await respond(
        f":white_check_mark: Scenario started — {result.get('total_beneficiaries', 0)} beneficiaries, "
        f"{result.get('volunteers_notified', 0)} DMs sent. Check #cellule-crise for the alert."
    )
    await asyncio.sleep(3)

    # Step 3: Simulated check-in
    await respond(":two: Processing a volunteer check-in (B023: medication request)...")
    result = await orch.process_volunteer_message(
        volunteer_id=user_id,
        text="B023: Mrs Dupont tired, requests medication renewal antihypertensive",
    )
    if result.get("status") == "ok":
        await respond(
            f":white_check_mark: Check-in processed — anomaly level {result.get('anomaly_level')} "
            f"(1=weak signal). Check #secteur-11 for the structured message with pharmacy lookup."
        )
    await asyncio.sleep(3)

    # Step 4: Critical escalation
    await respond(":three: Triggering a critical SAMU escalation (B003: on the ground, unconscious)...")
    result = await orch.trigger_escalation(
        beneficiary_id="B003",
        level=3,
        triggered_by=user_id,
        reason="On the ground, unconscious",
    )
    if result.get("status") == "ok":
        await respond(
            f":white_check_mark: SAMU escalation triggered — check #cellule-crise for the "
            f"red alert with context summary and SAMU button."
        )
    await asyncio.sleep(3)

    # Step 5: Daily report
    await respond(":four: Generating the daily report...")
    result = await orch.generate_daily_report()
    if result.get("status") == "ok":
        await respond(":white_check_mark: Daily report posted in #cellule-crise with KPIs + health directives.")
    elif result.get("status") == "no_scenario":
        await respond(":warning: No active scenario — run /vigie demo first.")

    # Summary
    await respond(
        ":tada: *Demo complete!*\n\n"
        "Check these channels:\n"
        "• *#cellule-crise* — alert banner, SAMU escalation, daily report\n"
        "• *#secteur-11* — check-in message with pharmacy lookup\n"
        "• *Your DMs* — volunteer assignment lists\n\n"
        "Type `/vigie status` to see live metrics.\n"
        "Type `/vigie reset` to start over.\n\n"
        "_Vigie — So the heatwave no longer kills in silence._"
    )


async def _cmd_status(respond: AsyncRespond, user_id: str = None) -> None:
    """Show current crisis cell status + volunteer personal progress."""
    from app.state import get_state

    state = get_state()
    metrics = state.get_metrics()
    active_esc = state.get_active_escalations()

    if not metrics.get("scenario_active"):
        await respond(
            ":bar_chart: *No active heatwave alert right now.*\n\n"
            "I'm here if you need me — type `/vigie help` anytime.\n\n"
            "_So the heatwave no longer kills in silence._"
        )
        return

    status_parts = [
        f":bar_chart: *Crisis cell — live status*\n",
        f":rotating_light: Alert: *{metrics['alert']['level']}* (heatwave)\n",
        f":busts_in_silhouette: Elders assigned: *{metrics['total_assigned']}*\n",
        f":white_check_mark: Contacted: *{metrics['contacted']}* ({metrics['coverage_pct']}%)\n",
        f":large_green_circle: OK: *{metrics['ok_count']}*\n",
        f":large_yellow_circle: Weak signals: *{metrics['weak_count']}*\n",
        f":large_orange_circle: Coordinator escalations: *{metrics['coord_escalations']}*\n",
        f":red_circle: SAMU escalations: *{metrics['samu_escalations']}*\n",
        f":stopwatch: Avg check-in time: *{metrics['avg_checkin_time']}*\n",
        f":stopwatch: Avg escalation latency: *{metrics['avg_escalade_latency']}*\n",
        f":warning: Not contacted > 72h: *{metrics['unreachable_72h']}*\n",
        f":hourglass: Active escalations: *{len(active_esc)}*\n",
    ]

    # Personal progress
    if user_id:
        try:
            from app.progress import get_volunteer_progress, build_progress_message
            progress = get_volunteer_progress(user_id)
            if progress["total_assigned"] > 0 or progress["completed"] > 0:
                status_parts.append(f"\n{'─' * 30}\n")
                status_parts.append(build_progress_message("volunteer", progress))
        except Exception as e:
            log.warning("vigie.status.progress_failed", error=str(e))

    await respond(text="".join(status_parts))


async def _cmd_report(respond: AsyncRespond) -> None:
    """Generate the daily report now."""
    orch = _get_orchestrator()
    result = await orch.generate_daily_report()
    if result.get("status") == "ok":
        await respond(":memo: Daily report posted in #cellule-crise.")
    else:
        await respond(f":warning: Error: {result.get('message', result)}")


async def _cmd_reset(respond: AsyncRespond, user_id: str) -> None:
    """Reset the simulation (admin only)."""
    log.info("vigie.command.reset", user=user_id)
    orch = _get_orchestrator()
    result = await orch.reset_scenario(triggered_by=user_id)
    if result.get("status") == "ok":
        await respond(":wastebasket: Crisis cell reset. State cleared.")
    else:
        await respond(f":warning: Error: {result.get('message', result)}")


async def _cmd_inspect(respond: AsyncRespond, args: list[str], client=None) -> None:
    """Analyze a dashboard screenshot using the Vigie VLM service.

    Usage:
        /vigie inspect <image_path>     — analyze a local file
        /vigie inspect                  — analyze the default boot screenshot (if configured)

    The VLM extracts: coverage %, L2/L3 counts, crisis messages, active alerts,
    and computes a dashboard health verdict (OK / ALERT).

    If a Slack client is provided, the screenshot is also uploaded as an image
    attachment alongside the structured analysis.
    """
    from app.services.vlm import get_vlm_service

    image_path = args[0] if args else ""
    if not image_path:
        # Fall back to env-configured boot image
        from app.utils.config import get_config
        image_path = get_config().deployment.vigie_vlm_boot_image if hasattr(get_config().deployment, "vigie_vlm_boot_image") else ""

    if not image_path:
        await respond(
            ":eyes: *Vigie VLM inspect*\n\n"
            "Usage: `/vigie inspect <image_path>`\n\n"
            "Provide the absolute path to a PNG/JPG screenshot of a Vigie dashboard. "
            "The VLM will extract coverage %, L2/L3 counts, active alerts, and a health verdict."
        )
        return

    # Resolve ~ and relative paths
    import os
    image_path = os.path.expanduser(image_path)
    if not os.path.isabs(image_path):
        image_path = os.path.abspath(image_path)

    if not os.path.exists(image_path):
        await respond(f":warning: Image not found: `{image_path}`")
        return

    await respond(f":eyes: Analyzing `{image_path}` with Vigie-VLM (this takes ~5-15s)...")

    service = get_vlm_service()
    analysis = await service.analyze_screenshot(image_path)

    if analysis.parse_error:
        await respond(
            f":warning: VLM analysis failed: `{analysis.parse_error}`\n"
            f"Latency: {analysis.latency_ms:.0f} ms"
        )
        return

    # Build a Slack-formatted summary using Block Kit
    health_emoji = ":white_check_mark:" if analysis.dashboard_health == "OK" else ":rotating_light:"
    alerts_text = (
        "\n".join(f"  • {a['name']} — {a['level']}" for a in analysis.active_alerts)
        if analysis.active_alerts
        else "  (none)"
    )
    sectors_text = ", ".join(analysis.top_sectors) if analysis.top_sectors else "(none)"

    # If we have a Slack client, upload the screenshot as an image attachment
    image_url = None
    if client is not None:
        try:
            from app.utils.config import get_config
            cfg = get_config()
            channel = cfg.slack.cellule_crise_channel_id or ""
            if channel:
                with open(image_path, "rb") as f:
                    upload = await client.files_upload_v2(
                        file=f,
                        filename=os.path.basename(image_path),
                        title=f"Vigie-VLM analysis — {analysis.dashboard_health}",
                        channel=channel,
                        initial_comment=(
                            f"{health_emoji} *Vigie-VLM analysis* ({analysis.latency_ms:.0f} ms)\n"
                            f"*Health:* {analysis.dashboard_health} | "
                            f"*Coverage:* {analysis.coverage_percent}% | "
                            f"*L2:* {analysis.l2_count} | *L3:* {analysis.l3_count}\n"
                            f"_{analysis.summary}_"
                        ),
                    )
                # Get the permalink to the uploaded file
                image_url = upload.get("file", {}).get("permalink", "")
        except Exception as e:
            log.warning("vigie.inspect.upload_failed", error=str(e))

    # Always send the structured analysis via respond (works without client too)
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{health_emoji} Vigie-VLM — {analysis.dashboard_health}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Coverage:* {analysis.coverage_percent if analysis.coverage_percent is not None else 'N/A'}%\n"
                    f"*Avg check-in latency:* {analysis.avg_latency_min if analysis.avg_latency_min is not None else 'N/A'} min\n"
                    f"*L2 (no answer):* {analysis.l2_count if analysis.l2_count is not None else 'N/A'}\n"
                    f"*L3 (unconscious):* {analysis.l3_count if analysis.l3_count is not None else 'N/A'}\n"
                    f"*#cellule-crise messages:* {analysis.crisis_msg_count if analysis.crisis_msg_count is not None else 'N/A'}\n"
                    f"*Sectors visible:* {sectors_text}"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Active alerts:*\n{alerts_text}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"_{analysis.summary}_",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Latency: {analysis.latency_ms:.0f} ms · Source: `{image_path}`",
                }
            ],
        },
    ]

    if image_url:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":frame_with_picture: <{image_url}|View screenshot>",
            },
        })

    await respond(blocks=blocks, text=f"Vigie-VLM — {analysis.dashboard_health}")
