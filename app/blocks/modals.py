"""
Vigie — Modal view builders.

Builds the Slack view payloads for structured-data modals:
  - vigie_modal_checkin   : volunteer submits a structured check-in
  - vigie_modal_anomaly   : user submits an anomaly report
  - vigie_modal_reassign  : user submits a reassignment
  - vigie_modal_escalate  : user submits manual escalation details
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.modals")


def build_checkin_modal(
    beneficiary_id: str,
    beneficiary_name: str,
    sector: str | int | None = None,
) -> dict[str, Any]:
    """Modal for a volunteer to submit a structured check-in."""
    private_metadata = f"checkin:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_checkin",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Beneficiary check-in", "emoji": True},
        "submit": {"type": "plain_text", "text": "Save", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Beneficiary:* {beneficiary_name} (`{beneficiary_id}`)\n"
                        + (f"*Sector:* {sector}\n" if sector else "")
                        + "Report the observed state after your phone call."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "state_block",
                "label": {"type": "plain_text", "text": "General state"},
                "element": {
                    "type": "static_select",
                    "action_id": "state",
                    "placeholder": {"type": "plain_text", "text": "Select a state"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "OK — doing well"}, "value": "ok"},
                        {"text": {"type": "plain_text", "text": "Weak signal (fatigue, medication...)"}, "value": "weak"},
                        {"text": {"type": "plain_text", "text": "Unreachable (3 calls unanswered)"}, "value": "unreachable"},
                        {"text": {"type": "plain_text", "text": "Confused / disoriented"}, "value": "confused"},
                        {"text": {"type": "plain_text", "text": "Critical (on the ground, unconscious...)"}, "value": "critical"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "notes_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Notes (free observations)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "e.g. Mrs. Dupont tired, asking for antihypertensive prescription renewal."},
                },
            },
            {
                "type": "input",
                "block_id": "action_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Recommended action"},
                "element": {
                    "type": "static_select",
                    "action_id": "action",
                    "placeholder": {"type": "plain_text", "text": "Let Vigie decide"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "None (close)"}, "value": "ok"},
                        {"text": {"type": "plain_text", "text": "Find a pharmacy"}, "value": "pharmacy"},
                        {"text": {"type": "plain_text", "text": "Contact neighbor referent"}, "value": "neighbor"},
                        {"text": {"type": "plain_text", "text": "Escalate to medical coordinator"}, "value": "coord"},
                        {"text": {"type": "plain_text", "text": "Escalate to SAMU (15)"}, "value": "samu"},
                    ],
                },
            },
        ],
    }


def build_anomaly_modal(trigger_message_ts: str, trigger_channel: str) -> dict[str, Any]:
    """Modal for the 'Report an anomaly' shortcut."""
    private_metadata = f"anomaly:{trigger_channel}:{trigger_message_ts}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_anomaly",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Report an anomaly", "emoji": True},
        "submit": {"type": "plain_text", "text": "Send", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Describe the observed anomaly. Vigie will analyze it and suggest an action.",
                },
            },
            {
                "type": "input",
                "block_id": "beneficiary_block",
                "label": {"type": "plain_text", "text": "Beneficiary ID (e.g. B023)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "beneficiary_id",
                    "placeholder": {"type": "plain_text", "text": "B023"},
                },
            },
            {
                "type": "input",
                "block_id": "level_block",
                "label": {"type": "plain_text", "text": "Estimated severity level"},
                "element": {
                    "type": "static_select",
                    "action_id": "level",
                    "options": [
                        {"text": {"type": "plain_text", "text": "Weak signal (level 1)"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "Coordinator escalation (level 2)"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "Critical SAMU (level 3)"}, "value": "3"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "label": {"type": "plain_text", "text": "Reason / observation"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                    "multiline": True,
                },
            },
        ],
    }


def build_reassign_modal(beneficiary_id: str) -> dict[str, Any]:
    """Modal for reassigning a beneficiary to another volunteer."""
    private_metadata = f"reassign:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_reassign",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Reassign beneficiary", "emoji": True},
        "submit": {"type": "plain_text", "text": "Reassign", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Reassign `{beneficiary_id}` to another volunteer.",
                },
            },
            {
                "type": "input",
                "block_id": "volunteer_block",
                "label": {"type": "plain_text", "text": "Slack ID of the new volunteer (e.g. U12345)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "volunteer_id",
                    "placeholder": {"type": "plain_text", "text": "U12345"},
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Reason (optional)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                },
            },
        ],
    }


def build_escalate_modal(beneficiary_id: str) -> dict[str, Any]:
    """Modal for manual escalation with custom reason."""
    private_metadata = f"escalate:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_escalate",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Manual escalation", "emoji": True},
        "submit": {"type": "plain_text", "text": "Confirm escalation", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":rotating_light: You are about to trigger an escalation for `{beneficiary_id}`.",
                },
            },
            {
                "type": "input",
                "block_id": "level_block",
                "label": {"type": "plain_text", "text": "Escalation level"},
                "element": {
                    "type": "static_select",
                    "action_id": "level",
                    "options": [
                        {"text": {"type": "plain_text", "text": "1 — Weak signal (enhanced monitoring)"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "2 — Medical coordinator"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "3 — Critical SAMU (15)"}, "value": "3"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "label": {"type": "plain_text", "text": "Detailed reason"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Describe the observed situation."},
                },
            },
        ],
    }
