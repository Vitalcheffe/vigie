"""
Vigie — Block Kit builder for the daily report (posted at 18h00 in #cellule-crise).

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
                "text": f":memo: Rapport quotidien Vigie — {date}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Généré automatiquement à 18h00 • Slack AI + Real-Time Search API"},
            ],
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 Indicateurs du jour", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Couverture (< 2h)*\n:large_green_circle: *{coverage_pct}%* ({contacted}/{total})"},
                {"type": "mrkdwn", "text": f"*Temps moyen check-in*\n:stopwatch: *{avg_checkin_time}*"},
                {"type": "mrkdwn", "text": f"*Latence escalade*\n:stopwatch: *{avg_escalade_latency}*"},
                {"type": "mrkdwn", "text": f"*Non contactés > 72h*\n:warning: *{unreachable_72h}*"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Check-in OK*\n:large_green_circle: *{ok_count}*"},
                {"type": "mrkdwn", "text": f"*Signaux faibles*\n:large_yellow_circle: *{weak_count}*"},
                {"type": "mrkdwn", "text": f"*Escalades coordinateur*\n:large_orange_circle: *{coord_count}*"},
                {"type": "mrkdwn", "text": f"*Escalades SAMU*\n{samu_emoji} *{samu_count}*"},
            ],
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":brain: Synthèse (Slack AI)", "emoji": True},
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
                "text": {"type": "mrkdwn", "text": f":eyes: *Signaux faibles à surveiller demain :*\n{signals_text}"},
            }
        )

    if rts_directives:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":globe_with_meridians: Directives sanitaires fraîches", "emoji": True},
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
                            + (f"\n<{url}|Lien>" if url else "")
                            + (f"\n> {summary}" if summary else "")
                        ),
                    },
                }
            )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_Vigie — Pour que la canicule ne tue plus en silence._"},
                {"type": "mrkdwn", "text": "Données simulées — aucun bénéficiaire réel n'est utilisé dans cette démo."},
            ],
        }
    )

    return {
        "blocks": blocks,
        "text": f"Rapport Vigie {date} — {coverage_pct}% couverture, {samu_count} SAMU",
    }
