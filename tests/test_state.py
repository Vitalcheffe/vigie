"""Tests: VigieState in-memory store (with real latency computation)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.state import (
    VigieState,
    _compute_avg_checkin_time,
    _compute_avg_escalade_latency,
    _format_duration,
    _parse_iso,
)


def test_state_starts_empty():
    state = VigieState()
    metrics = state.get_metrics()
    assert metrics["scenario_active"] is False
    assert metrics["total_assigned"] == 0
    assert metrics["contacted"] == 0


def test_state_start_scenario_resets_counters():
    state = VigieState()
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 0})
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    metrics = state.get_metrics()
    assert metrics["scenario_active"] is True
    assert metrics["total_assigned"] == 50
    assert metrics["contacted"] == 0  # reset


def test_state_record_checkin_increments_contacted():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 0})
    state.record_checkin({"beneficiary_id": "B002", "anomaly_level": 0})
    metrics = state.get_metrics()
    assert metrics["contacted"] == 2
    assert metrics["ok_count"] == 2


def test_state_record_checkin_dedupes_beneficiary():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 0})
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 1})  # second check-in
    metrics = state.get_metrics()
    assert metrics["contacted"] == 1  # deduped
    assert metrics["ok_count"] == 1  # first check-in was OK
    assert metrics["weak_count"] == 1  # second was weak


def test_state_record_escalation_counts_by_level():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_escalation({"escalation_id": "E1", "beneficiary_id": "B001", "level": 2})
    state.record_escalation({"escalation_id": "E2", "beneficiary_id": "B002", "level": 3})
    state.record_escalation({"escalation_id": "E3", "beneficiary_id": "B003", "level": 2})
    metrics = state.get_metrics()
    assert metrics["coord_escalations"] == 2
    assert metrics["samu_escalations"] == 1


def test_state_resolve_escalation_marks_resolved():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_escalation({"escalation_id": "E1", "beneficiary_id": "B001", "level": 2})
    metrics_before = state.get_metrics()
    assert metrics_before["coord_escalations"] == 1
    assert state.resolve_escalation("E1") is True
    metrics_after = state.get_metrics()
    assert metrics_after["coord_escalations"] == 0


def test_state_resolve_unknown_escalation_returns_false():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    assert state.resolve_escalation("DOES_NOT_EXIST") is False


def test_state_get_active_escalations_excludes_resolved():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_escalation({"escalation_id": "E1", "beneficiary_id": "B001", "level": 3})
    state.record_escalation({"escalation_id": "E2", "beneficiary_id": "B002", "level": 3})
    state.resolve_escalation("E1")
    active = state.get_active_escalations()
    assert len(active) == 1
    assert active[0]["escalation_id"] == "E2"


def test_state_reset_clears_everything():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 0})
    state.record_escalation({"escalation_id": "E1", "beneficiary_id": "B001", "level": 3})
    state.reset()
    metrics = state.get_metrics()
    assert metrics["scenario_active"] is False
    assert metrics["contacted"] == 0
    assert metrics["samu_escalations"] == 0


def test_state_weak_signals_summary():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state.record_checkin({"beneficiary_id": "B023", "anomaly_level": 1, "transcript_preview": "fatiguée"})
    state.record_checkin({"beneficiary_id": "B014", "anomaly_level": 1, "transcript_preview": "confuse"})
    state.record_checkin({"beneficiary_id": "B001", "anomaly_level": 0})
    summary = state.get_weak_signals_summary()
    assert len(summary) == 2
    assert any("B023" in s for s in summary)
    assert any("B014" in s for s in summary)


def test_state_coverage_pct_computed_correctly():
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    for i in range(47):
        state.record_checkin({"beneficiary_id": f"B{i:03d}", "anomaly_level": 0})
    metrics = state.get_metrics()
    assert metrics["coverage_pct"] == 94  # 47/50 = 94%
    assert metrics["unreachable_72h"] == 3


# ============================================================
# Real latency computation tests
# ============================================================


def test_format_duration_under_60s():
    assert _format_duration(45) == "45 s"


def test_format_duration_minutes():
    assert _format_duration(130) == "2 min 10 s"


def test_format_duration_hours():
    assert _format_duration(5400) == "1 h 30 min"


def test_parse_iso_valid():
    ts = _parse_iso("2026-07-15T08:00:00+00:00")
    assert ts is not None
    assert ts > 0


def test_parse_iso_z_suffix():
    ts = _parse_iso("2026-07-15T08:00:00Z")
    assert ts is not None


def test_parse_iso_invalid():
    assert _parse_iso(None) is None
    assert _parse_iso("") is None
    assert _parse_iso("not-a-date") is None


def test_compute_avg_checkin_time_with_no_data():
    assert _compute_avg_checkin_time([]) == "—"


def test_compute_avg_checkin_time_with_real_durations():
    """Two check-ins: 5 min and 7 min → avg 6 min."""
    checkins = [
        {"assigned_at": "2026-07-15T08:00:00+00:00", "recorded_at": "2026-07-15T08:05:00+00:00"},
        {"assigned_at": "2026-07-15T09:00:00+00:00", "recorded_at": "2026-07-15T09:07:00+00:00"},
    ]
    result = _compute_avg_checkin_time(checkins)
    assert "6 min" in result


def test_compute_avg_escalade_latency_with_real_durations():
    """Two escalations: 4 min 30 s and 5 min 30 s → avg 5 min."""
    escalations = [
        {"detected_at": "2026-07-15T10:00:00+00:00", "recorded_at": "2026-07-15T10:04:30+00:00"},
        {"detected_at": "2026-07-15T11:00:00+00:00", "recorded_at": "2026-07-15T11:05:30+00:00"},
    ]
    result = _compute_avg_escalade_latency(escalations)
    assert "5 min" in result


def test_compute_avg_checkin_time_ignores_missing_timestamps():
    """Check-ins without assigned_at should be skipped, not crashed."""
    checkins = [
        {"recorded_at": "2026-07-15T08:05:00+00:00"},  # no assigned_at
        {"assigned_at": "2026-07-15T09:00:00+00:00", "recorded_at": "2026-07-15T09:07:00+00:00"},
    ]
    result = _compute_avg_checkin_time(checkins)
    # Only the second check-in is counted: 7 min
    assert "7 min" in result


def test_state_metrics_reflect_real_latencies():
    """The full state store should compute real latencies from timestamps."""
    state = VigieState()
    state.start_scenario(alert={"level": "orange"}, total_assigned=50)
    state._scenario_start = datetime.now(UTC) - timedelta(minutes=10)
    # Use 7 min for check-in (not 2 min 10 s) and 3 min for escalation (not 4 min 30 s)
    state.record_checkin({
        "beneficiary_id": "B001",
        "anomaly_level": 0,
        "assigned_at": (datetime.now(UTC) - timedelta(minutes=7)).isoformat(),
    })
    state.record_escalation({
        "escalation_id": "E1",
        "beneficiary_id": "B001",
        "level": 3,
        "detected_at": (datetime.now(UTC) - timedelta(minutes=3)).isoformat(),
    })
    metrics = state.get_metrics()
    # Latencies should be computed from our test data, not hardcoded
    assert metrics["avg_checkin_time"] != "—"
    assert "7 min" in metrics["avg_checkin_time"] or "6 min" in metrics["avg_checkin_time"]
    assert metrics["avg_escalade_latency"] != "—"
    assert "3 min" in metrics["avg_escalade_latency"]
