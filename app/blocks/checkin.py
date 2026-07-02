"""
Vigie — Block Kit builders for check-in messages.

These functions produce the Slack Block Kit JSON for messages posted
in sector channels (#secteur-N) after each volunteer check-in.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.checkin")

# Slack color codes for the anomaly levels (used in attachments/sections)
ANOMALY_VISUALS = {
    0: {"emoji": ":large_green_circle:", "label": "OK", "color": "#2EB67D"},
    1: {"emoji": ":large_yellow_circle:", "label": "Signal faible", "color": "#ECB22E"},
    2: {"emoji": ":large_orange_circle:", "label": "Escalade coordinateur", "color": "#E01E5A"},
    3: {"emoji": ":red_circle:", "label": "Critique — SAMU", "color": "#E01E5A"},
}


def build_checkin_message(
    *,
    beneficiary: dict[str, Any],
    volunteer_id: str,
    transcript: str,
    anomaly_level: int,
    signals: list[str],
    recommended_action: str,
    suggested_pois: list[dict[str, Any]] | None = None,
    checkin_id: str | None = None,
) -> dict[str, Any]:
    """
    Build the Block Kit message for a sector channel after a check-in.

    The message includes:
      - Header with beneficiary name, age, sector, anomaly emoji
      - The volunteer's note (quoted)
      - Detected signals (badges)
      - Suggested POIs (if any, with distance)
      - Action buttons: Confirm POI / Escalade L2 / Escalade L3 / Close

    The button value carries the beneficiary_id so the action handler
    can route the callback to the MCP server.
    """
    poi_list = suggested_pois or []
    visual = ANOMALY_VISUALS.get(anomaly_level, ANOMALY_VISUALS[0])
    beneficiary_id = beneficiary.get("id", "?")
    name = f"{beneficiary.get('first_name', '?')} {beneficiary.get('last_initial', '?')}."
    age = beneficiary.get("age", "?")
    sector = beneficiary.get("sector", "?")

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{visual['emoji']} Check-in — {name}, {age} ans, secteur {sector}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Bénévole : <@{volunteer_id}>_"},
                {"type": "mrkdwn", "text": f"• Niveau : *{visual['label']}*"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"> {transcript}"},
        },
    ]

    if signals:
        badges = " ".join(f"`{s}`" for s in signals)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Signaux détectés :* {badges}"},
            }
        )

    if poi_list:
        poi_text = "\n".join(
            f"  • *{p.get('name', '?')}* — {p.get('type', '?')}"
            + (f" ({p['distance_m']:.0f} m)" if p.get("distance_m") else "")
            + (f" — `{p.get('opening_hours', '?')}`" if p.get("opening_hours") else "")
            for p in poi_list[:3]
        )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*POIs à proximité :*\n{poi_text}"},
            }
        )

    blocks.append({"type": "divider"})

    # Action buttons — values are JSON-encoded so the handler can parse them
    actions: list[dict[str, Any]] = []

    if recommended_action == "pharmacy" and poi_list:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Confirmer pharmacie", "emoji": True},
                "style": "primary",
                "action_id": "vigie_confirm_pharmacy",
                "value": json.dumps({"beneficiary_id": beneficiary_id, "poi_id": poi_list[0].get("id")}),
            }
        )

    if anomaly_level >= 1:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalader coordinateur", "emoji": True},
                "action_id": "vigie_escalate_2",
                "value": json.dumps({"beneficiary_id": beneficiary_id, "level": 2}),
                "style": "danger",
            }
        )

    if anomaly_level >= 1:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": ":rotating_light: SAMU (15)", "emoji": True},
                "action_id": "vigie_escalate_3",
                "value": json.dumps({"beneficiary_id": beneficiary_id, "level": 3}),
                "style": "danger",
            }
        )

    # Always offer Close (level 0 closure)
    actions.append(
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Clôturer", "emoji": True},
            "action_id": "vigie_close_checkin",
            "value": json.dumps({"beneficiary_id": beneficiary_id, "checkin_id": checkin_id or ""}),
        }
    )

    blocks.append({"type": "actions", "elements": actions})

    return {
        "blocks": blocks,
        "text": f"Check-in {name} — {visual['label']}",
    }


def build_volunteer_dm(
    *,
    volunteer_id: str,
    volunteer_name: str,
    assignments: list[dict[str, Any]],
    alert_level: str = "orange",
    date: str,
) -> dict[str, Any]:
    """
    Build the DM message sent to a volunteer at 7:30 with their daily list.

    The DM contains:
      - Greeting + alert context
      - List of assigned beneficiaries (compact, with phone)
      - 'Démarrer les appels' button
    """
    visual = ":large_orange_circle:" if alert_level == "orange" else ":red_circle:"
    count = len(assignments)

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{visual} Bonjour {volunteer_name.split()[0]} — {count} check-in pour aujourd'hui",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Vigilance *{alert_level} canicule* active depuis ce matin 7h. "
                    f"Vous avez *{count} bénéficiaires* à contacter avant 14h. "
                    f"Date : *{date}*.\n\n"
                    "Après chaque appel, postez-moi une note (texte ou vocale) avec ce que vous avez observé. "
                    "Je m'occupe de l'analyse, des pharmacies, et des escalades."
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Votre liste du jour", "emoji": True},
        },
    ]

    for b in assignments:
        name = f"{b.get('first_name', '?')} {b.get('last_initial', '?')}."
        age = b.get("age", "?")
        sector = b.get("sector", "?")
        phone = b.get("phone", "?")
        vuln = b.get("vulnerability_score", 0)
        conditions = b.get("medical_conditions") or []
        meds = b.get("medications") or []

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{name}* ({age} ans, secteur {sector}) — `id: {b.get('id')}`\n"
                        f":telephone: `{phone}`\n"
                        f":heart: Vulnérabilité : *{vuln}/100*"
                        + (f" — Conditions : {', '.join(conditions)}" if conditions else "")
                        + (f"\n:pill: Traitements : {', '.join(meds)}" if meds else "")
                    ),
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Fiche complète", "emoji": True},
                    "action_id": "vigie_view_beneficiary",
                    "value": b.get("id", ""),
                },
            }
        )

    blocks.append({"type": "divider"})

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":telephone_receiver: Démarrer les appels", "emoji": True},
                    "style": "primary",
                    "action_id": "vigie_start_calls",
                    "value": json.dumps({"volunteer_id": volunteer_id, "date": date}),
                }
            ],
        }
    )

    return {
        "blocks": blocks,
        "text": f"Vigie — {count} check-in pour aujourd'hui",
    }
