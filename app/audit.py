"""
Vigie — Audit log.

Append-only log of admin actions and critical events. Every call to
start_heatwave, trigger_escalation, reset_scenario, resolve_escalation
is recorded with: timestamp, actor, action, target, reason, result.

The log is queryable for compliance / forensics. In a real deploy,
this would be backed by a database with retention policies. For the
hackathon, it's an in-memory ring buffer (last 1000 events) exposed
via /audit on the health endpoint.

Public API:
  - log_action(actor, action, target, reason, result)
  - get_audit_log(limit=100) -> list[dict]
  - clear_audit_log()
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.audit")

_lock = threading.RLock()
_events: deque[dict[str, Any]] = deque(maxlen=1000)


def log_action(
    *,
    actor: str,
    action: str,
    target: str | None = None,
    reason: str | None = None,
    result: str = "ok",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an entry to the audit log.

    Args:
        actor: Slack user ID of the person who triggered the action
        action: One of 'start_heatwave', 'process_checkin', 'trigger_escalation',
                'resolve_escalation', 'reset_scenario', 'generate_report',
                'force_scenario'
        target: Beneficiary ID, escalation ID, or other target identifier
        reason: Free-text reason (for manual escalations)
        result: 'ok' | 'error' | 'no_alert' | 'no_scenario' | ...
        metadata: Optional dict with extra context (level, anomaly, etc.)
    """
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "reason": reason,
        "result": result,
        "metadata": metadata or {},
    }
    with _lock:
        _events.append(entry)
    log.info(
        "vigie.audit.action",
        actor=actor,
        action=action,
        target=target,
        result=result,
    )


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return the last `limit` audit entries (most recent first)."""
    with _lock:
        items = list(_events)
    items.reverse()
    return items[:limit]


def clear_audit_log() -> None:
    """Wipe the audit log (for tests and /vigie reset --purge)."""
    with _lock:
        _events.clear()
    log.info("vigie.audit.cleared")


def get_audit_stats() -> dict[str, Any]:
    """Return summary stats for the audit log."""
    with _lock:
        items = list(_events)
    by_action: dict[str, int] = {}
    by_result: dict[str, int] = {}
    for e in items:
        by_action[e["action"]] = by_action.get(e["action"], 0) + 1
        by_result[e["result"]] = by_result.get(e["result"], 0) + 1
    return {
        "total": len(items),
        "by_action": by_action,
        "by_result": by_result,
        "first_event": items[0]["timestamp"] if items else None,
        "last_event": items[-1]["timestamp"] if items else None,
    }
