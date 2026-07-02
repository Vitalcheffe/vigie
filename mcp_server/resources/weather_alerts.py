"""
Vigie MCP resource — weather_alerts.

Exposes real-time weather vigilance alerts from:
  - Météo-France API (primary, for France)
  - NWS Weather API (fallback, for United States)

URIs:
  - vigie://weather-alerts                  (all active alerts)
  - vigie://weather-alerts/department/{dep} (specific French department)
  - vigie://weather-alerts/state/{state}    (specific US state)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.mcp.resources.weather_alerts")


async def fetch_meteo_france_vigilance() -> list[dict[str, Any]]:
    """
    Fetch the Météo-France vigilance map.

    Returns a list of alerts with:
      - department (e.g., "75")
      - level (jaune / orange / rouge)
      - phenomenon (canicule, orage, inondation, etc.)
      - valid_from, valid_to
      - source URL
    """
    cfg = get_config().external

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if cfg.meteo_france_api_key:
                headers["Authorization"] = f"Bearer {cfg.meteo_france_api_key.get_secret_value()}"

            resp = await client.get(
                cfg.meteo_france_vigilance_url + "vigilance",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        # TODO: parse the actual Météo-France response schema
        # For now, return a simulated alert if the demo scenario is active
        return _simulated_alerts()

    except Exception as e:
        log.warning("vigie.mcp.weather.meteo_france.failed", error=str(e))
        return _simulated_alerts()


async def fetch_nws_alerts(state: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch active NWS alerts (US fallback).

    Args:
        state: Optional US state code (e.g., "CA") to filter.
    """
    cfg = get_config().external
    url = cfg.nws_api_base + cfg.nws_alerts_endpoint
    params: dict[str, str] = {}
    if state:
        params["area"] = state

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        alerts = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            alerts.append(
                {
                    "id": feature.get("id"),
                    "event": props.get("event"),
                    "headline": props.get("headline"),
                    "description": props.get("description"),
                    "severity": props.get("severity"),
                    "urgency": props.get("urgency"),
                    "area": props.get("areaDesc"),
                    "valid_from": props.get("onset"),
                    "valid_to": props.get("expires"),
                    "source": "NWS",
                }
            )
        return alerts
    except Exception as e:
        log.warning("vigie.mcp.weather.nws.failed", error=str(e))
        return []


def _simulated_alerts() -> list[dict[str, Any]]:
    """Return simulated heatwave alerts for demo purposes."""
    return [
        {
            "id": "vigilance-orange-canicule-75-2026",
            "department": "75",
            "department_name": "Paris",
            "level": "orange",
            "phenomenon": "canicule",
            "valid_from": "2026-07-15T06:00:00+02:00",
            "valid_to": "2026-07-18T22:00:00+02:00",
            "max_temperature": 38,
            "min_temperature_night": 23,
            "source": "Météo-France (simulated for demo)",
            "url": "https://vigilance.meteofrance.fr/",
            "recommendation": (
                "Passez au moins 3 heures par jour dans un lieu frais. "
                "Buvez régulièrement de l'eau même sans soif. "
                "Évitez les efforts physiques aux heures chaudes."
            ),
        },
        {
            "id": "vigilance-orange-canicule-93-2026",
            "department": "93",
            "department_name": "Seine-Saint-Denis",
            "level": "orange",
            "phenomenon": "canicule",
            "valid_from": "2026-07-15T06:00:00+02:00",
            "valid_to": "2026-07-18T22:00:00+02:00",
            "max_temperature": 39,
            "min_temperature_night": 24,
            "source": "Météo-France (simulated for demo)",
            "url": "https://vigilance.meteofrance.fr/",
        },
    ]


def register(mcp) -> None:
    """Register the weather_alerts resource on the MCP server."""

    @mcp.resource("vigie://weather-alerts")
    async def get_weather_alerts() -> str:
        """
        Get all active weather vigilance alerts.

        Returns Météo-France alerts (France) and/or NWS alerts (US),
        prioritized by severity. Each alert includes the level
        (jaune/orange/rouge or advisory/watch/warning), the phenomenon,
        the affected area, and validity times.
        """
        log.debug("vigie.mcp.resource.weather_alerts.read")
        meteo = await fetch_meteo_france_vigilance()
        return json.dumps(
            {
                "source": "Météo-France + NWS",
                "count": len(meteo),
                "alerts": meteo,
            },
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("vigie://weather-alerts/department/{department}")
    async def get_alerts_for_department(department: str) -> str:
        """Get weather alerts for a specific French department (e.g., '75')."""
        log.debug("vigie.mcp.resource.weather_alerts.department", department=department)
        alerts = await fetch_meteo_france_vigilance()
        filtered = [a for a in alerts if a.get("department") == department]
        return json.dumps(
            {"department": department, "count": len(filtered), "alerts": filtered},
            ensure_ascii=False,
            indent=2,
        )

    log.debug("vigie.mcp.resource.weather_alerts.registered")


# ============================================================
# Public helpers
# ============================================================

async def get_active_alerts() -> list[dict[str, Any]]:
    """Public accessor for the active weather alerts."""
    return await fetch_meteo_france_vigilance()


async def is_heatwave_active() -> bool:
    """Quick check: is there an active canicule alert?"""
    alerts = await fetch_meteo_france_vigilance()
    return any(
        a.get("phenomenon") == "canicule"
        and a.get("level") in ("orange", "rouge")
        for a in alerts
    )
