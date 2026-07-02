"""
Vigie MCP resource — beneficiary_registry.

Exposes the Plan Canicule beneficiary registry as a MCP resource.

The registry contains simulated beneficiary profiles conforming to the
French Plan Canicule schema (Décret n° 2006-1089):
  - id (string)
  - first_name, last_name
  - age
  - sector (1..12)
  - address (street, city, postal_code, lat, lon)
  - phone
  - emergency_contacts (neighbors, family, doctor)
  - medical_conditions (list)
  - medications (list)
  - vulnerability_score (0-100)
  - isolation_level (low / medium / high)
  - notes (free text from previous check-ins)
  - last_checkin_at (timestamp)
  - status (registered / being_checked / ok / unreachable / escalated / critical)

URI: vigie://beneficiary-registry
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.mcp.resources.beneficiary_registry")

# Cache the loaded registry in memory (reloaded on file change)
_registry_cache: list[dict[str, Any]] | None = None
_registry_path: Path | None = None


def _registry_file() -> Path:
    """Resolve the path to the beneficiaries JSON file."""
    cfg = get_config()
    # Default to mcp_server/data/beneficiaries.json
    base = Path(__file__).resolve().parent.parent
    return base / "data" / "beneficiaries.json"


def _load_registry() -> list[dict[str, Any]]:
    """Load the beneficiary registry from disk (with simple caching)."""
    global _registry_cache, _registry_path

    path = _registry_file()
    if _registry_cache is not None and _registry_path == path:
        return _registry_cache

    if not path.exists():
        log.warning("vigie.mcp.registry.not_found", path=str(path))
        # Auto-generate if missing (scripts/generate_beneficiaries.py)
        from scripts.generate_beneficiaries import generate_beneficiaries

        generate_beneficiaries(path, count=get_config().demo.num_beneficiaries)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        log.error("vigie.mcp.registry.invalid_format", path=str(path))
        return []

    _registry_cache = data
    _registry_path = path
    log.info("vigie.mcp.registry.loaded", count=len(data), path=str(path))
    return data


def register(mcp) -> None:
    """Register the beneficiary_registry resource on the MCP server."""

    @mcp.resource("vigie://beneficiary-registry")
    def get_beneficiary_registry() -> str:
        """
        Get the full Plan Canicule beneficiary registry.

        Returns a JSON string with all beneficiaries, including:
        - Personal info (anonymized first name + last initial)
        - Sector assignment
        - Vulnerability score
        - Last check-in status
        - Emergency contacts
        """
        log.debug("vigie.mcp.resource.beneficiary_registry.read")
        registry = _load_registry()
        return json.dumps(
            {
                "schema_version": "1.0",
                "source": "Plan Canicule français (Décret 2006-1089)",
                "disclaimer": "Simulated data — no real beneficiary records",
                "count": len(registry),
                "beneficiaries": registry,
            },
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("vigie://beneficiary-registry/{beneficiary_id}")
    def get_beneficiary(beneficiary_id: str) -> str:
        """
        Get a specific beneficiary by ID.

        Args:
            beneficiary_id: The beneficiary's unique identifier (e.g., "B001")
        """
        log.debug("vigie.mcp.resource.beneficiary.read", id=beneficiary_id)
        registry = _load_registry()
        for b in registry:
            if b.get("id") == beneficiary_id:
                return json.dumps(b, ensure_ascii=False, indent=2)
        return json.dumps(
            {"error": "not_found", "beneficiary_id": beneficiary_id},
            ensure_ascii=False,
            indent=2,
        )

    log.debug("vigie.mcp.resource.beneficiary_registry.registered")


# ============================================================
# Helper functions (used by tools and tests)
# ============================================================

def get_registry() -> list[dict[str, Any]]:
    """Public accessor for the in-memory registry."""
    return _load_registry()


def get_beneficiary_by_id(beneficiary_id: str) -> dict[str, Any] | None:
    """Public accessor for a single beneficiary."""
    for b in _load_registry():
        if b.get("id") == beneficiary_id:
            return b
    return None


def update_beneficiary_status(
    beneficiary_id: str,
    status: str,
    notes: str | None = None,
    last_checkin_at: str | None = None,
) -> bool:
    """
    Update a beneficiary's status in the registry.

    Returns True if updated, False if beneficiary not found.
    """
    registry = _load_registry()
    for b in registry:
        if b.get("id") == beneficiary_id:
            b["status"] = status
            if notes is not None:
                b["notes"] = notes
            if last_checkin_at is not None:
                b["last_checkin_at"] = last_checkin_at
            _save_registry(registry)
            return True
    return False


def _save_registry(registry: list[dict[str, Any]]) -> None:
    """Persist the registry back to disk."""
    path = _registry_file()
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    global _registry_cache
    _registry_cache = registry
    log.debug("vigie.mcp.registry.saved", count=len(registry), path=str(path))
