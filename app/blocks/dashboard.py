"""
Vigie — App Home dashboard builder.

The App Home is the volunteer's personal command center. It shows:
- Greeting with the volunteer's name
- Current weather alert banner
- Today's check-in assignments (compact)
- Real-time KPIs (crisis cell view)
- Quick actions (start calls, view crisis cell)
- Personal stats (today's progress)

Updated every time the volunteer opens the App Home tab.
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.dashboard")


def build_app_home(
    *,
    user_id: str,
    user_name: str | None = None,
    assignments: list[dict[str, Any]] | None = None,
    alert: dict[str, Any] | None = None,
    kpis: dict[str, Any] | None = None,
    personal_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the App Home view for a volunteer.

    Args:
        user_id: Slack user ID
        user_name: Volunteer's display name (greeting)
        assignments: List of today's assigned beneficiaries
        alert: Active weather alert dict (level, phenomenon, departments, ...)
        kpis: Crisis cell KPIs (coverage, latencies, counts)
        personal_stats: Volunteer's personal stats (today's count, weak signals)

    Returns a Slack view dict ready for `client.views_publish()`.
    """
    assignments = assignments or []
    kpis = kpis or {}
    personal_stats = personal_stats or {}
    first_name = (user_name or "").split()[0] or "volunteer"

    blocks: list[dict[str, Any]] = []

    # Header — warm, personal
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":wave: Hi {first_name}",
                "emoji": True,
            },
        }
    )

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"I'm Vigie — I help you watch over isolated elders during heatwaves.\n\n"
                    f"When there's a heatwave alert, I'll send you a list of people to call. "
                    f"You just click a button after each call. I handle the rest.\n\n"
                    f"_You're not alone in this. I'm here._ 💜"
                ),
            },
        }
    )

    # Alert banner
    if alert:
        level = alert.get("level", "?")
        phenomenon = alert.get("phenomenon", "heatwave")
        departments = alert.get("department_name") or ", ".join(alert.get("departments", []))
        max_temp = alert.get("max_temperature", "?")

        emoji = ":large_orange_circle:" if level == "orange" else ":red_circle:"
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{level} vigilance — {phenomenon}*\n"
                        f":round_pushpin: {departments}\n"
                        f":thermometer: Max forecast T°: *{max_temp}°C*\n"
                        f":clock1: Valid until: {alert.get('valid_to', '?')}"
                    ),
                },
            }
        )
    else:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":white_check_mark: *No active heatwave alert.* Your usual check-ins remain available.",
                },
            }
        )

    # Today's assignments
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":telephone_receiver: Your check-ins for today ({len(assignments)})",
                "emoji": True,
            },
        }
    )

    if assignments:
        for b in assignments[:5]:
            name = f"{b.get('first_name', '?')} {b.get('last_initial', '?')}."
            age = b.get("age", "?")
            sector = b.get("sector", "?")
            phone = b.get("phone", "?")
            status = b.get("status", "registered")
            status_emoji = {
                "registered": ":white_circle:",
                "being_checked": ":large_blue_circle:",
                "ok": ":large_green_circle:",
                "unreachable": ":large_yellow_circle:",
                "escalated": ":large_orange_circle:",
                "critical": ":red_circle:",
            }.get(status, ":white_circle:")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{status_emoji} *{name}* ({age} yrs, sector {sector})\n"
                            f":telephone: `{phone}` — `id: {b.get('id')}`"
                        ),
                    },
                }
            )

        if len(assignments) > 5:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"_... and {len(assignments) - 5} more. Details in the DM._"},
                }
            )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No check-ins assigned for today._"},
            }
        )

    # Crisis cell KPIs
    if kpis:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":bar_chart: Crisis cell — real-time view", "emoji": True},
            }
        )
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Coverage (< 2h)*\n{kpis.get('coverage_pct', '?')}%"},
                    {"type": "mrkdwn", "text": f"*Avg check-in time*\n{kpis.get('avg_checkin_time', '?')}"},
                    {"type": "mrkdwn", "text": f"*Escalation latency*\n{kpis.get('avg_escalade_latency', '?')}"},
                    {"type": "mrkdwn", "text": f"*Not contacted > 72h*\n{kpis.get('unreachable_72h', '?')}"},
                    {"type": "mrkdwn", "text": f"*Coord. escalations*\n{kpis.get('coord_count', '?')}"},
                    {"type": "mrkdwn", "text": f"*SAMU escalations*\n{kpis.get('samu_count', '?')}"},
                ],
            }
        )

    # Personal stats
    if personal_stats:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":bust_in_silhouette: Your statistics", "emoji": True},
            }
        )
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Check-ins completed today*\n{personal_stats.get('today_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Weak signals detected*\n{personal_stats.get('weak_signals', 0)}"},
                    {"type": "mrkdwn", "text": f"*Escalations triggered*\n{personal_stats.get('escalations', 0)}"},
                    {"type": "mrkdwn", "text": f"*Avg time (your check-ins)*\n{personal_stats.get('avg_time', '?')}"},
                ],
            }
        )

    # Quick actions
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":telephone_receiver: Start my calls", "emoji": True},
                    "action_id": "vigie_start_calls",
                    "style": "primary",
                    "value": user_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":memo: My past check-ins", "emoji": True},
                    "action_id": "vigie_view_my_checkins",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":rotating_light: Crisis cell", "emoji": True},
                    "action_id": "vigie_view_cellule_crise",
                },
            ],
        }
    )

    # Footer
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_Vigie — So the heatwave no longer kills in silence._"},
                {"type": "mrkdwn", "text": "In case of life-threatening emergency, call *15* or *112*."},
            ],
        }
    )

    return {"type": "home", "blocks": blocks}
