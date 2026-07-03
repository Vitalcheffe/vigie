"""Tests: Audit log."""

from __future__ import annotations

from app.audit import (
    clear_audit_log,
    get_audit_log,
    get_audit_stats,
    log_action,
)


def setup_function():
    """Clear the audit log before each test."""
    clear_audit_log()


def test_audit_log_starts_empty():
    """A fresh audit log should be empty."""
    clear_audit_log()
    assert get_audit_log() == []


def test_log_action_appends_entry():
    """log_action should append an entry to the log."""
    log_action(
        actor="U001",
        action="start_heatwave",
        target="75",
        reason="alert_level=orange",
        result="ok",
        metadata={"total_beneficiaries": 50},
    )

    entries = get_audit_log()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["actor"] == "U001"
    assert entry["action"] == "start_heatwave"
    assert entry["target"] == "75"
    assert entry["result"] == "ok"
    assert entry["metadata"]["total_beneficiaries"] == 50
    assert "timestamp" in entry


def test_audit_log_returns_most_recent_first():
    """get_audit_log should return entries most-recent-first."""
    for i in range(5):
        log_action(actor=f"U00{i}", action="test_action")

    entries = get_audit_log()
    assert len(entries) == 5
    # Most recent first
    assert entries[0]["actor"] == "U004"
    assert entries[-1]["actor"] == "U000"


def test_audit_log_respects_limit():
    """get_audit_log(limit=N) should return at most N entries."""
    for i in range(10):
        log_action(actor=f"U00{i}", action="test_action")

    entries = get_audit_log(limit=3)
    assert len(entries) == 3
    # Should be the 3 most recent
    assert entries[0]["actor"] == "U009"
    assert entries[1]["actor"] == "U008"
    assert entries[2]["actor"] == "U007"


def test_audit_log_clears():
    """clear_audit_log should wipe all entries."""
    log_action(actor="U001", action="test")
    assert len(get_audit_log()) == 1

    clear_audit_log()
    assert get_audit_log() == []


def test_audit_stats_counts_by_action_and_result():
    """get_audit_stats should aggregate by action and result."""
    log_action(actor="U001", action="start_heatwave", result="ok")
    log_action(actor="U001", action="process_checkin", result="ok")
    log_action(actor="U001", action="process_checkin", result="ok")
    log_action(actor="U001", action="trigger_escalation", result="ok")
    log_action(actor="U001", action="start_heatwave", result="error", reason="mcp_down")

    stats = get_audit_stats()
    assert stats["total"] == 5
    assert stats["by_action"]["start_heatwave"] == 2
    assert stats["by_action"]["process_checkin"] == 2
    assert stats["by_action"]["trigger_escalation"] == 1
    assert stats["by_result"]["ok"] == 4
    assert stats["by_result"]["error"] == 1


def test_audit_stats_empty_log():
    """get_audit_stats on an empty log should return zeros."""
    clear_audit_log()
    stats = get_audit_stats()
    assert stats["total"] == 0
    assert stats["by_action"] == {}
    assert stats["by_result"] == {}
    assert stats["first_event"] is None
    assert stats["last_event"] is None


def test_audit_log_optional_fields_default_to_none():
    """log_action should handle missing optional fields gracefully."""
    log_action(actor="U001", action="test_action")

    entries = get_audit_log()
    entry = entries[0]
    assert entry["target"] is None
    assert entry["reason"] is None
    assert entry["result"] == "ok"  # default
    assert entry["metadata"] == {}


def test_audit_log_ring_buffer_max_1000():
    """The audit log should cap at 1000 entries (ring buffer)."""
    clear_audit_log()
    for i in range(1050):
        log_action(actor=f"U00{i}", action="flood_test")

    entries = get_audit_log(limit=2000)
    assert len(entries) == 1000  # capped
    # Most recent should be the last one we added
    assert entries[0]["actor"] == "U001049"
