"""Tests: Real-Time Search service (with mocked HTTP)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.rts import RTSService, get_rts_service


@pytest.mark.asyncio
async def test_rts_search_returns_empty_when_all_sources_fail():
    """When all RSS feeds are unreachable AND no Slack RTS configured,
    search should return an empty list — NOT fake data."""
    import httpx

    svc = RTSService()
    # No endpoint configured → no Slack RTS call
    svc.endpoint = None
    svc.api_key = None
    svc._cache.clear()

    # Mock httpx.AsyncClient.get to always raise
    class _FailClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            raise httpx.ConnectError("simulated DNS failure")

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("simulated DNS failure")

    with patch("app.services.rts.httpx.AsyncClient", _FailClient):
        results = await svc.search("canicule", max_results=5)

    assert results == []
    # Verify NO simulation was served
    assert not any(r.get("source") == "simulated" for r in results)


@pytest.mark.asyncio
async def test_rts_search_returns_results_from_rss_feed():
    """A valid RSS feed should produce normalized results."""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Santé publique France</title>
    <item>
      <title>Canicule — recommandations sanitaires</title>
      <link>https://www.santepubliquefrance.fr/canicule-2026</link>
      <description>Activité de niveau 3 du plan canicule.</description>
      <pubDate>Mon, 14 Jul 2026 08:00:00 +0200</pubDate>
    </item>
    <item>
      <title>Grippe saisonnière — bilan hebdomadaire</title>
      <link>https://www.santepubliquefrance.fr/grippe-2026</link>
      <description>Activité faible.</description>
      <pubDate>Mon, 14 Jul 2026 08:00:00 +0200</pubDate>
    </item>
  </channel>
</rss>
"""

    svc = RTSService()
    svc.endpoint = None
    svc.api_key = None
    svc._cache.clear()

    class _OkClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            class _Resp:
                status_code = 200

                def raise_for_status(self):
                    pass

                @property
                def text(self):
                    return rss_xml

            return _Resp()

        async def post(self, *args, **kwargs):
            raise RuntimeError("should not be called")

    with patch("app.services.rts.httpx.AsyncClient", _OkClient):
        results = await svc.search("canicule", max_results=5, freshness_hours=720)

    # Should only return the canicule item (filtered by query terms)
    assert len(results) >= 1
    canicule_results = [r for r in results if "canicule" in r.get("title", "").lower()]
    assert len(canicule_results) >= 1
    assert canicule_results[0]["url"] == "https://www.santepubliquefrance.fr/canicule-2026"


@pytest.mark.asyncio
async def test_rts_cache_returns_same_results_within_ttl():
    """Two calls within TTL should hit the cache and return the same data."""
    svc = RTSService()
    svc.endpoint = None
    svc.api_key = None
    svc.ttl = 60
    svc._cache.clear()

    # Patch the internal fetch to return a known list
    async def fake_fetch(query, max_results, freshness_hours):
        return [{"source": "test", "title": query, "url": "https://example.org", "summary": "", "published_at": "", "_published_ts": 0}]

    with patch.object(svc, "_fetch_rss_feeds", side_effect=fake_fetch):
        results1 = await svc.search("canicule", max_results=3)
        results2 = await svc.search("canicule", max_results=3)

    assert results1 == results2
    assert len(svc._cache) == 1


@pytest.mark.asyncio
async def test_rts_clear_cache_invalidates():
    """clear_cache should empty the cache."""
    svc = RTSService()
    svc._cache["fake_key"] = (0.0, [])
    assert len(svc._cache) == 1
    svc.clear_cache()
    assert len(svc._cache) == 0


@pytest.mark.asyncio
async def test_rts_get_health_directives_returns_list():
    """Convenience method should return a list (possibly empty)."""
    svc = RTSService()
    svc.endpoint = None
    svc.api_key = None
    svc._cache.clear()

    # Patch the internal fetch to return empty (no RSS available)
    async def empty_fetch(query, max_results, freshness_hours):
        return []

    with patch.object(svc, "_fetch_rss_feeds", side_effect=empty_fetch):
        directives = await svc.get_health_directives(department="75")

    assert isinstance(directives, list)


def test_rts_singleton_returns_same_instance():
    """get_rts_service should return the same instance on repeated calls."""
    a = get_rts_service()
    b = get_rts_service()
    assert a is b
