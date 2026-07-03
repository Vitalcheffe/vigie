"""
Vigie — App Home dashboard builder.

The App Home is the volunteer's personal command center. It shows:
- Greeting with the volunteer's name
- Current weather alert banner
- Today's check-in assignments (compact)
- Real-time KPIs (cellule de crise view)
- Quick actions (start calls, view cellule de crise)
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
        kpis: Cellule de crise KPIs (coverage, latencies, counts)
        personal_stats: Volunteer's personal stats (today's count, weak signals)

    Returns a Slack view dict ready for `client.views_publish()`.
    """
    assignments = assignments or []
    kpis = kpis or {}
    personal_stats = personal_stats or {}
    first_name = (user_name or "").split()[0] or "bénévole"

    blocks: list[dict[str, Any]] = []

    # Header
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":wave: Bonjour {first_name}",
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
                    "Bienvenue dans votre tableau de bord Vigie. "
                    "Ici, vous trouverez vos check-in du jour, les alertes en cours, "
                    "et l'état de la cellule de crise.\n\n"
                    "_Vigie veille pour que personne ne veille seul._"
                ),
            },
        }
    )

    # Alert banner
    if alert:
        level = alert.get("level", "?")
        phenomenon = alert.get("phenomenon", "canicule")
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
                        f"{emoji} *Vigilance {level} — {phenomenon}*\n"
                        f":round_pushpin: {departments}\n"
                        f":thermometer: T° max prévue : *{max_temp}°C*\n"
                        f":clock1: Valide jusqu'à : {alert.get('valid_to', '?')}"
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
                    "text": ":white_check_mark: *Aucune alerte canicule active.* Vos check-in habituels restent disponibles.",
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
                "text": f":telephone_receiver: Vos check-in du jour ({len(assignments)})",
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
                            f"{status_emoji} *{name}* ({age} ans, secteur {sector})\n"
                            f":telephone: `{phone}` — `id: {b.get('id')}`"
                        ),
                    },
                }
            )

        if len(assignments) > 5:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"_... et {len(assignments) - 5} autres. Détails dans le DM._"},
                }
            )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_Aucun check-in assigné pour aujourd'hui._"},
            }
        )

    # Cellule de crise KPIs
    if kpis:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":bar_chart: Cellule de crise — vue temps réel", "emoji": True},
            }
        )
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Couverture (< 2h)*\n{kpis.get('coverage_pct', '?')}%"},
                    {"type": "mrkdwn", "text": f"*Temps moyen check-in*\n{kpis.get('avg_checkin_time', '?')}"},
                    {"type": "mrkdwn", "text": f"*Latence escalade*\n{kpis.get('avg_escalade_latency', '?')}"},
                    {"type": "mrkdwn", "text": f"*Non contactés > 72h*\n{kpis.get('unreachable_72h', '?')}"},
                    {"type": "mrkdwn", "text": f"*Escalades coord.*\n{kpis.get('coord_count', '?')}"},
                    {"type": "mrkdwn", "text": f"*Escalades SAMU*\n{kpis.get('samu_count', '?')}"},
                ],
            }
        )

    # Personal stats
    if personal_stats:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":bust_in_silhouette: Vos statistiques", "emoji": True},
            }
        )
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Check-in réalisés aujourd'hui*\n{personal_stats.get('today_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Signaux faibles détectés*\n{personal_stats.get('weak_signals', 0)}"},
                    {"type": "mrkdwn", "text": f"*Escalades déclenchées*\n{personal_stats.get('escalations', 0)}"},
                    {"type": "mrkdwn", "text": f"*Temps moyen (vos check-in)*\n{personal_stats.get('avg_time', '?')}"},
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
                    "text": {"type": "plain_text", "text": ":telephone_receiver: Démarrer mes appels", "emoji": True},
                    "action_id": "vigie_start_calls",
                    "style": "primary",
                    "value": user_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":memo: Mes check-in passés", "emoji": True},
                    "action_id": "vigie_view_my_checkins",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":rotating_light: Cellule de crise", "emoji": True},
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
                {"type": "mrkdwn", "text": "_Vigie — Pour que la canicule ne tue plus en silence._"},
                {"type": "mrkdwn", "text": "En cas d'urgence vitale, appelez le *15* ou le *112*."},
            ],
        }
    )

    return {"type": "home", "blocks": blocks}
