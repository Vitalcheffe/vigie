"""Tests for VLM audit log integration."""
import asyncio
import json
import os
import sys
import unittest.mock as mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vlm import DashboardAnalysis, VigieVLMService, _audit_vlm_call
from app.audit import get_audit_log, clear_audit_log, get_audit_stats


def _fresh_service(timeout: float = 5.0) -> VigieVLMService:
    """Return a VigieVLMService with reset state."""
    svc = VigieVLMService(timeout=timeout)
    VigieVLMService._stats = {
        "calls_total": 0,
        "calls_ok": 0,
        "calls_failed": 0,
        "cache_hits": 0,
        "parse_errors": 0,
    }
    VigieVLMService._cache = {}
    return svc


def test_audit_vlm_call_records_entry():
    """_audit_vlm_call writes an entry to the audit log."""
    clear_audit_log()
    analysis = DashboardAnalysis(
        coverage_percent=94,
        l2_count=2,
        l3_count=1,
        crisis_msg_count=43,
        dashboard_health="ALERT",
        active_alerts=[{"name": "Monique B.", "level": "L3"}],
        top_sectors=["secteur-1", "secteur-2", "secteur-3"],
        summary="ok",
        latency_ms=12345.6,
    )
    _audit_vlm_call(analysis, 12345.6, "/tmp/test.png")

    entries = get_audit_log(limit=10)
    assert len(entries) == 1, f"expected 1 entry, got {len(entries)}"
    e = entries[0]
    assert e["actor"] == "vigie-vlm"
    assert e["action"] == "vlm_analyze"
    assert e["target"] == "/tmp/test.png"
    assert e["result"] == "ok"
    assert e["metadata"]["coverage_percent"] == 94
    assert e["metadata"]["l2_count"] == 2
    assert e["metadata"]["l3_count"] == 1
    assert e["metadata"]["dashboard_health"] == "ALERT"
    assert e["metadata"]["active_alerts_count"] == 1
    assert e["metadata"]["top_sectors_count"] == 3
    assert e["metadata"]["vlm_latency_ms"] == 12345.6
    print("PASS test_audit_vlm_call_records_entry")


def test_audit_vlm_call_with_parse_error():
    """_audit_vlm_call records parse_error result correctly."""
    clear_audit_log()
    analysis = DashboardAnalysis(
        parse_error="no_json_object_found",
        latency_ms=500.0,
    )
    _audit_vlm_call(analysis, 500.0, "/tmp/bad.png")

    entries = get_audit_log(limit=10)
    assert len(entries) == 1
    e = entries[0]
    assert e["result"] == "parse_error"
    assert e["metadata"]["parse_error"] == "no_json_object_found"
    print("PASS test_audit_vlm_call_with_parse_error")


def test_audit_vlm_call_with_subprocess_error():
    """_audit_vlm_call records subprocess_error result correctly."""
    clear_audit_log()
    analysis = DashboardAnalysis(
        parse_error="rc=1: Failed to make vision API request",
        latency_ms=100.0,
    )
    _audit_vlm_call(analysis, 100.0, "/tmp/fail.png")

    entries = get_audit_log(limit=10)
    assert len(entries) == 1
    e = entries[0]
    assert e["result"] == "subprocess_error"
    print("PASS test_audit_vlm_call_with_subprocess_error")


def test_audit_vlm_call_with_exception_error():
    """_audit_vlm_call records subprocess_error for exceptions too."""
    clear_audit_log()
    analysis = DashboardAnalysis(
        parse_error="exc=TimeoutError:timeout",
        latency_ms=180000.0,
    )
    _audit_vlm_call(analysis, 180000.0, "/tmp/timeout.png")

    entries = get_audit_log(limit=10)
    assert len(entries) == 1
    e = entries[0]
    assert e["result"] == "subprocess_error"
    print("PASS test_audit_vlm_call_with_exception_error")


def test_analyze_screenshot_logs_to_audit():
    """analyze_screenshot records an audit entry on successful call (mocked subprocess)."""
    clear_audit_log()
    svc = _fresh_service(5.0)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake-png")
        path = f.name
    try:
        async def fake_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    fake_json = json.dumps({
                        "choices": [{
                            "message": {
                                "content": '{"COVERAGE_PERCENT": 88, "L2_COUNT": 1, "L3_COUNT": 0, "DASHBOARD_HEALTH": "OK", "TOP_SECTORS": [], "ACTIVE_ALERTS": [], "SUMMARY": "ok"}'
                            }
                        }]
                    })
                    return fake_json.encode(), b""
            return FakeProc()

        with mock.patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            asyncio.run(svc.analyze_screenshot(path))

        entries = get_audit_log(limit=10)
        assert len(entries) == 1, f"expected 1 audit entry, got {len(entries)}"
        e = entries[0]
        assert e["action"] == "vlm_analyze"
        assert e["actor"] == "vigie-vlm"
        assert e["result"] == "ok"
        assert e["metadata"]["coverage_percent"] == 88
        print("PASS test_analyze_screenshot_logs_to_audit")
    finally:
        os.unlink(path)


def test_analyze_screenshot_logs_to_audit_on_failure():
    """analyze_screenshot records an audit entry even on subprocess failure."""
    clear_audit_log()
    svc = _fresh_service(5.0)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake-png")
        path = f.name
    try:
        async def fake_exec(*args, **kwargs):
            class FakeProc:
                returncode = 1
                async def communicate(self):
                    return b"", b"API error"
            return FakeProc()

        with mock.patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            asyncio.run(svc.analyze_screenshot(path))

        entries = get_audit_log(limit=10)
        assert len(entries) == 1, f"expected 1 audit entry, got {len(entries)}"
        e = entries[0]
        assert e["action"] == "vlm_analyze"
        assert e["result"] == "subprocess_error"
        print("PASS test_analyze_screenshot_logs_to_audit_on_failure")
    finally:
        os.unlink(path)


def test_audit_stats_include_vlm_events():
    """get_audit_stats includes vlm_analyze events in by_action counts."""
    clear_audit_log()
    # Add 3 VLM events
    for cov in [94, 95, 96]:
        _audit_vlm_call(
            DashboardAnalysis(coverage_percent=cov, dashboard_health="OK", latency_ms=100.0),
            100.0,
            "/tmp/test.png",
        )

    stats = get_audit_stats()
    assert stats["total"] == 3
    assert stats["by_action"].get("vlm_analyze") == 3
    assert stats["by_result"].get("ok") == 3
    print("PASS test_audit_stats_include_vlm_events")


def main():
    print("=== VLM Audit Log Tests ===")
    test_audit_vlm_call_records_entry()
    test_audit_vlm_call_with_parse_error()
    test_audit_vlm_call_with_subprocess_error()
    test_audit_vlm_call_with_exception_error()
    test_analyze_screenshot_logs_to_audit()
    test_analyze_screenshot_logs_to_audit_on_failure()
    test_audit_stats_include_vlm_events()
    print("\nAll VLM audit log tests passed (7/7).")


if __name__ == "__main__":
    main()
