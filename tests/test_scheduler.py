"""Tests: Scheduler (with mocked orchestrator)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scheduler import (
    _job_daily_report,
    _job_refresh_canvas,
    _job_refresh_rts,
    get_scheduler,
    stop_scheduler,
)


@pytest.fixture
def mock_orchestrator():
    """A mock orchestrator for scheduler jobs."""
    orch = MagicMock()
    orch.state = MagicMock()
    orch.state.is_scenario_active = False
    orch.generate_daily_report = AsyncMock(return_value={"status": "ok"})
    orch._update_cellule_crise_canvas = AsyncMock()
    orch.rts = MagicMock()
    orch.rts.clear_cache = MagicMock()
    orch.rts.get_health_directives = AsyncMock(return_value=[])
    return orch


@pytest.mark.asyncio
async def test_daily_report_skips_when_no_scenario(mock_orchestrator):
    """_job_daily_report should skip when no scenario is active."""
    mock_orchestrator.state.is_scenario_active = False

    await _job_daily_report(mock_orchestrator)

    mock_orchestrator.generate_daily_report.assert_not_called()


@pytest.mark.asyncio
async def test_daily_report_fires_when_scenario_active(mock_orchestrator):
    """_job_daily_report should call generate_daily_report when scenario is active."""
    mock_orchestrator.state.is_scenario_active = True

    await _job_daily_report(mock_orchestrator)

    mock_orchestrator.generate_daily_report.assert_called_once()


@pytest.mark.asyncio
async def test_daily_report_handles_exception(mock_orchestrator):
    """_job_daily_report should not raise if generate_daily_report fails."""
    mock_orchestrator.state.is_scenario_active = True
    mock_orchestrator.generate_daily_report = AsyncMock(side_effect=RuntimeError("AI down"))

    # Should not raise
    await _job_daily_report(mock_orchestrator)


@pytest.mark.asyncio
async def test_refresh_canvas_skips_when_no_scenario(mock_orchestrator):
    """_job_refresh_canvas should skip when no scenario is active."""
    mock_orchestrator.state.is_scenario_active = False

    await _job_refresh_canvas(mock_orchestrator)

    mock_orchestrator._update_cellule_crise_canvas.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_canvas_fires_when_scenario_active(mock_orchestrator):
    """_job_refresh_canvas should call _update_cellule_crise_canvas when active."""
    mock_orchestrator.state.is_scenario_active = True

    await _job_refresh_canvas(mock_orchestrator)

    mock_orchestrator._update_cellule_crise_canvas.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_canvas_handles_exception(mock_orchestrator):
    """_job_refresh_canvas should not raise if canvas update fails."""
    mock_orchestrator.state.is_scenario_active = True
    mock_orchestrator._update_cellule_crise_canvas = AsyncMock(
        side_effect=RuntimeError("Slack API down")
    )

    await _job_refresh_canvas(mock_orchestrator)  # should not raise


@pytest.mark.asyncio
async def test_refresh_rts_clears_cache_and_fetches(mock_orchestrator):
    """_job_refresh_rts should clear the cache then fetch fresh directives."""
    await _job_refresh_rts(mock_orchestrator)

    mock_orchestrator.rts.clear_cache.assert_called_once()
    mock_orchestrator.rts.get_health_directives.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_rts_handles_exception(mock_orchestrator):
    """_job_refresh_rts should not raise if the RTS service fails."""
    mock_orchestrator.rts.get_health_directives = AsyncMock(
        side_effect=RuntimeError("RSS feeds all down")
    )

    await _job_refresh_rts(mock_orchestrator)  # should not raise


def test_get_scheduler_returns_singleton():
    """get_scheduler should return the same instance on repeated calls."""
    s1 = get_scheduler()
    s2 = get_scheduler()
    assert s1 is s2


def test_stop_scheduler_clears_singleton():
    """stop_scheduler should clear the singleton so the next call creates a new one."""
    s1 = get_scheduler()
    stop_scheduler()
    s2 = get_scheduler()
    assert s1 is not s2
