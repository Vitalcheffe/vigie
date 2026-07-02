"""Tests: VigieState in-memory store."""

from __future__ import annotations

from app.state import VigieState


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
