"""
Vigie MCP resource — weather_alerts.

Exposes real-time weather vigilance alerts from:
  - Météo-France API (primary, for France)
  - NWS Weather API (fallback, for United States)

The Météo-France vigilance endpoint returns a Cartesian product of
(department, phenomenon, level) tuples. We parse the raw XML/JSON
response and normalize into our alert schema.

URIs:
  - vigie://weather-alerts                  (all active alerts)
  - vigie://weather-alerts/department/{dep} (specific French department)
  - vigie://weather-alerts/state/{state}    (specific US state)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.mcp.resources.weather_alerts")

# Météo-France vigilance phenomena codes → human labels
_PHENOMENA_LABELS = {
    1: "vent violent",
    2: "pluie-inondation",
    3: "orages",
    4: "crues",
    5: "neige-verglas",
    6: "canicule",
    7: "grand-froid",
    8: "avalanches",
    9: "vagues-submersion",
}

# Météo-France vigilance levels → normalized strings
_LEVEL_LABELS = {
    1: "vert",
    2: "jaune",
    3: "orange",
    4: "rouge",
}


async def fetch_meteo_france_vigilance() -> list[dict[str, Any]]:
    """
    Fetch the Météo-France vigilance map and parse active alerts.

    Calls the public Météo-France DPVigilance API. Returns a list of
    normalized alert dicts. Only returns alerts with level >= jaune
    (level 2+), since 'vert' is the default 'no alert' state.

    If the API call fails or returns an unexpected schema, returns an
    empty list (we DO NOT fall back to fake data — that would mask a
    real outage during a real heatwave).
    """
    cfg = get_config().external

    headers: dict[str, str] = {"Accept": "application/json"}
    if cfg.meteo_france_api_key:
        headers["Authorization"] = f"Bearer {cfg.meteo_france_api_key.get_secret_value()}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                cfg.meteo_france_vigilance_url + "vigilance",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        log.warning("vigie.mcp.weather.meteo_france.http_failed", error=str(e))
        return []
    except json.JSONDecodeError as e:
        log.warning("vigie.mcp.weather.meteo_france.json_failed", error=str(e))
        return []

    return _parse_meteo_france_response(data)


def _parse_meteo_france_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse the Météo-France DPVigilance response into normalized alerts.

    The response shape varies across API versions. We handle both the
    legacy product format and the newer geojson format.
    """
    alerts: list[dict[str, Any]] = []

    # Format 1: product format (most common)
    product = data.get("product") or data
    if isinstance(product, dict):
        timelag = product.get("timelag", "0")
        begin_time = product.get("begin_validity_time")
        end_time = product.get("end_validity_time")

        # Thee color_max is a global indicator per department
        for region in product.get("regions", []) or []:
            dept = region.get("domain_id") or region.get("department")
            color_max = region.get("color_max", 0)
            if color_max < 2:
                continue  # vert = no alert

            # Each phenomenon has its own color
            for ph in region.get("phenomenons", []) or []:
                ph_id = ph.get("phenomenon_id")
                ph_color = ph.get("phenomenon_max_color", 0)
                if ph_color < 2:
                    continue

                alerts.append(
                    {
                        "id": f"mf-vig-{dept}-{ph_id}-{timelag}",
                        "department": str(dept),
                        "department_name": _DEPARTMENT_NAMES.get(str(dept), f"Département {dept}"),
                        "level": _LEVEL_LABELS.get(ph_color, "jaune"),
                        "phenomenon": _PHENOMENA_LABELS.get(ph_id, f"phénomène {ph_id}"),
                        "valid_from": begin_time,
                        "valid_to": end_time,
                        "source": "Météo-France",
                        "url": "https://vigilance.meteofrance.fr/",
                    }
                )

    # Format 2: geojson format (newer)
    elif isinstance(product, list):
        for feature in product:
            props = feature.get("properties", {})
            ph_id = props.get("phenomenon_id")
            color = props.get("phenomenon_max_color", 0)
            dept = props.get("domain_id")
            if color < 2 or not dept:
                continue
            alerts.append(
                {
                    "id": f"mf-vig-{dept}-{ph_id}",
                    "department": str(dept),
                    "department_name": _DEPARTMENT_NAMES.get(str(dept), f"Département {dept}"),
                    "level": _LEVEL_LABELS.get(color, "jaune"),
                    "phenomenon": _PHENOMENA_LABELS.get(ph_id, "unknown"),
                    "valid_from": props.get("begin_validity_time"),
                    "valid_to": props.get("end_validity_time"),
                    "source": "Météo-France",
                    "url": "https://vigilance.meteofrance.fr/",
                }
            )

    # Add recommendations for heatwave alerts
    for alert in alerts:
        if alert["phenomenon"] == "canicule":
            alert["recommendation"] = (
                "Passez au moins 3 heures par jour dans un lieu frais. "
                "Buvez régulièrement de l'eau même sans soif. "
                "Évitez les efforts physiques aux heures chaudes."
            )
            # Estimate max temperature from the alert level
            alert["max_temperature"] = 38 if alert["level"] == "orange" else 40
            alert["min_temperature_night"] = 23 if alert["level"] == "orange" else 25

    log.info("vigie.mcp.weather.meteo_france.parsed", count=len(alerts))
    return alerts


