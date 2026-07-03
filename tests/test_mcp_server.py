"""Tests: MCP server resources and tools (direct unit tests).

These tests call the MCP resource and tool functions directly (without
going through the MCP protocol) to validate the business logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ============================================================
# Resources: beneficiary_registry
# ============================================================


def test_beneficiary_registry_loads_from_disk():
    """The registry should load beneficiaries from the JSON fixture."""
    from mcp_server.resources.beneficiary_registry import get_registry

    registry = get_registry()
    assert isinstance(registry, list)
    assert len(registry) == 50  # our fixture has 50 beneficiaries

    first = registry[0]
    assert "id" in first
    assert "first_name" in first
    assert "sector" in first
    assert "vulnerability_score" in first


def test_beneficiary_registry_get_by_id():
    """get_beneficiary_by_id should return the matching beneficiary."""
    from mcp_server.resources.beneficiary_registry import get_beneficiary_by_id

    b = get_beneficiary_by_id("B001")
    assert b is not None
    assert b["id"] == "B001"


def test_beneficiary_registry_get_unknown_returns_none():
    """get_beneficiary_by_id should return None for unknown IDs."""
    from mcp_server.resources.beneficiary_registry import get_beneficiary_by_id

    assert get_beneficiary_by_id("BXXX") is None


def test_beneficiary_registry_update_status():
    """update_beneficiary_status should persist the new status."""
    from mcp_server.resources.beneficiary_registry import (
        get_beneficiary_by_id,
        update_beneficiary_status,
    )

    success = update_beneficiary_status("B001", status="being_checked", notes="test note")
    assert success is True

    b = get_beneficiary_by_id("B001")
    assert b["status"] == "being_checked"
    assert b["notes"] == "test note"

    # Restore
    update_beneficiary_status("B001", status="registered", notes=None)


# ============================================================
# Resources: weather_alerts
# ============================================================


@pytest.mark.asyncio
async def test_weather_alerts_parse_meteo_france_product_format():
    """The parser should handle the legacy Météo-France product format."""
    from mcp_server.resources.weather_alerts import _parse_meteo_france_response

    mock_response = {
        "product": {
            "timelag": "0",
            "begin_validity_time": "2026-07-15T06:00:00+02:00",
            "end_validity_time": "2026-07-18T22:00:00+02:00",
            "regions": [
                {
                    "domain_id": "75",
                    "color_max": 3,
                    "phenomenons": [
                        {"phenomenon_id": 6, "phenomenon_max_color": 3},  # heatwave orange
                    ],
                },
                {
                    "domain_id": "93",
                    "color_max": 3,
                    "phenomenons": [
                        {"phenomenon_id": 6, "phenomenon_max_color": 3},
                    ],
                },
            ],
        }
    }

    alerts = _parse_meteo_france_response(mock_response)
    assert len(alerts) == 2
    assert alerts[0]["department"] == "75"
    assert alerts[0]["department_name"] == "Paris"
    assert alerts[0]["level"] == "orange"
    assert alerts[0]["phenomenon"] == "heatwave"
    assert "recommendation" in alerts[0]
    assert alerts[0]["max_temperature"] == 38


@pytest.mark.asyncio
async def test_weather_alerts_parse_skips_vert_level():
    """Alerts with color_max < 2 (vert) should be skipped."""
    from mcp_server.resources.weather_alerts import _parse_meteo_france_response

    mock_response = {
        "product": {
            "regions": [
                {
                    "domain_id": "75",
                    "color_max": 1,  # vert
                    "phenomenons": [{"phenomenon_id": 6, "phenomenon_max_color": 1}],
                },
            ],
        }
    }

    alerts = _parse_meteo_france_response(mock_response)
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_weather_alerts_is_heatwave_active_with_no_alerts():
    """is_heatwave_active should return False when no alerts are present."""
    from mcp_server.resources.weather_alerts import is_heatwave_active

    with patch(
        "mcp_server.resources.weather_alerts.fetch_meteo_france_vigilance",
        new=AsyncMock(return_value=[]),
    ):
        result = await is_heatwave_active()
    assert result is False


@pytest.mark.asyncio
async def test_weather_alerts_is_heatwave_active_with_orange_canicule():
    """is_heatwave_active should return True for an orange heatwave alert."""
    from mcp_server.resources.weather_alerts import is_heatwave_active

    mock_alerts = [
        {"phenomenon": "heatwave", "level": "orange", "department": "75"},
    ]
    with patch(
        "mcp_server.resources.weather_alerts.fetch_meteo_france_vigilance",
        new=AsyncMock(return_value=mock_alerts),
    ):
        result = await is_heatwave_active()
    assert result is True


def test_weather_alerts_department_names_mapping():
    """The department name mapping should cover all metropolitan departments."""
    from mcp_server.resources.weather_alerts import _DEPARTMENT_NAMES

    assert _DEPARTMENT_NAMES["75"] == "Paris"
    assert _DEPARTMENT_NAMES["93"] == "Seine-Saint-Denis"
    assert _DEPARTMENT_NAMES["13"] == "Bouches-du-Rhône"
    assert _DEPARTMENT_NAMES["971"] == "Guadeloupe"


# ============================================================
# Resources: community_pois
# ============================================================


def test_community_pois_haversine_distance():
    """The haversine function should compute distances correctly."""
    from mcp_server.resources.community_pois import _haversine

    # Paris 11e to Paris 1er (~3.5 km)
    dist = _haversine(48.8590, 2.3790, 48.8606, 2.3376)
    assert 3000 < dist < 5000  # roughly 3-5 km

    # Same point → 0
    assert _haversine(48.8590, 2.3790, 48.8590, 2.3790) == 0.0

    # None coords → 9999
    assert _haversine(48.8590, 2.3790, None, None) == 9999.0


@pytest.mark.asyncio
async def test_community_pois_fetch_returns_empty_on_failure():
    """fetch_pois_around should return [] (not crash) on HTTP failure."""
    import httpx

    from mcp_server.resources.community_pois import fetch_pois_around

    with patch("mcp_server.resources.community_pois.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("DNS failure"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_pois_around(48.8590, 2.3790, 1000)

    assert result == []


# ============================================================
# Tools: assign_checkins
# ============================================================


@pytest.mark.asyncio
async def test_assign_checkins_no_heatwave_returns_error():
    """assign_checkins should return an error when no heatwave is active."""
    from mcp_server.tools.assign_checkins import assign_checkins

    with patch(
        "mcp_server.tools.assign_checkins.is_heatwave_active",
        new=AsyncMock(return_value=False),
    ):
        result = await assign_checkins()

    assert result["error"] == "no_active_heatwave"


def test_assign_checkins_already_checked_today():
    """The helper should detect same-day check-ins."""
    from mcp_server.tools.assign_checkins import _already_checked_today

    assert _already_checked_today({"last_checkin_at": None}, "2026-07-15") is False
    assert _already_checked_today({"last_checkin_at": "2026-07-15T08:00:00Z"}, "2026-07-15") is True
    assert _already_checked_today({"last_checkin_at": "2026-07-14T08:00:00Z"}, "2026-07-15") is False


# ============================================================
# Tools: record_checkin
# ============================================================


@pytest.mark.asyncio
async def test_record_checkin_classifies_critical_keywords():
    """The keyword classifier should detect critical signals."""
    from mcp_server.tools.record_checkin import _classify_anomaly

    level, signals, recommended = await _classify_anomaly(
        "M. Bernard est au sol, inconscient",
        None,
        {"id": "B001"},
    )
    assert level == 3
    assert "critical_keyword" in signals
    assert recommended == "escalate_samu"


@pytest.mark.asyncio
async def test_record_checkin_classifies_unreachable():
    """The keyword classifier should detect unreachable beneficiaries."""
    from mcp_server.tools.record_checkin import _classify_anomaly

    level, signals, recommended = await _classify_anomaly(
        "Pas de réponse après 3 appels",
        None,
        {"id": "B002"},
    )
    assert level == 2
    assert "unreachable" in signals


@pytest.mark.asyncio
async def test_record_checkin_classifies_medication_request():
    """The keyword classifier should detect medication requests (level 1)."""
    from mcp_server.tools.record_checkin import _classify_anomaly

    level, signals, recommended = await _classify_anomaly(
        "Mme Dupont demande renouvellement ordonnance antihypertenseur",
        None,
        {"id": "B003"},
    )
    assert level == 1
    assert "medication_request" in signals
    assert recommended == "pharmacy"


@pytest.mark.asyncio
async def test_record_checkin_classifies_ok():
    """A normal check-in should classify as level 0 (OK)."""
    from mcp_server.tools.record_checkin import _classify_anomaly

    level, signals, recommended = await _classify_anomaly(
        "Tout va bien, Mme Martin est en forme",
        None,
        {"id": "B004"},
    )
    assert level == 0
    assert signals == []
    assert recommended == "ok"


# ============================================================
# Tools: escalate
# ============================================================


@pytest.mark.asyncio
async def test_escalate_invalid_level_returns_error():
    """Escalate should reject invalid levels (not 1, 2, or 3)."""
    from mcp_server.tools.escalate import escalate

    result = await escalate(
        beneficiary_id="B001",
        level=4,
        triggered_by="U001",
    )
    assert result["error"] == "invalid_level"


@pytest.mark.asyncio
async def test_escalate_unknown_beneficiary_returns_error():
    """Escalate should return an error for unknown beneficiary IDs."""
    from mcp_server.tools.escalate import escalate

    with patch(
        "mcp_server.tools.escalate.get_beneficiary_by_id",
        return_value=None,
    ):
        result = await escalate(
            beneficiary_id="BXXX",
            level=2,
            triggered_by="U001",
        )
    assert result["error"] == "beneficiary_not_found"


@pytest.mark.asyncio
async def test_escalate_level_labels():
    """The level labels should be human-readable French."""
    from mcp_server.tools.escalate import _LEVEL_LABELS

    assert "Weak signal" in _LEVEL_LABELS[1]
    assert "coordinator" in _LEVEL_LABELS[2].lower()
    assert "SAMU" in _LEVEL_LABELS[3]


@pytest.mark.asyncio
async def test_escalate_get_neighbor_referent_loads_from_volunteers():
    """_get_neighbor_referent should load from volunteers.json."""
    from mcp_server.tools.escalate import _get_neighbor_referent

    # B001 is in sector 1 (based on our generator: sector = ((i-1) % 12) + 1)
    referent = await _get_neighbor_referent({"sector": 1})
    assert referent is not None
    assert "name" in referent
    assert "phone" in referent


@pytest.mark.asyncio
async def test_escalate_get_neighbor_referent_no_sector_returns_none():
    """_get_neighbor_referent should return None if no sector."""
    from mcp_server.tools.escalate import _get_neighbor_referent

    referent = await _get_neighbor_referent({})
    assert referent is None


@pytest.mark.asyncio
async def test_escalate_generate_context_summary_includes_profile():
    """_generate_context_summary should include name, age, sector, conditions."""
    from mcp_server.tools.escalate import _generate_context_summary

    summary = await _generate_context_summary({
        "first_name": "Hélène",
        "last_initial": "M",
        "age": 82,
        "sector": 11,
        "medical_conditions": ["hypertension"],
        "medications": ["antihypertenseur"],
    })

    assert "Hélène" in summary
    assert "82" in summary
    assert "11" in summary
    assert "hypertension" in summary
    assert "antihypertenseur" in summary
