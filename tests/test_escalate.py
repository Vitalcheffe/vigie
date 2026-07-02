"""
Test: escalate tool.

Validates the escalation logic:
  - Level 1 updates status to "ok" (monitored)
  - Level 2 notifies medical coordinator and neighbor referent
  - Level 3 triggers SAMU protocol
  - Invalid level returns an error
"""

from __future__ import annotations

import pytest

from mcp_server.tools.escalate import escalate


@pytest.mark.asyncio
async def test_escalate_invalid_level_returns_error():
    """Level 0 or 4 should return an error."""
    result = await escalate(
        beneficiary_id="B001",
        level=4,
        triggered_by="U123",
    )
    assert result["error"] == "invalid_level"


@pytest.mark.asyncio
async def test_escalate_unknown_beneficiary_returns_error():
    """Unknown beneficiary ID should return an error."""
    result = await escalate(
        beneficiary_id="BXXX",
        level=2,
        triggered_by="U123",
    )
    assert result["error"] == "beneficiary_not_found"


@pytest.mark.asyncio
async def test_escalate_level_3_triggers_samu():
    """Level 3 escalation should trigger SAMU protocol."""
    # This test requires a beneficiary to exist in the registry
    # TODO: full test with mock registry
    pass
