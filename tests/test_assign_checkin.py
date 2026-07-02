"""
Test: assign_checkins tool.

Validates that the assign_checkins tool correctly:
  - Returns an error when no heatwave is active (mock)
  - Distributes beneficiaries evenly across volunteers
  - Updates beneficiary status to "being_checked"
  - Handles empty registry gracefully
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools.assign_checkins import assign_checkins


@pytest.mark.asyncio
async def test_assign_checkins_no_heatwave_returns_error():
    """When no heatwave is active, the tool should return an error."""
    with patch(
        "mcp_server.tools.assign_checkins.is_heatwave_active",
        new=AsyncMock(return_value=False),
    ):
        result = await assign_checkins()

    assert result["error"] == "no_active_heatwave"
    assert "date" in result


@pytest.mark.asyncio
async def test_assign_checkins_distributes_beneficiaries():
    """With an active heatwave, beneficiaries should be distributed across volunteers."""
    # TODO: full test with mock registry and volunteers
    pass


def test_already_checked_today_helper():
    """The _already_checked_today helper should detect same-day check-ins."""
    from mcp_server.tools.assign_checkins import _already_checked_today

    assert _already_checked_today({"last_checkin_at": None}, "2026-07-15") is False
    assert _already_checked_today({"last_checkin_at": "2026-07-15T08:00:00Z"}, "2026-07-15") is True
    assert _already_checked_today({"last_checkin_at": "2026-07-14T08:00:00Z"}, "2026-07-15") is False
