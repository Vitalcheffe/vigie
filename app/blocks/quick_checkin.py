"""
Vigie — Quick check-in modal (human-friendly, no IDs to type).

When a volunteer clicks "Check-in" next to a beneficiary name in their DM,
this modal opens with:
  - The beneficiary's name pre-filled (no ID visible)
  - 4 big buttons: OK / Weak signal / Unreachable / Critical
  - A notes field (optional)

The volunteer just clicks a button and types a note. No IDs, no slash
commands, no technical jargon.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.quick_checkin")


def build_quick_checkin_modal(
    beneficiary_id: str,
    beneficiary_name: str,
    sector: str | int | None = None,
    age: int | None = None,
    phone: str | None = None,
) -> dict[str, Any]:
    """Build a human-friendly check-in modal.

    The volunteer sees the beneficiary's NAME, not their ID.
    They click one of 4 buttons + type optional notes. Done.
    """
    private_metadata = json.dumps({
        "beneficiary_id": beneficiary_id,
        "beneficiary_name": beneficiary_name,
    })

    info_text = f"*{beneficiary_name}*"
    if age:
        info_text += f" ({age} years old)"
    if sector:
        info_text += f"\n:round_pushpin: Sector {sector}"
    if phone:
        info_text += f"\n:telephone: `{phone}`"

    # Add a personal note if available
    import json as _json
    try:
        from pathlib import Path
        b_path = Path(__file__).resolve().parent.parent.parent / "mcp_server" / "data" / "beneficiaries.json"
        beneficiaries = _json.loads(b_path.read_text())
        for b in beneficiaries:
            if b.get("id") == beneficiary_id:
                backstory = b.get("backstory", "")
                if backstory:
                    info_text += f"\n\n:house: {backstory}"
                break
    except Exception:
        pass

    return {
        "type": "modal",
        "callback_id": "vigie_modal_checkin",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Check-in", "emoji": True},
        "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": info_text,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*How was the call?* Select the state:",
                },
            },
            {
                "type": "actions",
                "block_id": "state_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":white_check_mark: OK", "emoji": True},
                        "action_id": "vigie_state_ok",
                        "value": json.dumps({"beneficiary_id": beneficiary_id, "state": "ok"}),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":warning: Weak signal", "emoji": True},
                        "action_id": "vigie_state_weak",
                        "value": json.dumps({"beneficiary_id": beneficiary_id, "state": "weak"}),
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":no_entry: No answer", "emoji": True},
                        "action_id": "vigie_state_unreachable",
                        "value": json.dumps({"beneficiary_id": beneficiary_id, "state": "unreachable"}),
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":rotating_light: Critical", "emoji": True},
                        "action_id": "vigie_state_critical",
                        "value": json.dumps({"beneficiary_id": beneficiary_id, "state": "critical"}),
                        "style": "danger",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "notes_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Notes (what did you observe?)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., Mrs Dupont sounds tired, asks for medication renewal",
                    },
                },
            },
        ],
    }
