"""
Vigie — Reminder service.

Sends gentle reminders to volunteers who haven't completed their check-ins.
Runs every 2 hours during an active heatwave scenario.

The tone is warm, not nagging:
  "Hi Marie, you still have 3 check-ins pending. No rush — just a reminder.
   Mrs Dupont, Mr Bernard, and Mrs Leroy are waiting for a call. 💜"
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient

from app.state import get_state
from app.tone import VOLUNTEER_THANKS
from app.utils.logging import get_logger
from app.utils.slack_helpers import post_dm

log = get_logger("vigie.reminders")


async def send_checkin_reminders(client: AsyncWebClient) -> dict[str, Any]:
    """Send gentle reminders to volunteers with pending check-ins.

    Only fires when a scenario is active. Reads the state store to find
    which beneficiaries haven't been contacted yet, maps them back to
    their assigned volunteer, and sends a warm DM.

    Returns a summary dict.
    """
    state = get_state()
    metrics = state.get_metrics()

    if not metrics.get("scenario_active"):
        log.debug("reminders.skipped_no_scenario")
        return {"status": "skipped", "reason": "no_active_scenario"}

    total = metrics.get("total_assigned", 0)
    contacted = metrics.get("contacted", 0)
    pending = total - contacted

    if pending <= 0:
        log.info("reminders.all_done", contacted=contacted, total=total)
        return {"status": "all_done", "contacted": contacted, "total": total}

    # Find which beneficiaries are still pending
    # (assigned but not yet checked in)
    from mcp_server.resources.beneficiary_registry import get_registry

    registry = get_registry()
    pending_beneficiaries = [
        b for b in registry
        if b.get("status") == "being_checked"
    ]

    if not pending_beneficiaries:
        return {"status": "no_pending", "pending": 0}

    # Group by volunteer (we don't have the assignment mapping in state,
    # so we send to all volunteers who have been assigned)
    # In production, we'd track the volunteer→beneficiary mapping.
    # For now, we send a general reminder to the workspace.

    pending_names = [
        f"{b.get('first_name', '?')} {b.get('last_initial', '?')}."
        for b in pending_beneficiaries[:5]
    ]
    names_str = ", ".join(pending_names)
    if len(pending_beneficiaries) > 5:
        names_str += f" and {len(pending_beneficiaries) - 5} more"

    thanks = random.choice(VOLUNTEER_THANKS)

    reminder_text = (
        f":bell: *Gentle reminder*\n\n"
        f"You still have *{pending}* check-in{'s' if pending > 1 else ''} pending. "
        f"No rush — just a friendly nudge. 💜\n\n"
        f"Still waiting for a call: {names_str}\n\n"
        f"Just click the **Check-in** button next to each name in our conversation. "
        f"It takes 10 seconds per person.\n\n"
        f"{thanks}"
    )

    # In a real deployment, we'd send this DM to each volunteer who has
    # pending check-ins. For now, we post it in #cellule-crise.
    from app.utils.slack_helpers import post_to_cellule_crise
    await post_to_cellule_crise(client, text=reminder_text)

    log.info("reminders.sent", pending=pending, beneficiaries=len(pending_beneficiaries))

    return {
        "status": "sent",
        "pending": pending,
        "beneficiaries": len(pending_beneficiaries),
    }
