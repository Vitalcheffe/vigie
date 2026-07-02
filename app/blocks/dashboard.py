"""
Vigie — App Home dashboard builder.

The App Home is the volunteer's personal command center. It shows:
- Greeting with the volunteer's name
- Today's check-in assignments (5 beneficiaries)
- Real-time KPIs (5 metrics)
- Quick actions (start calls, view cellule de crise)
- Personal stats (today's progress, weak signals detected)
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.dashboard")


def build_app_home(user_id: str) -> dict[str, Any]:
    """
    Build the App Home view for a volunteer.

    Returns a Slack view dict ready for `client.views_publish()`.

    The view has three sections:
    1. Header with greeting + weather alert banner
    2. Today's assignments (compact list)
    3. Real-time KPIs + quick action buttons
    """
    # TODO: full implementation with live data from MCP server
    return {
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":wave: Bonjour, je suis Vigie",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Bienvenue dans votre tableau de bord Vigie. "
                        "Ici, vous trouverez vos check-in du jour, "
                        "les alertes en cours, et l'état de la cellule de crise.\n\n"
                        "_Vigie veille pour que personne ne veille seul._"
                    ),
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":rotating_light: *Aucune alerte canicule active*\n\n"
                        "Le tableau de bord temps réel sera disponible. "
                        "En attendant, tapez `/vigie help` pour voir les commandes."
                    ),
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Mes check-in du jour",
                            "emoji": True,
                        },
                        "action_id": "vigie_view_my_checkins",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cellule de crise",
                            "emoji": True,
                        },
                        "action_id": "vigie_view_cellule_crise",
                    },
                ],
            },
        ],
    }
