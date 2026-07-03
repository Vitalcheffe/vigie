"""
Unit tests for the Vigie VLM service (app/services/vlm.py).

Tests:
  1. Parser handles clean JSON
  2. Parser handles JSON wrapped in markdown fences
  3. Parser handles JSON with extra text around
  4. Parser handles malformed JSON (sets parse_error)
  5. Dashboard health rule (OK vs ALERT) computed correctly
  6. Singleton accessor returns same instance
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vlm import (
    VIGIE_VLM_SYSTEM_PROMPT,
    DashboardAnalysis,
    VigieVLMService,
    get_vlm_service,
)


def _make_service() -> VigieVLMService:
    return VigieVLMService(timeout=10.0)


def test_parse_clean_json():
    """Parser handles clean JSON."""
    svc = _make_service()
    payload = {
        "COVERAGE_PERCENT": 94,
        "AVG_LATENCY_MIN": 7,
        "L2_COUNT": 2,
        "L3_COUNT": 1,
        "CRISIS_MSG_COUNT": 43,
        "TOP_SECTORS": ["secteur-1", "secteur-2", "secteur-3"],
        "ACTIVE_ALERTS": [
            {"name": "Monique B.", "level": "L3"},
            {"name": "Henri D.", "level": "L2"},
        ],
        "DASHBOARD_HEALTH": "ALERT",
        "SUMMARY": "Cellule active, 1 cas critique SAMU en cours.",
    }
    content = json.dumps(payload)
    a = svc._parse_analysis(content)
    assert a.coverage_percent == 94, f"coverage={a.coverage_percent}"
    assert a.avg_latency_min == 7
    assert a.l2_count == 2
    assert a.l3_count == 1
    assert a.crisis_msg_count == 43
    assert a.top_sectors == ["secteur-1", "secteur-2", "secteur-3"]
    assert len(a.active_alerts) == 2
    assert a.active_alerts[0]["name"] == "Monique B."
    assert a.active_alerts[0]["level"] == "L3"
    assert a.dashboard_health == "ALERT"
    assert "Cellule active" in a.summary
    assert a.parse_error is None
    print("PASS test_parse_clean_json")


def test_parse_markdown_fenced_json():
    """Parser handles JSON wrapped in ```json fences."""
    svc = _make_service()
    payload = {
        "COVERAGE_PERCENT": 100,
        "L2_COUNT": 0,
        "L3_COUNT": 0,
        "TOP_SECTORS": [],
        "ACTIVE_ALERTS": [],
        "DASHBOARD_HEALTH": "OK",
        "SUMMARY": "Tout va bien.",
    }
    content = f"```json\n{json.dumps(payload, indent=2)}\n```"
    a = svc._parse_analysis(content)
    assert a.coverage_percent == 100
    assert a.l2_count == 0
    assert a.l3_count == 0
    assert a.dashboard_health == "OK"
    assert a.parse_error is None
    print("PASS test_parse_markdown_fenced_json")


def test_parse_json_with_surrounding_text():
    """Parser handles JSON with extra text around."""
    svc = _make_service()
    payload = {
        "COVERAGE_PERCENT": 85,
        "L3_COUNT": 2,
        "DASHBOARD_HEALTH": "ALERT",
        "TOP_SECTORS": ["secteur-1"],
        "ACTIVE_ALERTS": [],
        "SUMMARY": "Couverture faible.",
    }
    content = f"Voici l'analyse:\n{json.dumps(payload)}\nMerci."
    a = svc._parse_analysis(content)
    assert a.coverage_percent == 85
    assert a.l3_count == 2
    assert a.dashboard_health == "ALERT"
    assert a.parse_error is None
    print("PASS test_parse_json_with_surrounding_text")


def test_parse_malformed_json():
    """Parser handles malformed JSON."""
    svc = _make_service()
    content = "This is not JSON at all, just prose."
    a = svc._parse_analysis(content)
    assert a.parse_error is not None
    assert "no_json_object_found" in a.parse_error or "json_decode" in a.parse_error
    print("PASS test_parse_malformed_json")


def test_health_rule_computation():
    """Dashboard health rule computed from coverage + L3 when DASHBOARD_HEALTH absent."""
    svc = _make_service()
    # OK case: coverage >= 90 and L3 == 0
    a = svc._parse_analysis(json.dumps({
        "COVERAGE_PERCENT": 95,
        "L3_COUNT": 0,
        "TOP_SECTORS": [],
        "ACTIVE_ALERTS": [],
        "SUMMARY": "ok",
    }))
    assert a.dashboard_health == "OK", f"expected OK, got {a.dashboard_health}"

    # ALERT case: L3 > 0
    a = svc._parse_analysis(json.dumps({
        "COVERAGE_PERCENT": 95,
        "L3_COUNT": 1,
        "TOP_SECTORS": [],
        "ACTIVE_ALERTS": [],
        "SUMMARY": "alert",
    }))
    assert a.dashboard_health == "ALERT", f"expected ALERT, got {a.dashboard_health}"

    # ALERT case: coverage < 90
    a = svc._parse_analysis(json.dumps({
        "COVERAGE_PERCENT": 80,
        "L3_COUNT": 0,
        "TOP_SECTORS": [],
        "ACTIVE_ALERTS": [],
        "SUMMARY": "low coverage",
    }))
    assert a.dashboard_health == "ALERT", f"expected ALERT, got {a.dashboard_health}"

    # UNKNOWN case: missing both fields
    a = svc._parse_analysis(json.dumps({
        "TOP_SECTORS": [],
        "ACTIVE_ALERTS": [],
        "SUMMARY": "unknown",
    }))
    assert a.dashboard_health == "UNKNOWN", f"expected UNKNOWN, got {a.dashboard_health}"
    print("PASS test_health_rule_computation")


def test_extract_content_from_cli_output():
    """_extract_content handles the z-ai CLI stdout format with emojis + JSON."""
    svc = _make_service()
    raw = """🚀 Initializing Z-AI SDK...
🚀 Sending vision chat request...
{
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "content": "{\\"COVERAGE_PERCENT\\": 94, \\"L3_COUNT\\": 1}",
        "role": "assistant"
      }
    }
  ],
  "created": 1783057975,
  "id": "abc123",
  "model": "glm-4.6v",
  "object": "chat.completion",
  "usage": {"total_tokens": 100}
}

stderr:
"""
    content = svc._extract_content(raw)
    assert "COVERAGE_PERCENT" in content
    assert "94" in content
    print("PASS test_extract_content_from_cli_output")


def test_singleton_accessor():
    """get_vlm_service returns the same instance."""
    s1 = get_vlm_service()
    s2 = get_vlm_service()
    assert s1 is s2
    print("PASS test_singleton_accessor")


def test_system_prompt_is_stable():
    """System prompt must contain the 9 mandatory fields (regression guard)."""
    mandatory_fields = [
        "COVERAGE_PERCENT",
        "AVG_LATENCY_MIN",
        "L2_COUNT",
        "L3_COUNT",
        "CRISIS_MSG_COUNT",
        "TOP_SECTORS",
        "ACTIVE_ALERTS",
        "DASHBOARD_HEALTH",
        "SUMMARY",
    ]
    for field in mandatory_fields:
        assert field in VIGIE_VLM_SYSTEM_PROMPT, f"missing field {field} in system prompt"
    print("PASS test_system_prompt_is_stable")


def main():
    print("=== VLM Service Unit Tests ===")
    test_parse_clean_json()
    test_parse_markdown_fenced_json()
    test_parse_json_with_surrounding_text()
    test_parse_malformed_json()
    test_health_rule_computation()
    test_extract_content_from_cli_output()
    test_singleton_accessor()
    test_system_prompt_is_stable()
    print("\nAll VLM service tests passed (8/8).")


if __name__ == "__main__":
    main()
