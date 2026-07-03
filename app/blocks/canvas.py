"""
Vigie — Canvas builder for the #cellule-crise real-time view.

Slack Canvas is the persistent, structured document surface where we
publish the live state of the crisis cell: alert level, coverage,
active escalations, today's KPIs. Updated every 5 minutes during alert.
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.canvas")


def build_cellule_crise_canvas(
    *,
    date: str,
    alert_level: str,
    alert_phenomenon: str,
    alert_departments: list[str],
    total_beneficiaries: int,
    contacted: int,
    ok_count: int,
    weak_count: int,
    coord_count: int,
    samu_count: int,
    avg_checkin_time: str,
    avg_escalade_latency: str,
    unreachable_72h: int,
    active_escalations: list[dict[str, Any]] | None = None,
    rts_directives: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build the document content for the crisis cell Slack Canvas.

    Returns a list of Canvas blocks (Slack document_markdown format).

    The Canvas is updated every 5 minutes during an active alert. It is
    the single source of truth that coordinators glance at throughout the day.
    """
    coverage_pct = int((contacted / total_beneficiaries) * 100) if total_beneficiaries > 0 else 0
    escalations = active_escalations or []
    directives = rts_directives or []

    blocks: list[dict[str, Any]] = []

    # Title
    blocks.append(
        {
            "type": "heading",
            "level": 1,
            "text": f"Crisis cell — Vigie — {date}",
        }
    )

    # Alert banner
    alert_emoji = ":large_orange_circle:" if alert_level == "orange" else ":red_circle:"
    deps_str = ", ".join(alert_departments) if alert_departments else "—"
    blocks.append(
        {
            "type": "callout",
            "style": "warning" if alert_level == "orange" else "error",
            "text": f"{alert_emoji} *{alert_level} vigilance — {alert_phenomenon}*\nDepartments: {deps_str}",
        }
    )

    # KPI section
    blocks.append({"type": "heading", "level": 2, "text": "Real-time indicators"})
    blocks.append(
        {
            "type": "bulleted_list",
            "elements": [
                {"type": "text", "text": f"*Coverage (< 2h)*: {coverage_pct}% ({contacted}/{total_beneficiaries})"},
                {"type": "text", "text": f"*Avg check-in time*: {avg_checkin_time}"},
                {"type": "text", "text": f"*Escalation latency*: {avg_escalade_latency}"},
                {"type": "text", "text": f"*Check-in OK*: {ok_count}"},
                {"type": "text", "text": f"*Weak signals*: {weak_count}"},
                {"type": "text", "text": f"*Coordinator escalations*: {coord_count}"},
                {"type": "text", "text": f"*SAMU escalations*: {samu_count}"},
                {"type": "text", "text": f"*Not contacted > 72h*: {unreachable_72h}"},
            ],
        }
    )

    # Active escalations
    blocks.append({"type": "heading", "level": 2, "text": "Active escalations"})
    if escalations:
        esc_items = []
        for esc in escalations:
            level = esc.get("level", 0)
            name = esc.get("beneficiary_name", "?")
            sector = esc.get("sector", "?")
            triggered_at = esc.get("triggered_at", "?")
            esc_items.append(
                {
                    "type": "text",
                    "text": f"L{level} — {name} (sector {sector}) — {triggered_at}",
                }
            )
        blocks.append({"type": "bulleted_list", "elements": esc_items})
    else:
        blocks.append({"type": "paragraph", "text": "_No active escalation._"})

    # Directives
    if directives:
        blocks.append({"type": "heading", "level": 2, "text": "Fresh health directives"})
        dir_items = []
        for d in directives[:3]:
            source = d.get("source", "?")
            title = d.get("title", "")
            url = d.get("url", "")
            text = f"*{source}* — {title}"
            if url:
                text += f" <{url}|(link)>"
            dir_items.append({"type": "text", "text": text})
        blocks.append({"type": "bulleted_list", "elements": dir_items})

    # Footer
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "paragraph",
            "text": "_Vigie — automatic refresh every 5 minutes during vigilance. So the heatwave no longer kills in silence._",
        }
    )

    return blocks
