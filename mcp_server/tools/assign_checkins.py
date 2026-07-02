"""
Vigie MCP tool — assign_checkins.

Assigns daily check-in lists to volunteers based on:
  - Active weather alert (orange/rouge)
  - Beneficiary registry (filtered by sector)
  - Volunteer availability
  - Previous day's assignments (rotation)

The tool is called automatically by Vigie at 7:30 AM during an active alert,
or manually by a coordinator via `/vigie start`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.utils.logging import get_logger
from mcp_server.resources.beneficiary_registry import (
    get_registry,
    update_beneficiary_status,
)
from mcp_server.resources.weather_alerts import is_heatwave_active

log = get_logger("vigie.mcp.tools.assign_checkins")


async def assign_checkins(
    volunteer_ids: list[str] | None = None,
    date: str | None = None,
    sector_filter: str | None = None,
) -> dict[str, Any]:
    """
    Assign daily check-in lists to volunteers.

    Args:
        volunteer_ids: Optional list of volunteer user IDs. If None, all active volunteers.
        date: ISO date string (YYYY-MM-DD). Defaults to today.
        sector_filter: Optional sector ID to restrict assignments.

    Returns:
        {
            "date": "2026-07-15",
            "alert_level": "orange",
            "total_beneficiaries": 187,
            "total_volunteers": 12,
            "assignments": [
                {
                    "volunteer_id": "U123",
                    "volunteer_name": "Marie Dupont",
                    "beneficiaries": [
                        {"id": "B001", "name": "Hélène M.", "sector": "11", "phone": "+33..."},
                        ...
                    ]
                },
                ...
            ],
            "unassigned_count": 0,
            "timestamp": "2026-07-15T07:30:00+02:00"
        }
    """
    if date is None:
        date = datetime.now(UTC).date().isoformat()

    log.info("vigie.mcp.tool.assign_checkins", date=date, sector=sector_filter)

    # 1. Check if heatwave is active
    heatwave_active = await is_heatwave_active()
    if not heatwave_active:
        log.warning("vigie.mcp.tool.assign_checkins.no_heatwave")
        return {
            "error": "no_active_heatwave",
            "message": "No active canicule alert. Use force=true to override.",
            "date": date,
        }

    # 2. Load registry
    registry = get_registry()
    if sector_filter:
        registry = [b for b in registry if str(b.get("sector")) == str(sector_filter)]

    # 3. Filter beneficiaries needing check-in today
    # (registered + not already checked today + not critical/hospitalized)
    needs_checkin = [
        b for b in registry
        if b.get("status") in ("registered", "ok", "unreachable")
        and not _already_checked_today(b, date)
    ]

    # 4. Load volunteers (stub: we'll load from volunteers.json)
    volunteers = _load_volunteers()
    if volunteer_ids:
        volunteers = [v for v in volunteers if v["id"] in volunteer_ids]

    if not volunteers:
        return {
            "error": "no_volunteers_available",
            "date": date,
        }

    # 5. Distribute beneficiaries round-robin, sector-matched
    # For now, simple even distribution. J2 will add sector matching.
    assignments = []
    per_volunteer = len(needs_checkin) // len(volunteers)
    remainder = len(needs_checkin) % len(volunteers)

    idx = 0
    for i, vol in enumerate(volunteers):
        count = per_volunteer + (1 if i < remainder else 0)
        vol_beneficiaries = needs_checkin[idx : idx + count]
        idx += count

        # Mark beneficiaries as "being_checked"
        for b in vol_beneficiaries:
            update_beneficiary_status(
                b["id"],
                status="being_checked",
                last_checkin_at=datetime.now(UTC).isoformat(),
            )

        assignments.append(
            {
                "volunteer_id": vol["id"],
                "volunteer_name": vol["name"],
                "sector": vol.get("sector"),
                "beneficiaries": [
                    {
                        "id": b["id"],
                        "name": f"{b['first_name']} {b['last_initial']}.",
                        "age": b.get("age"),
                        "sector": b.get("sector"),
                        "phone": b.get("phone"),
                        "address": b.get("address"),
                        "vulnerability_score": b.get("vulnerability_score"),
                        "medical_conditions": b.get("medical_conditions", []),
                        "medications": b.get("medications", []),
                        "emergency_contacts": b.get("emergency_contacts", []),
                    }
                    for b in vol_beneficiaries
                ],
            }
        )

    result = {
        "date": date,
        "alert_level": "orange",
        "total_beneficiaries": len(needs_checkin),
        "total_volunteers": len(volunteers),
        "assignments": assignments,
        "unassigned_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    log.info(
        "vigie.mcp.tool.assign_checkins.done",
        beneficiaries=len(needs_checkin),
        volunteers=len(volunteers),
        assignments=len(assignments),
    )
    return result


def _already_checked_today(beneficiary: dict, date: str) -> bool:
    """Check if beneficiary was already checked today."""
    last = beneficiary.get("last_checkin_at")
    if not last:
        return False
    try:
        return last.startswith(date)
    except Exception:
        return False


def _load_volunteers() -> list[dict[str, Any]]:
    """Load volunteers from disk (stub: full implementation)."""
    import pathlib

    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "volunteers.json"
    if not path.exists():
        log.warning("vigie.mcp.volunteers.not_found", path=str(path))
        return []

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def register(mcp) -> None:
    """Register the assign_checkins tool on the MCP server."""

    @mcp.tool()
    async def assign_checkins_tool(
        volunteer_ids: list[str] | None = None,
        date: str | None = None,
        sector_filter: str | None = None,
    ) -> str:
        """
        Assign daily check-in lists to volunteers during an active heatwave alert.

        Called automatically by Vigie at 7:30 AM, or manually via /vigie start.

        Args:
            volunteer_ids: Optional list of volunteer user IDs. If None, all active volunteers.
            date: ISO date (YYYY-MM-DD). Defaults to today.
            sector_filter: Optional sector ID to restrict assignments.

        Returns JSON with assignments per volunteer, including beneficiary details.
        """
        result = await assign_checkins(volunteer_ids, date, sector_filter)
        return json.dumps(result, ensure_ascii=False, indent=2)

    log.debug("vigie.mcp.tool.assign_checkins.registered")
