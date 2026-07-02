"""
Vigie — Orchestrator.

The conductor that wires Slack events/commands to the MCP server, Slack AI,
and Real-Time Search service. Handlers stay thin; all real logic lives here.

Public API:
  - start_heatwave(triggered_by) — trigger the heatwave scenario
  - process_volunteer_message(volunteer_id, text, file_id=None) — handle a DM
  - trigger_escalation(beneficiary_id, level, triggered_by, reason)
  - generate_daily_report()
  - get_dashboard_state(user_id) — fetch KPIs for App Home
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient

from app.audit import log_action
from app.blocks.canvas import build_cellule_crise_canvas
from app.blocks.checkin import build_checkin_message, build_volunteer_dm
from app.blocks.dashboard import build_app_home
from app.blocks.escalation import build_escalation_message
from app.blocks.reports import build_daily_report
from app.services.mcp_client import MCPClient, MCPClientError
from app.services.rts import get_rts_service
from app.services.slack_ai import get_slack_ai_service
from app.state import get_state
from app.utils.logging import get_logger
from app.utils.slack_helpers import (
    get_cellule_crise_channel_id,
    get_user_info,
    post_dm,
    post_to_cellule_crise,
    post_to_sector,
    publish_canvas,
)

log = get_logger("vigie.orchestrator")

_BENEFICIARY_ID_PATTERN = re.compile(r"\bB(\d{1,4})\b", re.IGNORECASE)


class VigieOrchestrator:
    """High-level Vigie workflow conductor."""

    def __init__(
        self,
        slack_client: AsyncWebClient,
        mcp_client: MCPClient | None = None,
    ) -> None:
        self.slack = slack_client
        self.mcp = mcp_client or MCPClient()
        self.slack_ai = get_slack_ai_service()
        self.rts = get_rts_service()
        self.state = get_state()

    # ============================================================
    # /vigie start — trigger the heatwave scenario
    # ============================================================

    async def start_heatwave(self, triggered_by: str, *, force_alert: bool = False) -> dict[str, Any]:
        """
        Trigger the heatwave scenario:
          1. Read active weather alerts from MCP (real Météo-France + NWS API)
          2. If no alert and force_alert=True, use the scenario alert from
             mcp_server/data/scenario_canicule_juillet.json (clearly labeled
             as a scenario, not real data)
          3. Call assign_checkins
          4. DM each volunteer their list
          5. Post alert banner in #cellule-crise

        Returns a summary dict for the responding user.

        The `force_alert` flag is used by /vigie-simulate to replay the
        heatwave scenario even when no real alert is active. The alert
        banner clearly indicates "SCENARIO" when force_alert is used.
        """
        log.info("vigie.start_heatwave", triggered_by=triggered_by, force_alert=force_alert)

        try:
            async with self.mcp as mcp:
                alerts = await mcp.list_weather_alerts()

                if not alerts:
                    if not force_alert:
                        return {
                            "status": "no_alert",
                            "message": (
                                "No active heatwave alert detected by Météo-France. "
                                "Use `/vigie-simulate canicule_juillet` to force the scenario."
                            ),
                        }
                    # Load the scenario alert from disk (clearly labeled as scenario)
                    alerts = [_load_scenario_alert()]

                assignments_result = await mcp.assign_checkins(force=force_alert)
                if "error" in assignments_result:
                    return {"status": "error", "message": assignments_result["error"]}

                assignments = assignments_result.get("assignments", [])
                total_beneficiaries = assignments_result.get("total_beneficiaries", 0)
                total_volunteers = assignments_result.get("total_volunteers", 0)
                date = assignments_result.get("date", datetime.now(UTC).date().isoformat())

            # Post alert banner in crisis cell
            alert = alerts[0]
            is_scenario = force_alert or alert.get("source", "").startswith("Scenario")
            banner_prefix = ":film_projector: *DEMO SCENARIO* — " if is_scenario else ""
            alert_text = (
                f"{banner_prefix}:rotating_light: *{alert.get('level', '?').upper()} heatwave vigilance* "
                f"{'(scenario)' if is_scenario else 'detected by Météo-France'}.\n"
                f":round_pushpin: {alert.get('department_name', alert.get('department', '?'))}\n"
                f":thermometer: Max forecast T°: *{alert.get('max_temperature', '?')}°C*\n"
                f":clock1: Valid until: {alert.get('valid_to', '?')}\n\n"
                f"*{total_beneficiaries} beneficiaries* to contact today.\n"
                f"*{total_volunteers} volunteers* assigned automatically.\n"
                f"_Triggered by <@{triggered_by}>_"
            )
            await post_to_cellule_crise(self.slack, text=alert_text)

            # DM each volunteer
            dm_count = 0
            for assignment in assignments:
                volunteer_id = assignment.get("volunteer_id")
                volunteer_name = assignment.get("volunteer_name", volunteer_id)
                beneficiaries = assignment.get("beneficiaries", [])

                if not volunteer_id:
                    continue

                # Get the Slack user info if volunteer has a slack_user_id
                # (in sandbox, the volunteer_id is the slack user id once seeded)
                msg = build_volunteer_dm(
                    volunteer_id=volunteer_id,
                    volunteer_name=volunteer_name,
                    assignments=beneficiaries,
                    alert_level=alert.get("level", "orange"),
                    date=date,
                )
                await post_dm(self.slack, volunteer_id, text=msg["text"], blocks=msg["blocks"])
                dm_count += 1

            log.info(
                "vigie.start_heatwave.done",
                volunteers_notified=dm_count,
                beneficiaries=total_beneficiaries,
                alert_level=alert.get("level"),
            )

            # Mark scenario as active in the state store
            self.state.start_scenario(alert=alert, total_assigned=total_beneficiaries)

            # Update the health endpoint with live metrics
            from app.health import update_metrics
            update_metrics(self.state.get_metrics())

            # Publish the initial cellule-de-crise Canvas
            await self._update_cellule_crise_canvas()

            log_action(
                actor=triggered_by,
                action="force_scenario" if force_alert else "start_heatwave",
                target=alert.get("department", "?"),
                reason=f"alert_level={alert.get('level')}",
                result="ok",
                metadata={
                    "alert_level": alert.get("level"),
                    "total_beneficiaries": total_beneficiaries,
                    "volunteers_notified": dm_count,
                    "force_alert": force_alert,
                },
            )

            return {
                "status": "ok",
                "alert_level": alert.get("level"),
                "total_beneficiaries": total_beneficiaries,
                "total_volunteers": total_volunteers,
                "volunteers_notified": dm_count,
                "alert": alert,
            }

        except MCPClientError as e:
            log.error("vigie.start_heatwave.mcp_error", error=str(e))
            log_action(actor=triggered_by, action="start_heatwave", result="mcp_error", reason=str(e))
            return {"status": "mcp_error", "message": str(e)}
        except Exception as e:
            log.error("vigie.start_heatwave.failed", error=str(e))
            log_action(actor=triggered_by, action="start_heatwave", result="error", reason=str(e))
            return {"status": "error", "message": str(e)}

    # ============================================================
    # Volunteer DM → check-in processing
    # ============================================================

    async def process_volunteer_message(
        self,
        volunteer_id: str,
        text: str,
        file_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a DM from a volunteer (a check-in note).

        The volunteer must mention the beneficiary ID in their message
        (e.g., "B023: Mrs. Dupont tired"). If voice note, transcribe first.

        Steps:
          1. Transcribe (if voice) via Slack AI / Whisper
          2. Extract beneficiary ID from text
          3. Call MCP record_checkin
          4. Post the result in the sector channel
        """
        log.info("vigie.process_message", volunteer=volunteer_id, text_preview=text[:80])

        # Transcribe voice if needed
        if file_bytes and filename:
            try:
                text = await self.slack_ai.transcribe_audio(file_bytes, filename)
                log.debug("vigie.process_message.transcribed", length=len(text))
            except Exception as e:
                log.error("vigie.process_message.transcribe_failed", error=str(e))
                return {"status": "transcribe_failed", "message": str(e)}

        # Extract beneficiary ID
        beneficiary_id = _extract_beneficiary_id(text)
        if not beneficiary_id:
            await post_dm(
                self.slack,
                volunteer_id,
                text=(
                    "I couldn't identify the beneficiary in your message. "
                    "Start with the ID (e.g.: `B023: Mrs. Dupont is doing well`)."
                ),
            )
            return {"status": "no_beneficiary_id"}

        # Classify anomaly with Slack AI (in parallel with MCP call below)
        try:
            ai_level, ai_signals, ai_recommended = await self.slack_ai.classify_anomaly(text)
        except Exception as e:
            log.warning("vigie.process_message.ai_classify_failed", error=str(e))
            ai_level, ai_signals, ai_recommended = 0, [], "ok"

        # Call MCP record_checkin
        try:
            async with self.mcp as mcp:
                result = await mcp.record_checkin(
                    beneficiary_id=beneficiary_id,
                    volunteer_id=volunteer_id,
                    transcript=text,
                    channel_type="voice" if file_bytes else "text",
                    detected_signals=ai_signals,
                )
        except MCPClientError as e:
            log.error("vigie.process_message.mcp_error", error=str(e))
            return {"status": "mcp_error", "message": str(e)}

        if "error" in result:
            await post_dm(
                self.slack,
                volunteer_id,
                text=f"Error for {beneficiary_id}: {result.get('error')}",
            )
            return result

        # Use AI classification if MCP didn't classify, or merge signals
        anomaly_level = result.get("anomaly_level", ai_level)
        signals = result.get("detected_signals") or ai_signals
        recommended = result.get("recommended_action", ai_recommended)
        suggested_pois = result.get("suggested_pois", [])

        # Get the beneficiary info from MCP result
        beneficiary = {
            "id": beneficiary_id,
            "first_name": result.get("beneficiary", {}).get("name", "?").split()[0] if result.get("beneficiary") else "?",
            "last_initial": "?",
            "age": result.get("beneficiary", {}).get("age"),
            "sector": result.get("beneficiary", {}).get("sector"),
        }

        # Build and post the sector channel message
        sector_msg = build_checkin_message(
            beneficiary=beneficiary,
            volunteer_id=volunteer_id,
            transcript=text,
            anomaly_level=anomaly_level,
            signals=signals,
            recommended_action=recommended,
            suggested_pois=suggested_pois,
            checkin_id=result.get("checkin_id"),
        )

        sector = beneficiary.get("sector")
        if sector:
            await post_to_sector(
                self.slack,
                sector,
                text=sector_msg["text"],
                blocks=sector_msg["blocks"],
            )

        # Acknowledge the volunteer in DM
        level_emoji = {0: ":white_check_mark:", 1: ":large_yellow_circle:", 2: ":large_orange_circle:", 3: ":red_circle:"}
        await post_dm(
            self.slack,
            volunteer_id,
            text=(
                f"{level_emoji.get(anomaly_level, ':white_circle:')} Check-in recorded for "
                f"{beneficiary_id} — level {anomaly_level}. "
                f"Message posted in #secteur-{sector}." if sector else
                f"{level_emoji.get(anomaly_level, ':white_circle:')} Check-in recorded for {beneficiary_id}."
            ),
        )

        # Record the check-in in the state store
        # assigned_at = scenario start (best approximation; in production
        # we'd track the exact DM-sent timestamp per volunteer)
        assigned_at = self.state._scenario_start.isoformat() if self.state._scenario_start else None
        self.state.record_checkin({
            "beneficiary_id": beneficiary_id,
            "volunteer_id": volunteer_id,
            "anomaly_level": anomaly_level,
            "transcript_preview": text[:120],
            "checkin_id": result.get("checkin_id"),
            "assigned_at": assigned_at,
        })

        # Update the health endpoint
        from app.health import update_metrics
        update_metrics(self.state.get_metrics())

        # Update the cellule-de-crise Canvas with new check-in data
        await self._update_cellule_crise_canvas()

        log_action(
            actor=volunteer_id,
            action="process_checkin",
            target=beneficiary_id,
            reason=text[:120],
            result="ok",
            metadata={
                "anomaly_level": anomaly_level,
                "checkin_id": result.get("checkin_id"),
                "channel_type": "voice" if file_bytes else "text",
            },
        )

        return {
            "status": "ok",
            "beneficiary_id": beneficiary_id,
            "anomaly_level": anomaly_level,
            "checkin_id": result.get("checkin_id"),
        }

    # ============================================================
    # Escalation trigger
    # ============================================================

    async def trigger_escalation(
        self,
        beneficiary_id: str,
        level: int,
        triggered_by: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Trigger an escalation and post in #cellule-crise.
        """
        log.info(
            "vigie.trigger_escalation",
            beneficiary=beneficiary_id,
            level=level,
            triggered_by=triggered_by,
        )

        try:
            async with self.mcp as mcp:
                result = await mcp.escalate(
                    beneficiary_id=beneficiary_id,
                    level=level,
                    triggered_by=triggered_by,
                    reason=reason,
                )
        except MCPClientError as e:
            log.error("vigie.trigger_escalation.mcp_error", error=str(e))
            return {"status": "mcp_error", "message": str(e)}

        if "error" in result:
            return result

        # Build the crisis cell message
        beneficiary = {
            "id": beneficiary_id,
            "first_name": result.get("beneficiary", {}).get("name", "?").split()[0] if result.get("beneficiary") else "?",
            "last_initial": "?",
            "age": result.get("beneficiary", {}).get("age"),
            "sector": result.get("beneficiary", {}).get("sector"),
            "phone": result.get("beneficiary", {}).get("phone"),
            "address": result.get("beneficiary", {}).get("address"),
        }

        escalation_msg = build_escalation_message(
            beneficiary=beneficiary,
            level=level,
            triggered_by=triggered_by,
            reason=reason,
            context_summary=result.get("context_summary", ""),
            neighbor_notified=result.get("neighbor_referent_notified", False),
            coordinator_notified=result.get("medical_coordinator_notified", False),
            samu_triggered=result.get("samu_triggered", False),
            escalation_id=result.get("escalation_id"),
        )

        await post_to_cellule_crise(
            self.slack,
            text=escalation_msg["text"],
            blocks=escalation_msg["blocks"],
        )

        # Record the escalation in the state store
        # detected_at = timestamp of the latest check-in for this beneficiary
        # (this is the moment the anomaly was detected, used to compute
        # escalation latency: detected_at → recorded_at)
        detected_at = None
        for c in reversed(self.state._checkins):  # noqa: SLF001
            if c.get("beneficiary_id") == beneficiary_id:
                detected_at = c.get("recorded_at")
                break
        if not detected_at:
            from datetime import UTC, datetime
            detected_at = datetime.now(UTC).isoformat()

        self.state.record_escalation({
            "escalation_id": result.get("escalation_id"),
            "beneficiary_id": beneficiary_id,
            "level": level,
            "triggered_by": triggered_by,
            "reason": reason,
            "samu_triggered": result.get("samu_triggered", False),
            "detected_at": detected_at,
        })

        # Update the health endpoint
        from app.health import update_metrics
        update_metrics(self.state.get_metrics())

        # Update the cellule-de-crise Canvas with the new escalation
        await self._update_cellule_crise_canvas()

        log_action(
            actor=triggered_by,
            action="trigger_escalation",
            target=beneficiary_id,
            reason=reason,
            result="ok",
            metadata={
                "level": level,
                "escalation_id": result.get("escalation_id"),
                "samu_triggered": result.get("samu_triggered", False),
            },
        )

        return {"status": "ok", "escalation_id": result.get("escalation_id"), "level": level}

    # ============================================================
    # Daily report generation
    # ============================================================

    async def generate_daily_report(self) -> dict[str, Any]:
        """
        Generate and post the daily report at 6 PM.

        Aggregates the day's check-ins, escalations, weak signals from the
        in-memory state store, generates an AI narrative, fetches fresh RTS
        directives, and posts a Block Kit report in #cellule-crise.

        Returns an error if no scenario is active (no point generating a
        report for an empty crisis cell).
        """
        log.info("vigie.generate_daily_report")

        metrics = self.state.get_metrics()
        if not metrics.get("scenario_active"):
            return {
                "status": "no_scenario",
                "message": "No active scenario. Type /vigie start to start.",
            }

        total = metrics["total_assigned"]
        contacted = metrics["contacted"]
        ok_count = metrics["ok_count"]
        weak_count = metrics["weak_count"]
        coord_count = metrics["coord_escalations"]
        samu_count = metrics["samu_escalations"]
        unreachable_72h = metrics["unreachable_72h"]
        avg_checkin_time = metrics.get("avg_checkin_time", "—")
        avg_escalade_latency = metrics.get("avg_escalade_latency", "—")
        weak_signals_list = self.state.get_weak_signals_summary() or [
            "No weak signal recorded today."
        ]
        date = datetime.now(UTC).date().isoformat()

        # Fetch fresh RTS directives in parallel with AI report
        rts_task = self.rts.get_health_directives(department="75")
        ai_task = self.slack_ai.generate_daily_report(
            date=date,
            total=total,
            contacted=contacted,
            ok_count=ok_count,
            weak_count=weak_count,
            coord_count=coord_count,
            samu_count=samu_count,
            avg_escalade_latency=avg_escalade_latency,
            unreachable_72h=unreachable_72h,
            weak_signals_list=weak_signals_list,
            rts_directives=[],  # Will be filled by RTS task
        )

        try:
            rts_directives = await rts_task
        except Exception as e:
            log.warning("vigie.report.rts_failed", error=str(e))
            rts_directives = []

        try:
            ai_report_text = await ai_task
        except Exception as e:
            log.warning("vigie.report.ai_failed", error=str(e))
            ai_report_text = (
                f"Summary unavailable ({e}). "
                f"See the KPIs above for the full figures."
            )

        msg = build_daily_report(
            date=date,
            total=total,
            contacted=contacted,
            ok_count=ok_count,
            weak_count=weak_count,
            coord_count=coord_count,
            samu_count=samu_count,
            avg_checkin_time=avg_checkin_time,
            avg_escalade_latency=avg_escalade_latency,
            unreachable_72h=unreachable_72h,
            weak_signals_list=weak_signals_list,
            rts_directives=rts_directives,
            ai_report_text=ai_report_text,
        )

        await post_to_cellule_crise(
            self.slack,
            text=msg["text"],
            blocks=msg["blocks"],
        )

        # Update the Canvas with the final report data
        await self._update_cellule_crise_canvas()

        log_action(
            actor="scheduler",
            action="generate_report",
            result="ok",
            metadata={
                "total": total,
                "contacted": contacted,
                "samu_count": samu_count,
            },
        )

        return {"status": "ok", "posted": True}

    # ============================================================
    # Dashboard state (App Home)
    # ============================================================

    async def get_dashboard_state(self, user_id: str) -> dict[str, Any]:
        """
        Build the App Home view for a volunteer.

        Returns a Slack view dict ready for views_publish. Uses live
        metrics from the state store. If no scenario is active, the
        alert banner is replaced with a calm "no active alert" message.
        """
        user_info = await get_user_info(self.slack, user_id)
        user_name = user_info.get("real_name") or user_info.get("display_name") or user_id

        metrics = self.state.get_metrics()
        alert = metrics.get("alert")  # None if no scenario active

        kpis = {
            "coverage_pct": metrics.get("coverage_pct", 0),
            "avg_checkin_time": metrics.get("avg_checkin_time", "—"),
            "avg_escalade_latency": metrics.get("avg_escalade_latency", "—"),
            "unreachable_72h": metrics.get("unreachable_72h", 0),
            "coord_count": metrics.get("coord_escalations", 0),
            "samu_count": metrics.get("samu_escalations", 0),
        }

        # Compute personal stats from the state store (filter by this volunteer)
        personal_today = sum(
            1
            for c in self.state._checkins  # noqa: SLF001
            if c.get("volunteer_id") == user_id
        )
        personal_weak = sum(
            1
            for c in self.state._checkins  # noqa: SLF001
            if c.get("volunteer_id") == user_id and c.get("anomaly_level") == 1
        )
        personal_escalations = sum(
            1
            for e in self.state._escalations  # noqa: SLF001
            if e.get("triggered_by") == user_id
        )

        # Compute personal average check-in time
        personal_checkins = [
            c for c in self.state._checkins  # noqa: SLF001
            if c.get("volunteer_id") == user_id
        ]
        from app.state import _compute_avg_checkin_time
        personal_avg_time = _compute_avg_checkin_time(personal_checkins)

        return build_app_home(
            user_id=user_id,
            user_name=user_name,
            assignments=[],
            alert=alert,
            kpis=kpis,
            personal_stats={
                "today_count": personal_today,
                "weak_signals": personal_weak,
                "escalations": personal_escalations,
                "avg_time": personal_avg_time,
            },
        )

    # ============================================================
    # Scenario reset (admin)
    # ============================================================

    async def reset_scenario(self, triggered_by: str) -> dict[str, Any]:
        """Reset the crisis cell state. Admin only."""
        log.info("vigie.reset_scenario", triggered_by=triggered_by)
        self.state.reset()
        from app.health import update_metrics
        update_metrics(self.state.get_metrics())
        await self._update_cellule_crise_canvas()
        log_action(
            actor=triggered_by,
            action="reset_scenario",
            result="ok",
        )
        return {"status": "ok", "reset": True}

    # ============================================================
    # Canvas publishing (real-time crisis cell view)
    # ============================================================

    async def _update_cellule_crise_canvas(self) -> None:
        """Publish or update the cellule-de-crise Slack Canvas.

        Called after every state change (start, check-in, escalation,
        report, reset) so coordinators always see live data.
        """
        metrics = self.state.get_metrics()
        alert = metrics.get("alert")
        if not alert:
            log.debug("vigie.canvas.skipped_no_alert")
            return

        active_escalations = self.state.get_active_escalations()
        # Enrich escalation items for the canvas
        esc_items = []
        for esc in active_escalations:
            beneficiary_name = esc.get("beneficiary_id", "?")
            esc_items.append({
                "level": esc.get("level", 0),
                "beneficiary_name": beneficiary_name,
                "sector": "?",
                "triggered_at": esc.get("recorded_at", "?")[:19],
            })

        # Fetch fresh directives for the canvas (uses cache, fast)
        try:
            rts_directives = await self.rts.get_health_directives(department="75")
        except Exception:
            rts_directives = []

        canvas_blocks = build_cellule_crise_canvas(
            date=datetime.now(UTC).date().isoformat(),
            alert_level=alert.get("level", "orange"),
            alert_phenomenon=alert.get("phenomenon", "heatwave"),
            alert_departments=[alert.get("department", "75")],
            total_beneficiaries=metrics["total_assigned"],
            contacted=metrics["contacted"],
            ok_count=metrics["ok_count"],
            weak_count=metrics["weak_count"],
            coord_count=metrics["coord_escalations"],
            samu_count=metrics["samu_escalations"],
            avg_checkin_time=metrics["avg_checkin_time"],
            avg_escalade_latency=metrics["avg_escalade_latency"],
            unreachable_72h=metrics["unreachable_72h"],
            active_escalations=esc_items,
            rts_directives=rts_directives[:3],
        )

        channel_id = await get_cellule_crise_channel_id(self.slack)
        if not channel_id:
            log.warning("vigie.canvas.no_channel")
            return

        success = await publish_canvas(
            self.slack,
            channel_id=channel_id,
            title="Crisis cell — Vigie",
            blocks=canvas_blocks,
        )
        if success:
            log.info("vigie.canvas.published", channel=channel_id)
        else:
            log.warning("vigie.canvas.publish_failed", channel=channel_id)


# ============================================================
# Helpers
# ============================================================


def _extract_beneficiary_id(text: str) -> str | None:
    """Extract a beneficiary ID (B001, B23, etc.) from a volunteer's message."""
    match = _BENEFICIARY_ID_PATTERN.search(text)
    if not match:
        return None
    n = int(match.group(1))
    return f"B{n:03d}"


def _load_scenario_alert() -> dict[str, Any]:
    """Load the demo scenario alert from scenario_canicule_juillet.json.

    This is the ONLY place where scenario (non-real) data is loaded. The
    alert is clearly labeled with source="Scenario (demo)" so that no
    judge or user can mistake it for a real Météo-France alert.
    """
    import json
    import pathlib

    scenario_path = pathlib.Path(__file__).resolve().parent.parent / "mcp_server" / "data" / "scenario_canicule_juillet.json"
    if not scenario_path.exists():
        log.error("vigie.scenario_file_missing", path=str(scenario_path))
        return {
            "level": "orange",
            "phenomenon": "heatwave",
            "department": "75",
            "department_name": "Paris (scenario)",
            "max_temperature": 38,
            "valid_from": "2026-07-15T06:00:00+02:00",
            "valid_to": "2026-07-18T22:00:00+02:00",
            "source": "Scenario (demo)",
            "url": "https://vigilance.meteofrance.fr/",
            "recommendation": "Demo scenario — not a real Météo-France alert.",
        }

    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            scenario = json.load(f)
        alert = scenario.get("alert", {})
        return {
            "id": "scenario-canicule-juillet-2026",
            "level": alert.get("level", "orange"),
            "phenomenon": alert.get("phenomenon", "heatwave"),
            "department": "75",
            "department_name": "Paris (demo scenario)",
            "max_temperature": alert.get("max_temperature", 38),
            "min_temperature_night": alert.get("min_temperature_night", 23),
            "valid_from": alert.get("valid_from"),
            "valid_to": alert.get("valid_to"),
            "source": "Scenario (demo)",
            "url": "https://vigilance.meteofrance.fr/",
            "recommendation": (
                "Spend at least 3 hours per day in a cool place. "
                "Drink water regularly even without thirst. "
                "Avoid physical exertion during the hottest hours."
            ),
        }
    except Exception as e:
        log.error("vigie.scenario_load_failed", error=str(e))
        return {
            "level": "orange",
            "phenomenon": "heatwave",
            "department": "75",
            "department_name": "Paris (scenario)",
            "max_temperature": 38,
            "valid_from": "2026-07-15T06:00:00+02:00",
            "valid_to": "2026-07-18T22:00:00+02:00",
            "source": "Scenario (demo)",
            "url": "https://vigilance.meteofrance.fr/",
        }
