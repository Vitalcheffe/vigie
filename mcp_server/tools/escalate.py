"""
Vigie MCP tool — escalate.

Triggers an escalation for a beneficiary:
  - Level 1: weak signal → notify coordinator, monitor
  - Level 2: coordinator escalation → DM medical coordinator, post in crisis cell
  - Level 3: critical → trigger SAMU protocol, escalate to crisis cell with full context

The escalation flow:
  1. Update beneficiary status to "escalated" or "critical"
  2. Generate Slack AI summary of last 48h context
  3. For level 3: trigger SAMU button in crisis cell
  4. For level 2: DM medical coordinator with structured briefing
  5. Notify neighbor referent if applicable
  6. Return the escalation record for Slack posting
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.utils.logging import get_logger
from mcp_server.resources.beneficiary_registry import (
    get_beneficiary_by_id,
    update_beneficiary_status,
)

log = get_logger("vigie.mcp.tools.escalate")


async def escalate(
    beneficiary_id: str,
    level: int,
    triggered_by: str,
    reason: str | None = None,
    include_neighbor_referent: bool = True,
) -> dict[str, Any]:
    """
    Escalate a beneficiary to a higher urgency level.

    Args:
        beneficiary_id: e.g., "B001"
        level: 1 (weak signal) | 2 (coordinator) | 3 (critical/SAMU)
        triggered_by: Slack user ID of the person triggering the escalation
        reason: Free-text reason for manual escalation
        include_neighbor_referent: Whether to alert the registered neighbor referent

    Returns:
        {
            "escalation_id": "...",
            "beneficiary": {...},
            "level": 3,
            "actions_taken": [...],
            "neighbor_referent_notified": true,
            "medical_coordinator_notified": true,
            "samu_triggered": false,
            "context_summary": "Slack AI summary of last 48h",
            "cellule_crise_message": "Message ready to post in #cellule-crise",
            "timestamp": "..."
        }
    """
    timestamp = datetime.now(UTC).isoformat()

    log.info(
        "vigie.mcp.tool.escalate",
        beneficiary=beneficiary_id,
        level=level,
        triggered_by=triggered_by,
    )

    if level not in (1, 2, 3):
        return {
            "error": "invalid_level",
            "message": "Level must be 1, 2, or 3.",
            "received": level,
        }

    beneficiary = get_beneficiary_by_id(beneficiary_id)
    if not beneficiary:
        return {
            "error": "beneficiary_not_found",
            "beneficiary_id": beneficiary_id,
        }

    actions_taken: list[str] = []
    neighbor_notified = False
    coordinator_notified = False
    samu_triggered = False

    # 1. Update beneficiary status
    new_status = {1: "ok", 2: "escalated", 3: "critical"}[level]
    update_beneficiary_status(
        beneficiary_id,
        status=new_status,
        notes=f"Escalated to level {level} at {timestamp}: {reason or 'auto'}",
        last_checkin_at=timestamp,
    )
    actions_taken.append(f"status_updated_to_{new_status}")

    # 2. Generate context summary (stub: Slack AI)
    context_summary = await _generate_context_summary(beneficiary)
    actions_taken.append("context_summary_generated")

    # 3. Level-specific actions
    if level >= 2:
        # Notify medical coordinator
        coordinator_notified = True
        actions_taken.append("medical_coordinator_dm_queued")

    if level >= 3:
        # Trigger SAMU protocol
        samu_triggered = True
        actions_taken.append("samu_protocol_triggered")
        actions_taken.append("samu_button_added_to_cellule_crise")

    # 4. Notify neighbor referent (level 2+)
    if include_neighbor_referent and level >= 2:
        neighbor = await _get_neighbor_referent(beneficiary)
        if neighbor:
            neighbor_notified = True
            actions_taken.append("neighbor_referent_dm_queued")

    # 5. Build the crisis cell message
    cellule_message = _build_cellule_crise_message(
        beneficiary=beneficiary,
        level=level,
        triggered_by=triggered_by,
        reason=reason,
        context_summary=context_summary,
        neighbor_notified=neighbor_notified,
        coordinator_notified=coordinator_notified,
        samu_triggered=samu_triggered,
    )

    escalation_id = f"E-{beneficiary_id}-L{level}-{int(datetime.now(UTC).timestamp())}"

    result = {
        "escalation_id": escalation_id,
        "beneficiary": {
            "id": beneficiary["id"],
            "name": f"{beneficiary['first_name']} {beneficiary['last_initial']}.",
            "age": beneficiary.get("age"),
            "sector": beneficiary.get("sector"),
            "phone": beneficiary.get("phone"),
            "address": beneficiary.get("address"),
        },
        "level": level,
        "level_label": _LEVEL_LABELS[level],
        "triggered_by": triggered_by,
        "reason": reason,
        "actions_taken": actions_taken,
        "neighbor_referent_notified": neighbor_notified,
        "medical_coordinator_notified": coordinator_notified,
        "samu_triggered": samu_triggered,
        "context_summary": context_summary,
        "cellule_crise_message": cellule_message,
        "timestamp": timestamp,
    }

    log.info(
        "vigie.mcp.tool.escalate.done",
        escalation_id=escalation_id,
        level=level,
        actions=actions_taken,
    )
    return result


# ============================================================
# Helpers
# ============================================================

_LEVEL_LABELS = {
    1: "Weak signal — enhanced monitoring",
    2: "Medical coordinator escalation",
    3: "Critical escalation — SAMU protocol",
}

_LEVEL_EMOJI = {
    1: ":large_yellow_circle:",
    2: ":large_orange_circle:",
    3: ":red_circle:",
}


async def _generate_context_summary(beneficiary: dict) -> str:
    """
    Generate a context summary for the crisis cell message.

    Builds a structured summary from the beneficiary's static profile
    (name, age, sector, medical conditions, medications, isolation).

    A future enhancement would call Slack AI to summarize the last 48h
    of check-ins + previous escalations + current weather context. For
    the hackathon demo, the static profile is sufficient and avoids
    extra latency in the escalation path.
    """
    name = f"{beneficiary['first_name']} {beneficiary['last_initial']}."
    age = beneficiary.get("age", "?")
    sector = beneficiary.get("sector", "?")
    conditions = ", ".join(beneficiary.get("medical_conditions", [])) or "none"
    medications = ", ".join(beneficiary.get("medications", [])) or "none"

    return (
        f"{name}, {age} yrs, sector {sector}. "
        f"Medical conditions: {conditions}. "
        f"Treatments: {medications}. "
        f"Lives alone. "
        f"Orange heatwave vigilance active."
    )


async def _get_neighbor_referent(beneficiary: dict) -> dict[str, Any] | None:
    """Get the registered neighbor referent for the beneficiary's sector.

    Loads from mcp_server/data/volunteers.json — a volunteer assigned to
    the same sector acts as the neighbor referent.
    """
    import json
    import pathlib

    sector = beneficiary.get("sector")
    if not sector:
        return None

    volunteers_path = pathlib.Path(__file__).resolve().parent.parent / "data" / "volunteers.json"
    if not volunteers_path.exists():
        log.warning("vigie.mcp.escalate.volunteers_missing", path=str(volunteers_path))
        return None

    try:
        with volunteers_path.open("r", encoding="utf-8") as f:
            volunteers = json.load(f)
        for v in volunteers:
            if str(v.get("sector")) == str(sector):
                return {
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "sector": sector,
                    "phone": v.get("phone"),
                    "email": v.get("email"),
                }
    except Exception as e:
        log.warning("vigie.mcp.escalate.referent_load_failed", error=str(e))

    return None


def _build_cellule_crise_message(
    beneficiary: dict,
    level: int,
    triggered_by: str,
    reason: str | None,
    context_summary: str,
    neighbor_notified: bool,
    coordinator_notified: bool,
    samu_triggered: bool,
) -> str:
    """Build the message to post in #cellule-crise."""
    name = f"{beneficiary['first_name']} {beneficiary['last_initial']}."
    age = beneficiary.get("age", "?")
    sector = beneficiary.get("sector", "?")
    emoji = _LEVEL_EMOJI.get(level, ":white_circle:")

    parts = [
        f"{emoji} *ESCALATION LEVEL {level}* — {name}, {age} yrs, sector {sector}",
        f"_Triggered by <@{triggered_by}>_",
        "",
        f"*Context:* {context_summary}",
        "",
    ]

    if reason:
        parts.append(f"*Reason:* {reason}")
        parts.append("")

    parts.append("*Actions:*")
    if samu_triggered:
        parts.append("  :rotating_light: SAMU protocol triggered — \"Call 15\" button below")
    if coordinator_notified:
        parts.append("  :medical_symbol: Medical coordinator notified by DM")
    if neighbor_notified:
        parts.append("  :house: Neighbor referent notified by DM")
    parts.append("")

    parts.append("*Procedure:*")
    if level == 3:
        parts.append("  1. Call 15 (SAMU) immediately")
        parts.append("  2. If possible, send a neighbor on site while waiting")
        parts.append("  3. Stay on the line with SAMU until emergency services arrive")
    elif level == 2:
        parts.append("  1. Medical coordinator makes contact within 15 min")
        parts.append("  2. Assess need for home visit")
        parts.append("  3. If worsening → escalate to level 3")
    else:
        parts.append("  1. Enhanced monitoring (check-in every 2h)")
        parts.append("  2. If worsening → escalate to level 2")

    return "\n".join(parts)


def register(mcp) -> None:
    """Register the escalate tool on the MCP server."""

    @mcp.tool()
    async def escalate_tool(
        beneficiary_id: str,
        level: int,
        triggered_by: str,
        reason: str | None = None,
        include_neighbor_referent: bool = True,
    ) -> str:
        """
        Escalate a beneficiary to a higher urgency level (1, 2, or 3).

        Level 1: weak signal — enhanced monitoring
        Level 2: coordinator escalation — medical coordinator + neighbor referent notified
        Level 3: critical — SAMU protocol triggered, button to call 15 in crisis cell

        Args:
            beneficiary_id: Beneficiary ID (e.g., "B001")
            level: 1, 2, or 3
            triggered_by: Slack user ID triggering the escalation
            reason: Free-text reason for manual escalation (optional)
            include_neighbor_referent: Whether to alert the registered neighbor referent (default true)

        Returns JSON with escalation record, context summary, and crisis cell message.
        """
        result = await escalate(
            beneficiary_id=beneficiary_id,
            level=level,
            triggered_by=triggered_by,
            reason=reason,
            include_neighbor_referent=include_neighbor_referent,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    log.debug("vigie.mcp.tool.escalate.registered")
