"""
Vigie — Canvas builder for the #cellule-crise real-time view.

Slack Canvas is the persistent, structured document surface where we
publish the live state of the cellule de crise: alert level, coverage,
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
    Build the document content for the cellule-de-crise Slack Canvas.

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
            "text": f"Cellule de crise — Vigie — {date}",
        }
    )

    # Alert banner
    alert_emoji = ":large_orange_circle:" if alert_level == "orange" else ":red_circle:"
    deps_str = ", ".join(alert_departments) if alert_departments else "—"
    blocks.append(
        {
            "type": "callout",
            "style": "warning" if alert_level == "orange" else "error",
            "text": f"{alert_emoji} *Vigilance {alert_level} — {alert_phenomenon}*\nDépartements : {deps_str}",
        }
    )

    # KPI section
    blocks.append({"type": "heading", "level": 2, "text": "Indicateurs temps réel"})
    blocks.append(
        {
            "type": "bulleted_list",
            "elements": [
                {"type": "text", "text": f"*Couverture (< 2h)* : {coverage_pct}% ({contacted}/{total_beneficiaries})"},
                {"type": "text", "text": f"*Temps moyen check-in* : {avg_checkin_time}"},
                {"type": "text", "text": f"*Latence escalade* : {avg_escalade_latency}"},
                {"type": "text", "text": f"*Check-in OK* : {ok_count}"},
                {"type": "text", "text": f"*Signaux faibles* : {weak_count}"},
                {"type": "text", "text": f"*Escalades coordinateur* : {coord_count}"},
                {"type": "text", "text": f"*Escalades SAMU* : {samu_count}"},
                {"type": "text", "text": f"*Non contactés > 72h* : {unreachable_72h}"},
            ],
        }
    )

    # Active escalations
    blocks.append({"type": "heading", "level": 2, "text": "Escalades actives"})
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
                    "text": f"L{level} — {name} (secteur {sector}) — {triggered_at}",
                }
            )
        blocks.append({"type": "bulleted_list", "elements": esc_items})
    else:
        blocks.append({"type": "paragraph", "text": "_Aucune escalade active._"})

    # Directives
    if directives:
        blocks.append({"type": "heading", "level": 2, "text": "Directives sanitaires fraîches"})
        dir_items = []
        for d in directives[:3]:
            source = d.get("source", "?")
            title = d.get("title", "")
            url = d.get("url", "")
            text = f"*{source}* — {title}"
            if url:
                text += f" <{url}|(lien)>"
            dir_items.append({"type": "text", "text": text})
        blocks.append({"type": "bulleted_list", "elements": dir_items})

    # Footer
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "paragraph",
            "text": "_Vigie — mise à jour automatique toutes les 5 minutes pendant la vigilance. Pour que la canicule ne tue plus en silence._",
        }
    )

    return blocks
