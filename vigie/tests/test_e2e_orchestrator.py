"""Tests: End-to-end orchestrator flow with mocked Slack + MCP + AI.

These tests validate the complete Vigie workflow:
  1. start_heatwave → posts alert + DMs volunteers + publishes canvas
  2. process_volunteer_message → transcribes, classifies, posts in sector
  3. trigger_escalation → posts in cellule-crise with SAMU button
  4. generate_daily_report → aggregates metrics + AI narrative + RTS

All external calls (Slack Web API, MCP server, Slack AI, RTS) are mocked
so the tests run hermetically.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.state import get_state


@pytest.fixture
def mock_slack_client():
    """A mock AsyncWebClient that captures all Slack API calls."""
    client = AsyncMock()
    # conversations_list returns our sandbox channels
    client.conversations_list = AsyncMock(
        return_value={
            "channels": [
                {"id": "C001", "name": "cellule-crise"},
                {"id": "C002", "name": "secteur-1"},
                {"id": "C003", "name": "secteur-2"},
                {"id": "C004", "name": "secteur-3"},
                {"id": "C005", "name": "secteur-11"},
                {"id": "C006", "name": "voisins-1"},
                {"id": "C007", "name": "voisins-2"},
                {"id": "C008", "name": "voisins-3"},
            ]
        }
    )
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "1234567890.123456"})
    client.conversations_open = AsyncMock(return_value={"channel": {"id": "DM001"}})
    client.views_publish = AsyncMock(return_value={"ok": True})
    client.auth_test = AsyncMock(return_value={"user_id": "U_VIGIE"})
    client.users_info = AsyncMock(
        return_value={"user": {"profile": {"real_name": "Test Volunteer", "display_name": "Test"}}}
    )
    client.canvas_create = AsyncMock(return_value={"ok": True, "canvas_id": "V001"})
    return client


@pytest.fixture
def mock_mcp_client():
    """A mock MCPClient that returns controlled responses.

    Supports async context manager (async with mcp as client:) because
    the orchestrator uses that pattern.
    """
    mcp = AsyncMock()

    # Make it an async context manager that returns itself
    mcp.__aenter__ = AsyncMock(return_value=mcp)
    mcp.__aexit__ = AsyncMock(return_value=None)

    # list_weather_alerts returns a scenario alert
    mcp.list_weather_alerts = AsyncMock(
        return_value=[
            {
                "id": "test-alert",
                "level": "orange",
                "phenomenon": "canicule",
                "department": "75",
                "department_name": "Paris",
                "max_temperature": 38,
                "valid_to": "2026-07-18T22:00:00+02:00",
                "source": "Scenario (demo)",
            }
        ]
    )

    # assign_checkins returns 2 volunteers with 2 beneficiaries each
    mcp.assign_checkins = AsyncMock(
        return_value={
            "status": "ok",
            "date": "2026-07-15",
            "alert_level": "orange",
            "total_beneficiaries": 4,
            "total_volunteers": 2,
            "assignments": [
                {
                    "volunteer_id": "U001",
                    "volunteer_name": "Marie Dupont",
                    "sector": 11,
                    "beneficiaries": [
                        {"id": "B023", "first_name": "Hélène", "last_initial": "M", "age": 82, "sector": 11, "phone": "+33 6 12 34 56 78"},
                        {"id": "B024", "first_name": "Pierre", "last_initial": "L", "age": 79, "sector": 11, "phone": "+33 6 12 34 56 79"},
                    ],
                },
                {
                    "volunteer_id": "U002",
                    "volunteer_name": "Luc Martin",
                    "sector": 3,
                    "beneficiaries": [
                        {"id": "B003", "first_name": "Jeanne", "last_initial": "M", "age": 81, "sector": 3, "phone": "+33 6 12 34 56 80"},
                        {"id": "B004", "first_name": "Robert", "last_initial": "P", "age": 78, "sector": 3, "phone": "+33 6 12 34 56 81"},
                    ],
                },
            ],
        }
    )

    # record_checkin returns a structured result
    mcp.record_checkin = AsyncMock(
        return_value={
            "checkin_id": "C-B023-1234",
            "beneficiary": {"name": "Hélène M.", "age": 82, "sector": 11, "phone": "+33..."},
            "anomaly_level": 1,
            "anomaly_label": "Signal faible",
            "detected_signals": ["medication_request"],
            "recommended_action": "pharmacy",
            "suggested_pois": [
                {"id": "osm-1", "type": "pharmacy", "name": "Pharmacie des Lilas", "distance_m": 200}
            ],
            "sector_message": "structured message",
        }
    )

    # escalate returns a critical result
    mcp.escalate = AsyncMock(
        return_value={
            "escalation_id": "E-B003-L3-1234",
            "beneficiary": {"name": "Jeanne M.", "age": 81, "sector": 3, "phone": "+33..."},
            "level": 3,
            "context_summary": "Jeanne M., 81 ans, secteur 3. Vit seule. Canicule active.",
            "neighbor_referent_notified": True,
            "medical_coordinator_notified": True,
            "samu_triggered": True,
        }
    )

    return mcp


@pytest.fixture
def orchestrator(mock_slack_client, mock_mcp_client):
    """Build an orchestrator with all external deps mocked."""
    from app.orchestrator import VigieOrchestrator

    orch = VigieOrchestrator(slack_client=mock_slack_client, mcp_client=mock_mcp_client)

    # Mock Slack AI
    orch.slack_ai = AsyncMock()
    orch.slack_ai.classify_anomaly = AsyncMock(return_value=(1, ["medication_request"], "pharmacy"))
    orch.slack_ai.generate_daily_report = AsyncMock(return_value="Synthèse du jour: 4 check-in, 1 signal faible.")
    orch.slack_ai.transcribe_audio = AsyncMock(return_value="B023: Mme Dupont fatiguée, demande médicaments")

    # Mock RTS
    orch.rts = AsyncMock()
    orch.rts.get_health_directives = AsyncMock(
        return_value=[
            {"source": "ARS Île-de-France", "title": "Vigilance orange canicule", "url": "https://ars.iledefrance.fr", "summary": "...", "published_at": "2026-07-15"}
        ]
    )

    # Reset state
    get_state().reset()

    return orch


@pytest.mark.asyncio
async def test_e2e_start_heatwave_posts_alert_and_dms_volunteers(orchestrator, mock_slack_client, mock_mcp_client):
    """start_heatwave should:
    1. Post an alert banner in #cellule-crise
    2. DM each volunteer their assignment
    3. Mark scenario active in state
    """
    result = await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)

    assert result["status"] == "ok"
    assert result["total_beneficiaries"] == 4
    assert result["volunteers_notified"] == 2

    # Verify alert was posted in cellule-crise
    cellule_posts = [
        call for call in mock_slack_client.chat_postMessage.call_args_list
        if call.kwargs.get("channel") == "C001"
    ]
    assert len(cellule_posts) >= 1
    alert_text = cellule_posts[0].kwargs.get("text", "")
    assert "canicule" in alert_text.lower() or "vigilance" in alert_text.lower()

    # Verify DMs were sent to both volunteers
    # conversations_open was called for each volunteer
    assert mock_slack_client.conversations_open.call_count >= 2

    # Verify state is now active
    state = get_state()
    assert state.is_scenario_active
    assert state.get_metrics()["total_assigned"] == 4


@pytest.mark.asyncio
async def test_e2e_process_volunteer_message_posts_in_sector(orchestrator, mock_slack_client, mock_mcp_client):
    """process_volunteer_message should:
    1. Extract beneficiary ID from text
    2. Call MCP record_checkin
    3. Post structured message in the sector channel
    4. Record in state store
    """
    # Start scenario first
    await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)
    mock_slack_client.chat_postMessage.reset_mock()

    result = await orchestrator.process_volunteer_message(
        volunteer_id="U001",
        text="B023: Mme Dupont fatiguée, demande médicaments",
    )

    assert result["status"] == "ok"
    assert result["beneficiary_id"] == "B023"
    assert result["anomaly_level"] == 1

    # Verify MCP record_checkin was called
    mock_mcp_client.record_checkin.assert_called_once()
    call_kwargs = mock_mcp_client.record_checkin.call_args.kwargs
    assert call_kwargs["beneficiary_id"] == "B023"
    assert call_kwargs["volunteer_id"] == "U001"

    # Verify a message was posted (either sector channel or DM ack)
    assert mock_slack_client.chat_postMessage.call_count >= 1

    # Verify state recorded the check-in
    state = get_state()
    metrics = state.get_metrics()
    assert metrics["contacted"] == 1


@pytest.mark.asyncio
async def test_e2e_trigger_escalation_posts_in_cellule_crise(orchestrator, mock_slack_client, mock_mcp_client):
    """trigger_escalation should:
    1. Call MCP escalate
    2. Post the escalation message in #cellule-crise
    3. Record in state store with detected_at
    """
    await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)
    mock_slack_client.chat_postMessage.reset_mock()

    result = await orchestrator.trigger_escalation(
        beneficiary_id="B003",
        level=3,
        triggered_by="U001",
        reason="Au sol, inconsciente",
    )

    assert result["status"] == "ok"
    assert result["level"] == 3

    # Verify MCP escalate was called
    mock_mcp_client.escalate.assert_called_once()

    # Verify a message was posted in cellule-crise
    assert mock_slack_client.chat_postMessage.call_count >= 1

    # Verify state recorded the escalation
    state = get_state()
    metrics = state.get_metrics()
    assert metrics["samu_escalations"] == 1


@pytest.mark.asyncio
async def test_e2e_generate_daily_report_requires_active_scenario(orchestrator):
    """generate_daily_report should refuse if no scenario is active."""
    result = await orchestrator.generate_daily_report()
    assert result["status"] == "no_scenario"


@pytest.mark.asyncio
async def test_e2e_generate_daily_report_aggregates_metrics(orchestrator, mock_slack_client):
    """generate_daily_report should:
    1. Pull metrics from state
    2. Call Slack AI for the narrative
    3. Call RTS for directives
    4. Post the report in #cellule-crise
    """
    # Start scenario + do a check-in + trigger escalation
    await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)
    await orchestrator.process_volunteer_message(
        volunteer_id="U001",
        text="B023: Mme Dupont fatiguée",
    )
    await orchestrator.trigger_escalation(
        beneficiary_id="B003",
        level=3,
        triggered_by="U001",
    )
    mock_slack_client.chat_postMessage.reset_mock()

    result = await orchestrator.generate_daily_report()

    assert result["status"] == "ok"
    assert result["posted"] is True

    # Verify Slack AI was called for the narrative
    orchestrator.slack_ai.generate_daily_report.assert_called_once()

    # Verify RTS was called for directives
    orchestrator.rts.get_health_directives.assert_called()

    # Verify the report was posted in cellule-crise
    assert mock_slack_client.chat_postMessage.call_count >= 1


@pytest.mark.asyncio
async def test_e2e_reset_scenario_clears_state(orchestrator, mock_slack_client):
    """reset_scenario should wipe the state store and update the canvas."""
    await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)
    await orchestrator.process_volunteer_message(
        volunteer_id="U001",
        text="B023: OK",
    )

    state = get_state()
    assert state.is_scenario_active

    result = await orchestrator.reset_scenario(triggered_by="U_ADMIN")

    assert result["status"] == "ok"
    assert result["reset"] is True
    assert not state.is_scenario_active
    assert state.get_metrics()["contacted"] == 0


@pytest.mark.asyncio
async def test_e2e_no_beneficiary_id_in_message_returns_error(orchestrator, mock_slack_client):
    """A DM without a beneficiary ID should prompt the volunteer."""
    await orchestrator.start_heatwave(triggered_by="U_ADMIN", force_alert=True)
    mock_slack_client.chat_postMessage.reset_mock()

    result = await orchestrator.process_volunteer_message(
        volunteer_id="U001",
        text="Bonjour Vigie, comment ça va ?",
    )

    assert result["status"] == "no_beneficiary_id"
    # A DM should have been sent to the volunteer explaining the format
    assert mock_slack_client.chat_postMessage.call_count >= 1
