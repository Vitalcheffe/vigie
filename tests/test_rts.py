"""Tests: Real-Time Search service (simulated mode)."""

from __future__ import annotations

import pytest

from app.services.rts import RTSService, get_rts_service


@pytest.mark.asyncio
async def test_rts_simulated_mode_returns_directives():
    """In simulation mode, search should return plausible directives."""
    svc = RTSService()
    # Force simulation mode by ensuring endpoint is None
    svc._is_simulated = True

    results = await svc.search("canicule directives", max_results=5)

    assert isinstance(results, list)
    assert len(results) >= 1
    for r in results:
        assert "source" in r
        assert "title" in r
        assert "summary" in r


@pytest.mark.asyncio
async def test_rts_cache_returns_same_results_within_ttl():
    """Two calls within TTL should hit the cache and return the same data."""
    svc = RTSService()
    svc._is_simulated = True
    svc._cache.clear()

    results1 = await svc.search("canicule ARS", max_results=3)
    results2 = await svc.search("canicule ARS", max_results=3)

    assert results1 == results2


@pytest.mark.asyncio
async def test_rts_clear_cache_invalidates():
    """clear_cache should empty the cache so next call fetches fresh."""
    svc = RTSService()
    svc._is_simulated = True
    svc._cache.clear()

    await svc.search("canicule", max_results=2)
    assert len(svc._cache) == 1

    svc.clear_cache()
    assert len(svc._cache) == 0


@pytest.mark.asyncio
async def test_rts_get_health_directives_returns_list():
    """Convenience method should return a list of directive dicts."""
    svc = RTSService()
    svc._is_simulated = True

    directives = await svc.get_health_directives(department="75")

    assert isinstance(directives, list)
    assert len(directives) >= 1


@pytest.mark.asyncio
async def test_rts_get_local_news_for_sector():
    """get_local_news should return news items for a sector label."""
    svc = RTSService()
    svc._is_simulated = True

    news = await svc.get_local_news("Paris 11e")

    assert isinstance(news, list)


def test_rts_singleton_returns_same_instance():
    """get_rts_service should return the same instance on repeated calls."""
    a = get_rts_service()
    b = get_rts_service()
    assert a is b
