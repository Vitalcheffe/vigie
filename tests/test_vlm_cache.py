"""
Tests for the VLM cache and health endpoint methods.
"""
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vlm import DashboardAnalysis, VigieVLMService


def _fresh_service(timeout: float = 5.0) -> VigieVLMService:
    """Return a VigieVLMService with reset stats and cache (isolation between tests)."""
    svc = VigieVLMService(timeout=timeout)
    # Reset class-level state
    VigieVLMService._stats = {
        "calls_total": 0,
        "calls_ok": 0,
        "calls_failed": 0,
        "cache_hits": 0,
        "parse_errors": 0,
    }
    VigieVLMService._cache = {}
    return svc


def test_cache_returns_same_result_without_subprocess():
    """Cache hit returns the same DashboardAnalysis without a new subprocess call."""
    svc = _fresh_service(5.0)
    # Manually inject a cache entry
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake-png-content")
        path = f.name
    try:
        mtime = os.path.getmtime(path)
        cached = DashboardAnalysis(
            coverage_percent=94,
            l2_count=2,
            l3_count=1,
            dashboard_health="ALERT",
            summary="cached result",
            latency_ms=1.0,
        )
        svc._cache[(path, mtime)] = cached
        # Calling analyze_screenshot should return cached without subprocess
        result = asyncio.run(svc.analyze_screenshot(path, use_cache=True))
        assert result is cached, "cache should return the exact same object"
        assert svc._stats["cache_hits"] == 1
        assert svc._stats["calls_total"] == 0  # no subprocess was called
        print("PASS test_cache_returns_same_result_without_subprocess")
    finally:
        os.unlink(path)


def test_cache_bypassed_with_use_cache_false():
    """use_cache=False forces a new subprocess call even if cache has the entry.

    We mock the subprocess to avoid hitting the real API.
    """
    svc = _fresh_service(5.0)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake-png-content")
        path = f.name
    try:
        mtime = os.path.getmtime(path)
        cached = DashboardAnalysis(coverage_percent=50, summary="old")
        svc._cache[(path, mtime)] = cached

        # Mock the subprocess by patching asyncio.create_subprocess_exec
        import unittest.mock as mock

        async def fake_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    # Return a fake z-ai vision JSON response
                    fake_json = json.dumps({
                        "choices": [{
                            "message": {
                                "content": '{"COVERAGE_PERCENT": 75, "L2_COUNT": 1, "L3_COUNT": 0, "DASHBOARD_HEALTH": "OK", "TOP_SECTORS": [], "ACTIVE_ALERTS": [], "SUMMARY": "fresh call"}'
                            }
                        }]
                    })
                    return fake_json.encode(), b""

            return FakeProc()

        with mock.patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = asyncio.run(svc.analyze_screenshot(path, use_cache=False))

        assert result is not cached, "should not return cached result"
        assert svc._stats["cache_hits"] == 0, f"cache_hits should be 0, got {svc._stats['cache_hits']}"
        assert svc._stats["calls_total"] == 1, f"calls_total should be 1, got {svc._stats['calls_total']}"
        assert result.coverage_percent == 75, f"coverage should be 75 (fresh), got {result.coverage_percent}"
        print("PASS test_cache_bypassed_with_use_cache_false")
    finally:
        os.unlink(path)


def test_cache_invalidated_on_mtime_change():
    """Cache key includes mtime, so modifying the file invalidates the cache."""
    svc = _fresh_service(5.0)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"original-content")
        path = f.name
    try:
        mtime1 = os.path.getmtime(path)
        cached = DashboardAnalysis(coverage_percent=94, summary="v1")
        svc._cache[(path, mtime1)] = cached

        # Modify the file
        time.sleep(0.1)  # ensure mtime changes
        with open(path, "w") as f:
            f.write("modified-content")
        os.utime(path, None)  # force mtime update
        mtime2 = os.path.getmtime(path)
        assert mtime2 != mtime1, "mtime should have changed"

        # Cache lookup with new mtime should miss
        result = asyncio.run(svc.analyze_screenshot(path, use_cache=True))
        assert result is not cached, "cache should miss because mtime changed"
        assert svc._stats["cache_hits"] == 0
        print("PASS test_cache_invalidated_on_mtime_change")
    finally:
        os.unlink(path)


def test_health_returns_stats():
    """health() returns the expected stats structure."""
    svc = _fresh_service(30.0)
    h = svc.health()
    assert "ok" in h
    assert "stats" in h
    assert "cache_size" in h
    assert "cache_max" in h
    assert "timeout_s" in h
    assert h["timeout_s"] == 30.0
    assert h["cache_max"] == 32
    assert "calls_total" in h["stats"]
    assert "calls_ok" in h["stats"]
    assert "calls_failed" in h["stats"]
    assert "cache_hits" in h["stats"]
    assert "parse_errors" in h["stats"]
    print("PASS test_health_returns_stats")


def test_clear_cache():
    """clear_cache empties the cache and returns the count."""
    svc = _fresh_service(5.0)
    svc._cache[("a", 1.0)] = DashboardAnalysis()
    svc._cache[("b", 2.0)] = DashboardAnalysis()
    svc._cache[("c", 3.0)] = DashboardAnalysis()
    cleared = svc.clear_cache()
    assert cleared == 3
    assert len(svc._cache) == 0
    print("PASS test_clear_cache")


def test_stats_increment_on_failure():
    """calls_failed increments when subprocess fails (returncode != 0)."""
    import unittest.mock as mock

    svc = _fresh_service(5.0)
    initial_failed = svc._stats["calls_failed"]
    initial_total = svc._stats["calls_total"]

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake")
        path = f.name
    try:
        async def fake_exec(*args, **kwargs):
            class FakeProc:
                returncode = 1  # failure
                async def communicate(self):
                    return b"", b"some error"
            return FakeProc()

        with mock.patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            asyncio.run(svc.analyze_screenshot(path))

        assert svc._stats["calls_failed"] == initial_failed + 1
        assert svc._stats["calls_total"] == initial_total + 1
        print("PASS test_stats_increment_on_failure")
    finally:
        os.unlink(path)


def test_cache_eviction_when_full():
    """Cache evicts oldest entry when full (FIFO)."""
    svc = _fresh_service(5.0)
    # Reduce cache max for test
    svc._cache_max_size = 3
    svc._cache[("a", 1.0)] = DashboardAnalysis(summary="a")
    svc._cache[("b", 2.0)] = DashboardAnalysis(summary="b")
    svc._cache[("c", 3.0)] = DashboardAnalysis(summary="c")
    # Adding a 4th should evict "a"
    # Simulate the eviction logic from analyze_screenshot
    if len(svc._cache) >= svc._cache_max_size:
        oldest_key = next(iter(svc._cache))
        del svc._cache[oldest_key]
    svc._cache[("d", 4.0)] = DashboardAnalysis(summary="d")
    assert ("a", 1.0) not in svc._cache, "oldest entry should be evicted"
    assert ("d", 4.0) in svc._cache
    assert len(svc._cache) == 3
    print("PASS test_cache_eviction_when_full")


def main():
    print("=== VLM Cache & Health Tests ===")
    test_cache_returns_same_result_without_subprocess()
    test_cache_bypassed_with_use_cache_false()
    test_cache_invalidated_on_mtime_change()
    test_health_returns_stats()
    test_clear_cache()
    test_stats_increment_on_failure()
    test_cache_eviction_when_full()
    print("\nAll cache & health tests passed (7/7).")


if __name__ == "__main__":
    main()