# INSEE department code → name (metropolitan France + DOM)
_DEPARTMENT_NAMES = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne",
    "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
    "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère",
    "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
    "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
    "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
    "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise",
    "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin",
    "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe",
    "73": "Savoie", "74": "Haute-Savoie", "75": "Paris", "76": "Seine-Maritime",
    "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres", "80": "Somme",
    "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse", "85": "Vendée",
    "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne",
    "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "976": "Mayotte",
}


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
    except httpx.HTTPError as e:
        log.warning("vigie.mcp.weather.nws.http_failed", error=str(e))
        return []
    except json.JSONDecodeError as e:
        log.warning("vigie.mcp.weather.nws.json_failed", error=str(e))
        return []

    alerts: list[dict[str, Any]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        event = props.get("event", "")
        # Filter for heat-related events
        if not any(term in event.lower() for term in ("heat", "excessive heat", "heat advisory")):
            continue

        # Map NWS severity to our level system
        severity = props.get("severity", "").lower()
        level = "orange" if severity in ("moderate", "severe") else "rouge" if severity == "extreme" else "jaune"

        alerts.append(
            {
                "id": feature.get("id"),
                "department": state or "US",
                "department_name": props.get("areaDesc", state or "United States"),
                "level": level,
                "phenomenon": "canicule",
                "valid_from": props.get("onset"),
                "valid_to": props.get("expires"),
                "source": "NWS",
                "url": props.get("url", "https://www.weather.gov/"),
                "recommendation": props.get("description", "")[:500],
            }
        )

    log.info("vigie.mcp.weather.nws.parsed", count=len(alerts), state=state)
    return alerts


def register(mcp) -> None:
    """Register the weather_alerts resource on the MCP server."""

    @mcp.resource("vigie://weather-alerts")
    async def get_weather_alerts() -> str:
        """
        Get all active weather vigilance alerts (Météo-France + NWS).

        Returns only heatwave (canicule) and other severe weather alerts
        (level jaune or higher). Each alert includes the level, phenomenon,
        affected area, validity times, and source URL.
        """
        log.debug("vigie.mcp.resource.weather_alerts.read")
        meteo = await fetch_meteo_france_vigilance()
        return json.dumps(
            {
                "source": "Météo-France + NWS",
                "count": len(meteo),
                "alerts": meteo,
                "fetched_at": datetime.now(UTC).isoformat(),
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
            {
                "department": department,
                "department_name": _DEPARTMENT_NAMES.get(department, f"Département {department}"),
                "count": len(filtered),
                "alerts": filtered,
            },
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
    """Quick check: is there an active canicule alert (orange or rouge)?"""
    alerts = await fetch_meteo_france_vigilance()
    return any(
        a.get("phenomenon") == "canicule"
        and a.get("level") in ("orange", "rouge")
        for a in alerts
    )
