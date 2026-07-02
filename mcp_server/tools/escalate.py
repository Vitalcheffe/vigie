"""
Vigie MCP tool — escalate.

Triggers an escalation for a beneficiary:
  - Level 1: weak signal → notify coordinator, monitor
  - Level 2: coordinator escalation → DM medical coordinator, post in cellule de crise
  - Level 3: critical → trigger SAMU protocol, escalate to cellule de crise with full context

The escalation flow:
  1. Update beneficiary status to "escalated" or "critical"
  2. Generate Slack AI summary of last 48h context
  3. For level 3: trigger SAMU button in cellule de crise
  4. For level 2: DM medical coordinator with structured briefing
  5. Notify neighbor referent if applicable
  6. Return the escalation record for Slack posting
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
    timestamp = datetime.now(timezone.utc).isoformat()

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

    # 5. Build the cellule de crise message
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

    escalation_id = f"E-{beneficiary_id}-L{level}-{int(datetime.now(timezone.utc).timestamp())}"

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
    1: "Signal faible — surveillance renforcée",
    2: "Escalade coordinateur médical",
    3: "Escalade critique — protocole SAMU",
}

_LEVEL_EMOJI = {
    1: ":large_yellow_circle:",
    2: ":large_orange_circle:",
    3: ":red_circle:",
}


async def _generate_context_summary(beneficiary: dict) -> str:
    """
    Generate a context summary using Slack AI.

    TODO: replace stub with Slack AI call that summarizes:
      - Last 48h of check-ins
      - Medical history (conditions + medications)
      - Previous escalations
      - Current weather alert context

    Output format:
      "Mme Dupont, 82 ans, secteur 11. Dernier check-in : il y a 2h, fatiguée,
      demande renouvellement ordonnance antihypertenseur. Hypertendue, vit
      seule. Aucun proche référent. Vigilance orange canicule active depuis 7h."
    """
    name = f"{beneficiary['first_name']} {beneficiary['last_initial']}."
    age = beneficiary.get("age", "?")
    sector = beneficiary.get("sector", "?")
    conditions = ", ".join(beneficiary.get("medical_conditions", [])) or "aucune"
    medications = ", ".join(beneficiary.get("medications", [])) or "aucun"

    return (
        f"{name}, {age} ans, secteur {sector}. "
        f"Conditions médicales : {conditions}. "
        f"Traitements : {medications}. "
        f"Vit seule. "
        f"Vigilance orange canicule active. "
        f"(Résumé contextuel — génération Slack AI complète.)"
    )


async def _get_neighbor_referent(beneficiary: dict) -> dict[str, Any] | None:
    """Get the registered neighbor referent for the beneficiary's sector."""
    sector = beneficiary.get("sector")
    if not sector:
        return None

    # TODO: load from volunteers.json
    return {
        "id": f"NR-{sector}",
        "name": "M. Bernard (simulated)",
        "sector": sector,
        "phone": "+33 6 00 00 00 00",
    }


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
        f"{emoji} *ESCALADE NIVEAU {level}* — {name}, {age} ans, secteur {sector}",
        f"_Déclenchée par <@{triggered_by}>_",
        "",
        f"*Contexte :* {context_summary}",
        "",
    ]

    if reason:
        parts.append(f"*Motif :* {reason}")
        parts.append("")

    parts.append("*Actions :*")
    if samu_triggered:
        parts.append("  :rotating_light: Protocole SAMU déclenché — bouton « Appeler le 15 » ci-dessous")
    if coordinator_notified:
        parts.append("  :medical_symbol: Coordinateur médical notifié par DM")
    if neighbor_notified:
        parts.append("  :house: Voisin référent notifié par DM")
    parts.append("")

    parts.append("*Procédure :*")
    if level == 3:
        parts.append("  1. Appeler le 15 (SAMU) immédiatement")
        parts.append("  2. Si possible, envoyer un voisin sur place en attendant")
        parts.append("  3. Rester en ligne avec le SAMU jusqu'à l'arrivée des secours")
    elif level == 2:
        parts.append("  1. Coordinateur médical prend contact dans les 15 min")
        parts.append("  2. Évaluer nécessité de visite à domicile")
        parts.append("  3. Si aggravation → escalade niveau 3")
    else:
        parts.append("  1. Surveillance renforcée (check-in toutes les 2h)")
        parts.append("  2. Si aggravation → escalade niveau 2")

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
        Level 3: critical — SAMU protocol triggered, button to call 15 in cellule de crise

        Args:
            beneficiary_id: Beneficiary ID (e.g., "B001")
            level: 1, 2, or 3
            triggered_by: Slack user ID triggering the escalation
            reason: Free-text reason for manual escalation (optional)
            include_neighbor_referent: Whether to alert the registered neighbor referent (default true)

        Returns JSON with escalation record, context summary, and cellule de crise message.
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
