"""
Vigie — Block Kit builders for escalation messages.

Messages posted in #cellule-crise when an escalation is triggered.
Level 3 (SAMU) escalations include a prominent "Call 15" button.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.escalation")

LEVEL_LABELS = {
    1: ("Weak signal — watching closely", ":large_yellow_circle:"),
    2: ("Needs medical coordinator", ":large_orange_circle:"),
    3: ("CRITICAL — SAMU needed", ":red_circle:"),
}


def build_escalation_message(
    *,
    beneficiary: dict[str, Any],
    level: int,
    triggered_by: str,
    reason: str | None,
    context_summary: str,
    neighbor_notified: bool,
    coordinator_notified: bool,
    samu_triggered: bool,
    escalation_id: str | None = None,
) -> dict[str, Any]:
    """
    Build the #cellule-crise message for an escalation.

    Layout:
      - Header with level emoji + beneficiary name
      - Triggered-by context
      - Context summary (Slack AI generated)
      - Reason (if manual)
      - Actions taken checklist
      - Procedure to follow
      - Action buttons (call SAMU for L3, mark as resolved, view full context)
    """
    label, emoji = LEVEL_LABELS.get(level, ("?", ":white_circle:"))
    name = f"{beneficiary.get('first_name', '?')} {beneficiary.get('last_initial', '?')}."
    age = beneficiary.get("age", "?")
    sector = beneficiary.get("sector", "?")
    phone = beneficiary.get("phone", "?")
    address = beneficiary.get("address", {})
    address_str = ""
    if isinstance(address, dict):
        address_str = ", ".join(
            str(v) for v in [
                address.get("street"),
                address.get("postal_code"),
                address.get("city"),
            ] if v
        )

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {name} needs help — {label}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{age} years old — sector {sector}"},
                {"type": "mrkdwn", "text": f"Alerted by <@{triggered_by}>"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":round_pushpin: *Address:* {address_str}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":telephone: *Phone:* `{phone}`"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":brain: *Context (Vigie summary):*\n> {context_summary}"},
        },
    ]

    if reason:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":memo: *Reason:* {reason}"},
            }
        )

    blocks.append({"type": "divider"})

    # Actions taken
    actions_taken = []
    if samu_triggered:
        actions_taken.append(":rotating_light: SAMU protocol triggered — \"Call 15\" button below")
    if coordinator_notified:
        actions_taken.append(":medical_symbol: Medical coordinator notified by DM")
    if neighbor_notified:
        actions_taken.append(":house: Neighbor referent notified by DM")
    if not actions_taken:
        actions_taken.append(":eyes: Enhanced monitoring activated")

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Actions taken:*\n" + "\n".join(f"  • {a}" for a in actions_taken),
            },
        }
    )

    # Procedure — clear, calm, actionable
    if level == 3:
        procedure = [
            "1. :rotating_light: Call *15 (SAMU)* now — use the button below",
            "2. If you can, ask a neighbor to go check on them while waiting",
            "3. Stay on the line with SAMU until help arrives",
            "4. Post the arrival time in this thread when emergency services get there",
        ]
    elif level == 2:
        procedure = [
            "1. The medical coordinator will reach out within *15 minutes*",
            "2. They'll decide if a home visit is needed",
            "3. If the situation gets worse, click \"Escalate to SAMU\" below",
        ]
    else:
        procedure = [
            "1. I'll keep a close eye on them — check-in every 2 hours",
            "2. If things change, click \"Escalate to coordinator\" below",
        ]

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Procedure:*\n" + "\n".join(procedure),
            },
        }
    )

    blocks.append({"type": "divider"})

    # Buttons
    actions: list[dict[str, Any]] = []
    if samu_triggered:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": ":rotating_light: Call 15 (SAMU)", "emoji": True},
                "style": "danger",
                "action_id": "vigie_call_samu",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "escalation_id": escalation_id or ""}),
            }
        )

    if level < 3:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalate to SAMU", "emoji": True},
                "style": "danger",
                "action_id": "vigie_escalate_3",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "level": 3}),
            }
        )
    if level < 2:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalate to coordinator", "emoji": True},
                "action_id": "vigie_escalate_2",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "level": 2}),
            }
        )

    actions.append(
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Mark as resolved", "emoji": True},
            "style": "primary",
            "action_id": "vigie_resolve_escalation",
            "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "escalation_id": escalation_id or ""}),
        }
    )

    blocks.append({"type": "actions", "elements": actions})

    return {
        "blocks": blocks,
        "text": f"ESCALATION LEVEL {level} — {name}",
    }


def build_escalation_thread_reply(
    *,
    escalation_id: str,
    update_type: str,
    author: str,
    message: str,
) -> dict[str, Any]:
    """Build a thread reply for an escalation update (e.g., SAMU arrived)."""
    icon = {
        "samu_arrived": ":ambulance:",
        "neighbor_check": ":house:",
        "resolved": ":white_check_mark:",
        "aggravation": ":red_circle:",
    }.get(update_type, ":memo:")

    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{update_type.replace('_', ' ').title()}* — <@{author}>\n> {message}",
                },
            }
        ],
        "text": f"{icon} {update_type}",
        "metadata": {
            "event_type": "vigie_escalation_update",
            "event_payload": {"escalation_id": escalation_id, "update_type": update_type},
        },
    }
