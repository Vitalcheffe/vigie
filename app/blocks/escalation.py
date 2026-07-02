"""
Vigie — Block Kit builders for escalation messages.

Messages posted in #cellule-crise when an escalation is triggered.
Level 3 (SAMU) escalations include a prominent "Appeler le 15" button.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.escalation")

LEVEL_LABELS = {
    1: ("Signal faible", ":large_yellow_circle:"),
    2: ("Escalade coordinateur", ":large_orange_circle:"),
    3: ("Critique — SAMU", ":red_circle:"),
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
                "text": f"{emoji} ESCALADE NIVEAU {level} — {name}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*{age} ans* — secteur {sector} — `id: {beneficiary.get('id')}`"},
                {"type": "mrkdwn", "text": f"Déclenchée par <@{triggered_by}>"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":round_pushpin: *Adresse :* {address_str}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":telephone: *Téléphone :* `{phone}`"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":brain: *Contexte (synthèse Vigie) :*\n> {context_summary}"},
        },
    ]

    if reason:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":memo: *Motif :* {reason}"},
            }
        )

    blocks.append({"type": "divider"})

    # Actions taken
    actions_taken = []
    if samu_triggered:
        actions_taken.append(":rotating_light: Protocole SAMU déclenché — bouton « Appeler le 15 » ci-dessous")
    if coordinator_notified:
        actions_taken.append(":medical_symbol: Coordinateur médical notifié par DM")
    if neighbor_notified:
        actions_taken.append(":house: Voisin référent notifié par DM")
    if not actions_taken:
        actions_taken.append(":eyes: Surveillance renforcée activée")

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Actions effectuées :*\n" + "\n".join(f"  • {a}" for a in actions_taken),
            },
        }
    )

    # Procedure
    if level == 3:
        procedure = [
            "1. Appeler le *15 (SAMU)* immédiatement — bouton ci-dessous",
            "2. Si possible, envoyer un voisin sur place en attendant",
            "3. Rester en ligne avec le SAMU jusqu'à l'arrivée des secours",
            "4. Documenter l'heure d'arrivée des secours dans ce thread",
        ]
    elif level == 2:
        procedure = [
            "1. Le coordinateur médical prend contact dans les *15 minutes*",
            "2. Évaluer la nécessité d'une visite à domicile",
            "3. Si aggravation → cliquer « Escalader SAMU » ci-dessous",
        ]
    else:
        procedure = [
            "1. Surveillance renforcée (check-in toutes les 2h)",
            "2. Si aggravation → cliquer « Escalader coordinateur » ci-dessous",
        ]

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Procédure :*\n" + "\n".join(procedure),
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
                "text": {"type": "plain_text", "text": ":rotating_light: Appeler le 15 (SAMU)", "emoji": True},
                "style": "danger",
                "action_id": "vigie_call_samu",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "escalation_id": escalation_id or ""}),
            }
        )

    if level < 3:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalader SAMU", "emoji": True},
                "style": "danger",
                "action_id": "vigie_escalate_3",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "level": 3}),
            }
        )
    if level < 2:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalader coordinateur", "emoji": True},
                "action_id": "vigie_escalate_2",
                "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "level": 2}),
            }
        )

    actions.append(
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Marquer résolu", "emoji": True},
            "style": "primary",
            "action_id": "vigie_resolve_escalation",
            "value": json.dumps({"beneficiary_id": beneficiary.get("id"), "escalation_id": escalation_id or ""}),
        }
    )

    blocks.append({"type": "actions", "elements": actions})

    return {
        "blocks": blocks,
        "text": f"ESCALADE NIVEAU {level} — {name}",
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
