"""
Vigie — Volunteer progress tracker.

Tracks how many check-ins each volunteer has completed today,
and sends personalized progress updates and thank-you messages.

When a volunteer completes all their check-ins, Vigie sends a 
celebratory message with the impact they made.
"""

from __future__ import annotations

import random
from typing import Any

from app.state import get_state
from app.tone import VOLUNTEER_THANKS
from app.utils.logging import get_logger

log = get_logger("vigie.progress")


def get_volunteer_progress(volunteer_id: str) -> dict[str, Any]:
    """Get a volunteer's progress for the current scenario.

    Returns:
        {
            "total_assigned": int,
            "completed": int,
            "pending": int,
            "weak_signals": int,
            "escalations": int,
            "progress_pct": int,
            "completed_names": [str],  # names of completed check-ins
            "pending_names": [str],    # names still waiting
        }
    """
    state = get_state()
    
    # Get all check-ins by this volunteer
    my_checkins = [
        c for c in state._checkins  # noqa: SLF001
        if c.get("volunteer_id") == volunteer_id
    ]
    
    # Get all escalations triggered by this volunteer
    my_escalations = [
        e for e in state._escalations  # noqa: SLF001
        if e.get("triggered_by") == volunteer_id
    ]
    
    # Count weak signals
    weak = sum(1 for c in my_checkins if c.get("anomaly_level", 0) == 1)
    
    # Get beneficiary names for completed and pending
    from mcp_server.resources.beneficiary_registry import get_registry, get_beneficiary_by_id
    
    completed_names = []
    for c in my_checkins:
        bid = c.get("beneficiary_id", "")
        b = get_beneficiary_by_id(bid)
        if b:
            completed_names.append(f"{b['first_name']} {b['last_initial']}.")
        else:
            completed_names.append(bid)
    
    # Find pending (assigned but not checked)
    registry = get_registry()
    pending_names = [
        f"{b['first_name']} {b['last_initial']}."
        for b in registry
        if b.get("status") == "being_checked"
        and b["id"] not in [c.get("beneficiary_id") for c in my_checkins]
    ][:10]  # limit to 10
    
    total = len(completed_names) + len(pending_names)
    completed = len(completed_names)
    
    return {
        "total_assigned": total,
        "completed": completed,
        "pending": len(pending_names),
        "weak_signals": weak,
        "escalations": len(my_escalations),
        "progress_pct": int((completed / total) * 100) if total > 0 else 0,
        "completed_names": completed_names,
        "pending_names": pending_names,
    }


def build_progress_message(volunteer_name: str, progress: dict[str, Any]) -> str:
    """Build a personalized progress message for a volunteer.

    Tone: warm, encouraging, shows impact.
    """
    pct = progress["progress_pct"]
    completed = progress["completed"]
    total = progress["total_assigned"]
    pending = progress["pending"]
    
    parts = [f":bar_chart: *Your progress today: {pct}%* ({completed}/{total} check-ins done)\n"]
    
    if completed > 0:
        parts.append(f":white_check_mark: *Completed:* {', '.join(progress['completed_names'][:5])}")
        if len(progress['completed_names']) > 5:
            parts.append(f" and {len(progress['completed_names']) - 5} more")
        parts.append("\n")
    
    if pending > 0:
        parts.append(f":clock1: *Still waiting:* {', '.join(progress['pending_names'][:5])}")
        if len(progress['pending_names']) > 5:
            parts.append(f" and {len(progress['pending_names']) - 5} more")
        parts.append("\n")
    
    if progress["weak_signals"] > 0:
        parts.append(f":warning: *Weak signals detected:* {progress['weak_signals']} — you may have caught something early.\n")
    
    if progress["escalations"] > 0:
        parts.append(f":rotating_light: *Escalations triggered:* {progress['escalations']} — you acted when it mattered.\n")
    
    # Closing message based on progress
    if pct == 100:
        parts.append(f"\n:tada: *You've completed all your check-ins!* {random.choice(VOLUNTEER_THANKS)}")
    elif pct >= 50:
        parts.append(f"\n:heart: You're over halfway there. Keep going — {random.choice(VOLUNTEER_THANKS)}")
    elif pct > 0:
        parts.append(f"\n:bulb: Good start. {pending} more to go. {random.choice(VOLUNTEER_THANKS)}")
    else:
        parts.append(f"\n:wave: Click the Check-in button next to each name after your call. I'm here to help.")
    
    return "".join(parts)
