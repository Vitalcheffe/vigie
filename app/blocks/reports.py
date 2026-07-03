"""
Vigie — Block Kit builder for the daily report (posted at 6 PM in #cellule-crise).

The report aggregates the day's check-ins, escalations, weak signals,
and cites fresh health directives from the Real-Time Search API.
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.reports")


def build_daily_report(
    *,
    date: str,
    total: int,
    contacted: int,
    ok_count: int,
    weak_count: int,
    coord_count: int,
    samu_count: int,
    avg_checkin_time: str,
    avg_escalade_latency: str,
    unreachable_72h: int,
    weak_signals_list: list[str],
    rts_directives: list[dict[str, Any]],
    ai_report_text: str,
) -> dict[str, Any]:
    """
    Build the daily Vigie report Block Kit message.

    Layout:
      - Header with date
      - KPI section (5 metrics in a grid-like layout)
      - AI-generated narrative report
      - RTS directives (cited with sources)
      - Footer with disclaimer
    """
    coverage_pct = int((contacted / total) * 100) if total > 0 else 0
    samu_emoji = ":red_circle:" if samu_count > 0 else ":white_check_mark:"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":memo: Vigie daily report — {date}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Auto-generated at 6:00 PM • Slack AI + Real-Time Search API"},
            ],
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 Today's indicators", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Coverage (< 2h)*\n:large_green_circle: *{coverage_pct}%* ({contacted}/{total})"},
                {"type": "mrkdwn", "text": f"*Avg check-in time*\n:stopwatch: *{avg_checkin_time}*"},
                {"type": "mrkdwn", "text": f"*Escalation latency*\n:stopwatch: *{avg_escalade_latency}*"},
                {"type": "mrkdwn", "text": f"*Not contacted > 72h*\n:warning: *{unreachable_72h}*"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Check-in OK*\n:large_green_circle: *{ok_count}*"},
                {"type": "mrkdwn", "text": f"*Weak signals*\n:large_yellow_circle: *{weak_count}*"},
                {"type": "mrkdwn", "text": f"*Coordinator escalations*\n:large_orange_circle: *{coord_count}*"},
                {"type": "mrkdwn", "text": f"*SAMU escalations*\n{samu_emoji} *{samu_count}*"},
            ],
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":brain: Summary (Slack AI)", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": ai_report_text},
        },
    ]

    if weak_signals_list:
        signals_text = "\n".join(f"  • {s}" for s in weak_signals_list)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":eyes: *Weak signals to monitor tomorrow:*\n{signals_text}"},
            }
        )

    if rts_directives:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":globe_with_meridians: Fresh health directives", "emoji": True},
            }
        )
        for d in rts_directives[:3]:
            source = d.get("source", "?")
            title = d.get("title", "")
            summary = d.get("summary", "")
            url = d.get("url", "")
            published = d.get("published_at", "")
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{title}*\n"
                            f":newspaper: {source}"
                            + (f" — {published}" if published else "")
                            + (f"\n<{url}|Link>" if url else "")
                            + (f"\n> {summary}" if summary else "")
                        ),
                    },
                }
            )

    # Impact section — human stories, not just numbers
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":purple_heart: Today's impact", "emoji": True},
        }
    )

    impact_parts = []
    if ok_count > 0:
        impact_parts.append(f":white_check_mark: *{ok_count} elders* heard a friendly voice today. They know someone is watching over them.")
    if weak_count > 0:
        impact_parts.append(f":warning: *{weak_count} weak signals* caught early — a volunteer noticed something before it became an emergency.")
    if samu_count > 0:
        impact_parts.append(f":rotating_light: *{samu_count} critical escalations* — someone may have been saved because a volunteer acted fast.")
    if coord_count > 0:
        impact_parts.append(f":medical_symbol: *{coord_count} medical coordinator interventions* — a professional was alerted in time.")
    if coverage_pct >= 80:
        impact_parts.append(f":tada: *{coverage_pct}% coverage* — nearly every isolated elder was contacted within 2 hours.")
    elif coverage_pct >= 50:
        impact_parts.append(f":heart: *{coverage_pct}% coverage* — more than half reached. Every call matters.")
    
    if not impact_parts:
        impact_parts.append(":seedling: Today was quiet. The watch continues. Every day without a crisis is a victory.")

    impact_text = "\n".join(impact_parts)
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": impact_text},
        }
    )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_Vigie — So the heatwave no longer kills in silence._"},
                {"type": "mrkdwn", "text": f"_{contacted} check-ins completed by {total - unreachable_72h} volunteers. Every number here is a person._"},
                {"type": "mrkdwn", "text": "Simulated data — no real beneficiary is used in this demo."},
            ],
        }
    )

    return {
        "blocks": blocks,
        "text": f"Vigie report {date} — {coverage_pct}% coverage, {samu_count} SAMU",
    }
