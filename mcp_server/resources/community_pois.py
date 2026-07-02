"""
Vigie MCP resource — community_pois.

Exposes points of interest from OpenStreetMap (Overpass API) useful
during heatwave response:
  - pharmacies (open now)
  - hospitals / clinics
  - drinking water points
  - cooling centers (mairies, EHPAD with public AC)
  - neighbor referents (community volunteers registered per sector)

URIs:
  - vigie://community-pois/{lat}/{lon}/{radius_m}
  - vigie://community-pois/sector/{sector_id}
  - vigie://community-pois/neighbor-referent/{sector_id}
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.mcp.resources.community_pois")


OVERPASS_QUERY_TEMPLATE = """
[out:json][timeout:25];
(
  node["amenity"="pharmacy"](around:{radius},{lat},{lon});
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});
  node["amenity"="drinking_water"](around:{radius},{lat},{lon});
  node["amenity"="community_centre"](around:{radius},{lat},{lon});
  node["amenity"="townhall"](around:{radius},{lat},{lon});
);
out body 50;
"""


async def fetch_pois_around(lat: float, lon: float, radius_m: int = 1000) -> list[dict[str, Any]]:
    """
    Query OpenStreetMap Overpass API for POIs around a given point.

    Args:
        lat: Latitude
        lon: Longitude
        radius_m: Search radius in meters (default 1km)

    Returns a list of POIs with: type, name, lat, lon, address, opening_hours.
    """
    cfg = get_config().external
    query = OVERPASS_QUERY_TEMPLATE.format(lat=lat, lon=lon, radius=radius_m)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(cfg.overpass_api_url, data={"data": query})
            resp.raise_for_status()
            data = resp.json()

        pois = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            amenity = tags.get("amenity", "unknown")
            pois.append(
                {
                    "id": f"osm-{el.get('id')}",
                    "type": amenity,
                    "name": tags.get("name", tags.get("operator", amenity)),
                    "lat": el.get("lat"),
                    "lon": el.get("lon"),
                    "address": {
                        "street": tags.get("addr:street"),
                        "housenumber": tags.get("addr:housenumber"),
                        "postcode": tags.get("addr:postcode"),
                        "city": tags.get("addr:city"),
                    },
                    "opening_hours": tags.get("opening_hours"),
                    "phone": tags.get("phone", tags.get("contact:phone")),
                    "wheelchair": tags.get("wheelchair"),
                    "distance_m": _haversine(lat, lon, el.get("lat"), el.get("lon")),
                }
            )

        # Sort by distance
        pois.sort(key=lambda p: p.get("distance_m", 9999))
        log.debug("vigie.mcp.pois.fetched", count=len(pois), lat=lat, lon=lon, radius=radius_m)
        return pois

    except Exception as e:
        log.warning("vigie.mcp.pois.overpass_failed", error=str(e))
        return _simulated_pois(lat, lon)


def _simulated_pois(lat: float, lon: float) -> list[dict[str, Any]]:
    """Fallback simulated POIs (for offline demo)."""
    return [
        {
            "id": "sim-pharmacy-1",
            "type": "pharmacy",
            "name": "Pharmacie des Lilas",
            "lat": lat + 0.0018,
            "lon": lon + 0.0012,
            "address": {"street": "Rue des Lilas", "housenumber": "12", "postcode": "75020", "city": "Paris"},
            "opening_hours": "Mo-Fr 09:00-19:00; Sa 09:00-13:00",
            "phone": "+33 1 43 00 00 00",
            "distance_m": 200,
        },
        {
            "id": "sim-hospital-1",
            "type": "hospital",
            "name": "Hôpital Saint-Louis",
            "lat": lat + 0.005,
            "lon": lon - 0.003,
            "address": {"street": "Avenue Claude Vellefaux", "housenumber": "1", "postcode": "75010", "city": "Paris"},
            "opening_hours": "24/7",
            "phone": "+33 1 42 49 99 99",
            "distance_m": 850,
        },
        {
            "id": "sim-water-1",
            "type": "drinking_water",
            "name": "Fontaine Place de la République",
            "lat": lat - 0.002,
            "lon": lon + 0.001,
            "address": {"city": "Paris"},
            "opening_hours": "24/7",
            "distance_m": 320,
        },
    ]


def _haversine(lat1: float, lon1: float, lat2: float | None, lon2: float | None) -> float:
    """Compute haversine distance in meters. Returns 9999 if invalid."""
    if lat2 is None or lon2 is None:
        return 9999.0
    import math

    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def register(mcp) -> None:
    """Register the community_pois resource on the MCP server."""

    @mcp.resource("vigie://community-pois/{lat}/{lon}/{radius_m}")
    async def get_pois_around(lat: float, lon: float, radius_m: int) -> str:
        """
        Get community points of interest around a geographic point.

        Args:
            lat: Latitude
            lon: Longitude
            radius_m: Search radius in meters

        Returns pharmacies, hospitals, water points, cooling centers sorted by distance.
        """
        pois = await fetch_pois_around(lat, lon, radius_m)
        return json.dumps(
            {
                "center": {"lat": lat, "lon": lon},
                "radius_m": radius_m,
                "count": len(pois),
                "pois": pois,
            },
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("vigie://community-pois/sector/{sector_id}")
    async def get_pois_for_sector(sector_id: str) -> str:
        """Get POIs for a specific Vigie sector (1..12)."""
        # TODO: load sector centroid from sectors.json
        # For now, use Paris 11e as default
        lat, lon = 48.8590, 2.3790
        pois = await fetch_pois_around(lat, lon, 1500)
        return json.dumps(
            {"sector": sector_id, "count": len(pois), "pois": pois},
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("vigie://community-pois/neighbor-referent/{sector_id}")
    def get_neighbor_referent(sector_id: str) -> str:
        """
        Get the registered neighbor referent(s) for a sector.

        Neighbor referents are community volunteers registered to be
        contacted by Vigie when a beneficiary is unreachable.
        """
        # TODO: load from volunteers.json
        return json.dumps(
            {
                "sector": sector_id,
                "referents": [
                    {
                        "id": f"NR-{sector_id}",
                        "name": "M. Bernard (simulated)",
                        "sector": sector_id,
                        "phone": "+33 6 00 00 00 00",
                        "address_proximity": "Same building as beneficiaries B001, B002",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    log.debug("vigie.mcp.resource.community_pois.registered")
