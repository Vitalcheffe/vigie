"""
Vigie — In-memory state store.

Tracks the live state of the cellule de crise: check-ins, escalations,
weak signals, coverage. Used by the orchestrator to:
  - Generate real metrics for the daily report (instead of hardcoded values)
  - Feed the /metrics health endpoint
  - Power the App Home dashboard KPIs

The store is intentionally in-memory (no DB). A production deploy would
swap this for Redis or PostgreSQL without changing the public API.

Public API:
  - record_checkin(checkin) -> None
  - record_escalation(escalation) -> None
  - get_metrics() -> dict
  - get_active_escalations() -> list
  - reset() -> None
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.state")

_lock = threading.RLock()


class VigieState:
    """Thread-safe in-memory state store for the Vigie cellule de crise."""

    def __init__(self) -> None:
        self._checkins: list[dict[str, Any]] = []
        self._escalations: list[dict[str, Any]] = []
        self._weak_signals: list[dict[str, Any]] = []
        self._assignments_today: dict[str, list[str]] = {}  # volunteer_id -> [beneficiary_id]
        self._total_assigned: int = 0
        self._active_alert: dict[str, Any] | None = None
        self._scenario_start: datetime | None = None

    # ============================================================
    # Heatwave scenario lifecycle
    # ============================================================

    def start_scenario(self, alert: dict[str, Any], total_assigned: int) -> None:
        """Mark the start of a heatwave scenario."""
        with _lock:
            self._active_alert = alert
            self._total_assigned = total_assigned
            self._scenario_start = datetime.now(UTC)
            self._checkins.clear()
            self._escalations.clear()
            self._weak_signals.clear()
            self._assignments_today.clear()
        log.info(
            "state.scenario_started",
            alert_level=alert.get("level"),
            total_assigned=total_assigned,
        )

    def stop_scenario(self) -> None:
        """End the active scenario."""
        with _lock:
            self._active_alert = None
            self._scenario_start = None
        log.info("state.scenario_stopped")

    @property
    def is_scenario_active(self) -> bool:
        return self._active_alert is not None

    @property
    def active_alert(self) -> dict[str, Any] | None:
        return self._active_alert

    # ============================================================
    # Check-ins
    # ============================================================

    def record_checkin(self, checkin: dict[str, Any]) -> None:
        """Record a completed check-in.

        Optional field `assigned_at` (ISO timestamp) lets us compute the
        actual check-in latency (assigned_at → recorded_at).
        """
        with _lock:
            self._checkins.append({**checkin, "recorded_at": datetime.now(UTC).isoformat()})
            if checkin.get("anomaly_level", 0) == 1:
                self._weak_signals.append(checkin)
        log.debug(
            "state.checkin_recorded",
            beneficiary=checkin.get("beneficiary_id"),
            level=checkin.get("anomaly_level"),
            total_checkins=len(self._checkins),
        )

    def record_escalation(self, escalation: dict[str, Any]) -> None:
        """Record an escalation.

        Optional field `detected_at` (ISO timestamp) lets us compute the
        actual escalation latency (detected_at → recorded_at).
        """
        with _lock:
            self._escalations.append({**escalation, "recorded_at": datetime.now(UTC).isoformat()})
        log.info(
            "state.escalation_recorded",
            beneficiary=escalation.get("beneficiary_id"),
            level=escalation.get("level"),
            total_escalations=len(self._escalations),
        )

    def resolve_escalation(self, escalation_id: str) -> bool:
        """Mark an escalation as resolved. Returns True if found and resolved."""
        with _lock:
            for esc in self._escalations:
                if esc.get("escalation_id") == escalation_id:
                    esc["resolved"] = True
                    esc["resolved_at"] = datetime.now(UTC).isoformat()
                    log.info("state.escalation_resolved", escalation_id=escalation_id)
                    return True
        return False

    # ============================================================
    # Metrics (computed on demand)
    # ============================================================

    def get_metrics(self) -> dict[str, Any]:
        """Return the live metrics dict for /metrics and dashboards.

        All latencies are computed from the recorded timestamps of
        check-ins and escalations — no hardcoded values.
        """
        with _lock:
            checkins = list(self._checkins)
            escalations = list(self._escalations)
            weak_signals = list(self._weak_signals)
            total_assigned = self._total_assigned
            alert = dict(self._active_alert) if self._active_alert else None

        contacted = len({c["beneficiary_id"] for c in checkins})
        ok_count = sum(1 for c in checkins if c.get("anomaly_level", 0) == 0)
        weak_count = len(weak_signals)
        coord_count = sum(1 for e in escalations if e.get("level") == 2 and not e.get("resolved"))
        samu_count = sum(1 for e in escalations if e.get("level") == 3 and not e.get("resolved"))

        coverage_pct = int((contacted / total_assigned) * 100) if total_assigned > 0 else 0
        unreachable_72h = max(0, total_assigned - contacted)

        # Compute real latencies from recorded_at timestamps
        avg_checkin_time = _compute_avg_checkin_time(checkins)
        avg_escalade_latency = _compute_avg_escalade_latency(escalations)

        return {
            "alert": alert,
            "scenario_active": alert is not None,
            "total_assigned": total_assigned,
            "contacted": contacted,
            "coverage_pct": coverage_pct,
            "ok_count": ok_count,
            "weak_count": weak_count,
            "coord_escalations": coord_count,
            "samu_escalations": samu_count,
            "avg_checkin_time": avg_checkin_time,
            "avg_escalade_latency": avg_escalade_latency,
            "unreachable_72h": unreachable_72h,
            "weak_signals": [w.get("beneficiary_id") for w in weak_signals],
            "active_escalations_count": coord_count + samu_count,
        }

    def get_active_escalations(self) -> list[dict[str, Any]]:
        """Return the list of unresolved escalations."""
        with _lock:
            return [e for e in self._escalations if not e.get("resolved")]

    def get_weak_signals_summary(self) -> list[str]:
        """Return a human-readable list of weak signals for the daily report."""
        with _lock:
            return [
                f"{w.get('beneficiary_id', '?')} — {w.get('transcript_preview', '?')}"
                for w in self._weak_signals
            ]

    def reset(self) -> None:
        """Wipe all state. Used by /vigie reset."""
        with _lock:
            self._checkins.clear()
            self._escalations.clear()
            self._weak_signals.clear()
            self._assignments_today.clear()
            self._total_assigned = 0
            self._active_alert = None
            self._scenario_start = None
        log.info("state.reset")


# Singleton
_state: VigieState | None = None


def get_state() -> VigieState:
    """Return the shared VigieState singleton."""
    global _state
    if _state is None:
        _state = VigieState()
    return _state


# ============================================================
# Latency computation helpers
# ============================================================

def _parse_iso(ts: str | None) -> float | None:
    """Parse an ISO timestamp to Unix seconds. Returns None on failure."""
    if not ts:
        return None
    try:
        from datetime import datetime
        ds = ts.strip()
        if ds.endswith("Z"):
            ds = ds[:-1] + "+00:00"
        return datetime.fromisoformat(ds).timestamp()
    except (ValueError, TypeError):
        return None


def _format_duration(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)} s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} min {secs:02d} s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours} h {minutes:02d} min"


def _compute_avg_checkin_time(checkins: list[dict[str, Any]]) -> str:
    """Compute the average check-in duration from assigned_at → recorded_at.

    Returns "—" if no check-ins have an assigned_at timestamp.
    """
    durations: list[float] = []
    for c in checkins:
        assigned_ts = _parse_iso(c.get("assigned_at"))
        recorded_ts = _parse_iso(c.get("recorded_at"))
        if assigned_ts is None or recorded_ts is None:
            continue
        if recorded_ts > assigned_ts:
            durations.append(recorded_ts - assigned_ts)

    if not durations:
        return "—"
    return _format_duration(sum(durations) / len(durations))


def _compute_avg_escalade_latency(escalations: list[dict[str, Any]]) -> str:
    """Compute the average escalation latency from detected_at → recorded_at.

    Returns "—" if no escalations have a detected_at timestamp.
    """
    durations: list[float] = []
    for e in escalations:
        detected_ts = _parse_iso(e.get("detected_at"))
        recorded_ts = _parse_iso(e.get("recorded_at"))
        if detected_ts is None or recorded_ts is None:
            continue
        if recorded_ts > detected_ts:
            durations.append(recorded_ts - detected_ts)

    if not durations:
        return "—"
    return _format_duration(sum(durations) / len(durations))
