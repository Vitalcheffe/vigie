"""
Vigie — Real-Time Search API service.

Wraps Slack's Real-Time Search API to surface fresh, in-workspace and
external context. Vigie uses RTS for:
  - current health directives (Ministère, ARS, CDC, WHO)
  - local canicule news
  - municipal/EHPAD opening hours during crisis

Results are cached for RTS_CACHE_TTL_SECONDS (default 30 min during alert)
to avoid hammering the API on every check-in.

If the RTS API is not configured (no endpoint / no key), the service
returns simulated directives so the demo still works end-to-end.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.services.rts")


# Default simulated directives (used when RTS API is not configured).
# These mimic the shape of real ARS / Ministry of Health communiqués
# so the agent can cite plausible sources during the demo.
_SIMULATED_DIRECTIVES = [
    {
        "source": "ARS Île-de-France",
        "url": "https://www.iledefrance.ars.sante.fr/",
        "published_at": "2026-07-15T08:30:00+02:00",
        "title": "Canicule — activation du niveau 3 du plan canicule",
        "summary": (
            "Activation du niveau 3 (mobilisation maximale) en Île-de-France. "
            "Recommandation aux personnes isolées de plus de 75 ans de contacter le 15 "
            "en cas de signe d'alerte (confusion, fatigue intense, difficulté à respirer)."
        ),
    },
    {
        "source": "Ministère de la Santé",
        "url": "https://sante.gouv.fr/canicule",
        "published_at": "2026-07-15T06:00:00+02:00",
        "title": "Communiqué — vigilance orange canicule sur 32 départements",
        "summary": (
            "Vigilance orange maintenue sur 32 départements. Fortes chaleurs attendues "
            "jusqu'au 18 juillet. Retrouvez les recommandations sur le site canicule.info "
            "et le numéro d'information Canicule Info Service : 0 800 06 66 66."
        ),
    },
    {
        "source": "Mairie de Paris",
        "url": "https://www.paris.fr/canicule",
        "published_at": "2026-07-15T07:15:00+02:00",
        "title": "Ouverture des 12 îlots de fraîcheur parisiens",
        "summary": (
            "Les 12 îlots de fraîcheur parisiens sont ouverts 24h/24 jusqu'à la fin de la vigilance orange. "
            "Consultez la carte interactive sur paris.fr/canicule. Pour les personnes isolées, "
            "le service Paris Ville Amie des Aînés reste joignable au 3975."
        ),
    },
]


class RTSService:
    """Real-Time Search API wrapper with TTL caching."""

    def __init__(self) -> None:
        cfg = get_config().rts
        self.endpoint = cfg.api_endpoint
        self.api_key = cfg.api_key.get_secret_value() if cfg.api_key else None
        self.ttl = cfg.cache_ttl_seconds
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._is_simulated = not (self.endpoint and self.api_key)
        if self._is_simulated:
            log.warning("rts.using_simulation_mode", reason="endpoint_or_key_missing")

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        freshness_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Search the RTS API for fresh results matching `query`.

        Returns a list of dicts with: source, url, published_at, title, summary.

        Results are cached for self.ttl seconds per query.
        """
        cache_key = f"{query}:{max_results}:{freshness_hours}"
        now = time.time()

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and (now - cached[0]) < self.ttl:
                log.debug("rts.cache_hit", query=query)
                return cached[1]

        if self._is_simulated:
            results = self._simulate(query, max_results)
        else:
            try:
                results = await self._call_rts(query, max_results, freshness_hours)
            except Exception as e:
                log.warning("rts.api_failed_falling_back_to_simulation", error=str(e))
                results = self._simulate(query, max_results)

        async with self._lock:
            self._cache[cache_key] = (now, results)
        return results

    async def get_health_directives(self, department: str | None = None) -> list[dict[str, Any]]:
        """
        Convenience method: get current health directives for heatwave response.

        Args:
            department: Optional French department code (e.g., "75") to scope results.
        """
        query = "canicule directives sanitaires ARS"
        if department:
            query += f" département {department}"
        return await self.search(query, max_results=5, freshness_hours=24)

    async def get_local_news(self, sector_label: str) -> list[dict[str, Any]]:
        """
        Convenience method: get local news related to the heatwave for a given sector.

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
        """Invalidate all cached results. Useful for tests or admin commands."""
        self._cache.clear()
        log.info("rts.cache_cleared")

    # ============================================================
    # Internal: real API call + simulation
    # ============================================================

    async def _call_rts(
        self,
        query: str,
        max_results: int,
        freshness_hours: int,
    ) -> list[dict[str, Any]]:
        """Call the Real-Time Search API. The exact request schema depends on
        the Slack-provided endpoint; this implementation follows the
        typical JSON contract (query, freshness, max_results)."""
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

        # Normalize response shape into our standard 5-field dict.
        items = data.get("results", []) if isinstance(data, dict) else []
        normalized: list[dict[str, Any]] = []
        for item in items:
            normalized.append(
                {
                    "source": item.get("source") or item.get("publisher") or "unknown",
                    "url": item.get("url") or item.get("link") or "",
                    "published_at": item.get("published_at") or item.get("date") or "",
                    "title": item.get("title", ""),
                    "summary": item.get("summary") or item.get("snippet") or "",
                }
            )
        log.debug("rts.api_called", query=query, returned=len(normalized))
        return normalized

    def _simulate(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Return simulated directives matching the query (substring match)."""
        q = query.lower()
        results = []
        for d in _SIMULATED_DIRECTIVES:
            haystack = (d["title"] + " " + d["summary"] + " " + d["source"]).lower()
            if any(term in haystack for term in q.split()):
                results.append(d)
            if len(results) >= max_results:
                break
        # If nothing matched, return the first N as fallback
        if not results:
            results = _SIMULATED_DIRECTIVES[:max_results]
        return results


# Singleton
_service: RTSService | None = None


def get_rts_service() -> RTSService:
    global _service
    if _service is None:
        _service = RTSService()
    return _service
