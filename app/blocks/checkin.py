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
    1: {"emoji": ":large_yellow_circle:", "label": "Weak signal", "color": "#ECB22E"},
    2: {"emoji": ":large_orange_circle:", "label": "Coordinator escalation", "color": "#E01E5A"},
    3: {"emoji": ":red_circle:", "label": "Critical — SAMU", "color": "#E01E5A"},
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
                "text": f"{visual['emoji']} Check-in — {name}, {age} yrs, sector {sector}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Volunteer: <@{volunteer_id}>_"},
                {"type": "mrkdwn", "text": f"• Level: *{visual['label']}*"},
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
                "text": {"type": "mrkdwn", "text": f"*Detected signals:* {badges}"},
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
                "text": {"type": "mrkdwn", "text": f"*Nearby POIs:*\n{poi_text}"},
            }
        )

    blocks.append({"type": "divider"})

    # Action buttons — values are JSON-encoded so the handler can parse them
    actions: list[dict[str, Any]] = []

    if recommended_action == "pharmacy" and poi_list:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Confirm pharmacy", "emoji": True},
                "style": "primary",
                "action_id": "vigie_confirm_pharmacy",
                "value": json.dumps({"beneficiary_id": beneficiary_id, "poi_id": poi_list[0].get("id")}),
            }
        )

    if anomaly_level >= 1:
        actions.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalate to coordinator", "emoji": True},
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
            "text": {"type": "plain_text", "text": "Close", "emoji": True},
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
      - 'Start calls' button
    """
    visual = ":large_orange_circle:" if alert_level == "orange" else ":red_circle:"
    count = len(assignments)
    first_name = volunteer_name.split()[0] if volunteer_name else "there"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{visual} Hi {first_name}, you have {count} people to check on today",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"A *{alert_level} heatwave alert* is active. "
                    f"These {count} people are counting on a phone call from you before 2 PM.\n\n"
                    "After each call, just click the **Check-in** button next to their name. "
                    "You'll pick how they're doing from a few options — that's it. "
                    "I handle pharmacies, escalations, and everything else.\n\n"
                    "_Thank you for being here. Every call matters._ 💜"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Your list for today", "emoji": True},
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
        bid = b.get("id", "")

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{name}* ({age} yrs, sector {sector})\n"
                        f":telephone: `{phone}`\n"
                        f":heart: Vulnerability: *{vuln}/100*"
                        + (f" — Conditions: {', '.join(conditions)}" if conditions else "")
                        + (f"\n:pill: Treatments: {', '.join(meds)}" if meds else "")
                    ),
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Check-in", "emoji": True},
                    "action_id": "vigie_quick_checkin",
                    "style": "primary",
                    "value": json.dumps({"beneficiary_id": bid, "beneficiary_name": name}),
                },
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_Click \"Check-in\" next to each name after your call. No need to type anything._"},
            ],
        }
    )

    return {
        "blocks": blocks,
        "text": f"Vigie — {count} check-ins for today",
    }
