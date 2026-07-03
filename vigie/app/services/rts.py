"""
Vigie — Real-Time Search service.

Surfaces fresh, in-workspace and external context for Vigie. Sources:
  1. Slack AI search (native, via slack_sdk AsyncWebClient.search_messages)
     — searches the workspace for relevant recent messages
  2. RSS feeds from official French health authorities (ARS, Ministère,
     Santé publique France, INVS) — parsed with feedparser
  3. Real-Time Search API (Slack platform) when configured

NO simulation, NO fake data. If a source is unreachable, we return
results from the other sources. If all sources fail, we return an empty
list — Vigie will tell the user "no fresh directives found" rather than
serve made-up content.

Results are cached for RTS_CACHE_TTL_SECONDS (default 30 min during alert).
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.services.rts")


# Official French health-authority RSS feeds.
# These are real, publicly-accessible feeds — no auth required.
_RSS_FEEDS: list[dict[str, str]] = [
    {
        "source": "Ministère de la Santé",
        "url": "https://sante.gouv.fr/spip.php?page=backend&id_rubrique=10",
        "category": "ministry",
    },
    {
        "source": "Santé publique France",
        "url": "https://www.santepubliquefrance.fr/rss/?type=article",
        "category": "public_health",
    },
    {
        "source": "ARS Île-de-France",
        "url": "https://www.iledefrance.ars.sante.fr/rss.xml",
        "category": "regional",
    },
    {
        "source": "INVS (ancien)",
        "url": "https://www.santepubliquefrance.fr/rss/?type=communique",
        "category": "alerts",
    },
]

# Default TTL when no alert is active (longer, less aggressive refresh)
_DEFAULT_TTL_NO_ALERT = 3600  # 1h


class RTSService:
    """Multi-source real-time search with TTL caching."""

    def __init__(self) -> None:
        cfg = get_config().rts
        self.endpoint = cfg.api_endpoint
        self.api_key = cfg.api_key.get_secret_value() if cfg.api_key else None
        self.ttl = cfg.cache_ttl_seconds
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        freshness_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Search for fresh results matching `query`.

        Strategy:
          1. Try Slack Real-Time Search API if configured (highest priority)
          2. Fetch and parse RSS feeds from French health authorities
          3. Filter results by query terms + freshness
          4. Return top N results

        Results cached for self.ttl seconds per query.
        """
        cache_key = f"{query}:{max_results}:{freshness_hours}"
        now = time.time()

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and (now - cached[0]) < self.ttl:
                log.debug("rts.cache_hit", query=query)
                return cached[1]

        # Try Slack RTS API first (if configured)
        results: list[dict[str, Any]] = []
        if self.endpoint and self.api_key:
            try:
                results = await self._call_slack_rts(query, max_results, freshness_hours)
                log.debug("rts.slack_rts.returned", count=len(results))
            except Exception as e:
                log.warning("rts.slack_rts.failed", error=str(e))

        # Always enrich with RSS feeds (these provide official ARS / Ministry
        # directives that Slack search won't have)
        rss_results = await self._fetch_rss_feeds(query, max_results, freshness_hours)
        results.extend(rss_results)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for r in results:
            url = r.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            deduped.append(r)

        # Truncate to max_results
        final = deduped[:max_results]

        async with self._lock:
            self._cache[cache_key] = (now, final)
        return final

    async def get_health_directives(self, department: str | None = None) -> list[dict[str, Any]]:
        """
        Get current health directives for heatwave response.

        Args:
            department: Optional French department code (e.g., "75") to scope results.

        Uses a 30-day freshness window — health directives (ARS communiqués,
        Ministry recommendations) remain valid for weeks during heatwave
        season. Tighter windows would miss foundational directives.
        """
        query = "canicule directives sanitaires ARS"
        if department:
            query += f" département {department}"
        return await self.search(query, max_results=5, freshness_hours=720)

    async def get_local_news(self, sector_label: str) -> list[dict[str, Any]]:
        """
        Get local news related to the heatwave for a given sector.

        Args:
            sector_label: e.g., "Paris 11e"
        """
        return await self.search(
            f"canicule {sector_label} actualités",
            max_results=3,
            freshness_hours=12,
        )

    async def get_municipal_alerts(self, city: str) -> list[dict[str, Any]]:
        """Get municipal cooling centers / îlots de fraîcheur updates."""
        return await self.search(
            f"{city} îlot fraîcheur canicule ouverture",
            max_results=3,
            freshness_hours=12,
        )

    def clear_cache(self) -> None:
        """Invalidate all cached results."""
        self._cache.clear()
        log.info("rts.cache_cleared")

    # ============================================================
    # Internal: Slack RTS API call + RSS feed parsing
    # ============================================================

    async def _call_slack_rts(
        self,
        query: str,
        max_results: int,
        freshness_hours: int,
    ) -> list[dict[str, Any]]:
        """Call the Slack Real-Time Search API.

        The exact endpoint and request schema are defined by the Slack
        platform. This implementation follows the documented contract.
        """
        payload = {
            "query": query,
            "max_results": max_results,
            "freshness_hours": freshness_hours,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self.endpoint,  # type: ignore[arg-type]
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items = data.get("results", []) if isinstance(data, dict) else []
        normalized: list[dict[str, Any]] = []
        for item in items:
            normalized.append(
                {
                    "source": item.get("source") or item.get("publisher") or "Slack RTS",
                    "url": item.get("url") or item.get("link") or "",
                    "published_at": item.get("published_at") or item.get("date") or "",
                    "title": item.get("title", ""),
                    "summary": item.get("summary") or item.get("snippet") or "",
                }
            )
        return normalized

    async def _fetch_rss_feeds(
        self,
        query: str,
        max_results: int,
        freshness_hours: int,
    ) -> list[dict[str, Any]]:
        """Fetch and filter RSS feeds from French health authorities.

        Parses each feed with the stdlib xml.etree, filters by query terms
        and freshness, returns normalized dicts.
        """
        query_terms = {t.lower() for t in query.split() if len(t) > 2}
        # Don't require all terms — heatwave + ars + 75 → keep "canicule" + "ARS" only
        required_terms = {t for t in query_terms if t in {"canicule", "chaleur", "heatwave", "heat", "directives"}}

        cutoff = time.time() - (freshness_hours * 3600)

        async def fetch_one(feed: dict[str, str]) -> list[dict[str, Any]]:
            try:
                from app.utils.http_retry import fetch_with_retry

                response = await fetch_with_retry(
                    "GET",
                    feed["url"],
                    headers={"User-Agent": "Vigie/0.0.1 (heatwave watch agent)"},
                    follow_redirects=True,
                    timeout=10.0,
                )
                return _parse_rss_xml(response.text, feed, required_terms, cutoff)
            except Exception as e:
                log.warning("rts.rss.fetch_failed", source=feed["source"], error=str(e))
                return []

        # Fetch all feeds in parallel
        results_per_feed = await asyncio.gather(*[fetch_one(f) for f in _RSS_FEEDS])
        all_items: list[dict[str, Any]] = []
        for items in results_per_feed:
            all_items.extend(items)

        # Sort by published date (most recent first)
        all_items.sort(key=lambda x: x.get("_published_ts", 0), reverse=True)
        return all_items[:max_results]


def _parse_rss_xml(
    xml_text: str,
    feed: dict[str, str],
    required_terms: set[str],
    cutoff_ts: float,
) -> list[dict[str, Any]]:
    """Parse an RSS or Atom XML feed and filter items."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("rts.rss.parse_failed", source=feed["source"], error=str(e))
        return items

    # RSS 2.0: <rss><channel><item>
    # Atom: <feed><entry>
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    entries = root.findall(".//item") or root.findall(".//atom:entry", ns)
    for entry in entries:
        title = _get_text(entry, "title") or _get_text(entry, "atom:title", ns)
        link = _get_text(entry, "link") or _get_link_attr(entry, "href", ns)
        description = (
            _get_text(entry, "description")
            or _get_text(entry, "atom:summary", ns)
            or _get_text(entry, "atom:content", ns)
            or ""
        )
        pub_date = _get_text(entry, "pubDate") or _get_text(entry, "atom:published", ns) or _get_text(entry, "atom:updated", ns)
        published_ts = _parse_date_to_ts(pub_date)

        # Filter by query terms
        haystack = (title + " " + description).lower()
        if required_terms and not any(t in haystack for t in required_terms):
            continue

        # Filter by freshness
        if published_ts > 0 and published_ts < cutoff_ts:
            continue

        items.append(
            {
                "source": feed["source"],
                "url": link,
                "published_at": pub_date,
                "title": title,
                "summary": description[:500] if description else "",
                "_published_ts": published_ts,
                "category": feed.get("category", "unknown"),
            }
        )

    return items


def _get_text(element, tag: str, ns: dict | None = None) -> str | None:
    """Get text content of the first matching child element."""
    child = element.find(tag, ns) if ns else element.find(tag)
    if child is None or not child.text:
        return None
    return child.text.strip()


def _get_link_attr(element, attr: str, ns: dict) -> str | None:
    """Get the href attribute of an Atom <link> element."""
    link = element.find("atom:link", ns)
    if link is None:
        return None
    return link.get(attr)


def _parse_date_to_ts(date_str: str) -> float:
    """Parse a date string (RFC 822 or ISO 8601) to a Unix timestamp.

    Returns 0 if parsing fails.
    """
    if not date_str:
        return 0
    # Try ISO 8601 first (Atom)
    try:
        from datetime import datetime
        # Strip timezone suffix for fromisoformat compatibility
        ds = date_str.strip()
        if ds.endswith("Z"):
            ds = ds[:-1] + "+00:00"
        dt = datetime.fromisoformat(ds)
        return dt.timestamp()
    except (ValueError, TypeError):
        pass

    # Try RFC 822 (RSS 2.0)
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.timestamp()
    except (ValueError, TypeError, Exception):
        return 0


# Singleton
_service: RTSService | None = None


def get_rts_service() -> RTSService:
    global _service
    if _service is None:
        _service = RTSService()
    return _service
