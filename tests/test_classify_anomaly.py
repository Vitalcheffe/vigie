"""
Test: record_checkin anomaly classification.

Validates the 4-level anomaly classification:
  0 = OK
  1 = Weak signal
  2 = Coordinator escalation
  3 = Critical (SAMU)
"""

from __future__ import annotations

import pytest

from mcp_server.tools.record_checkin import _classify_anomaly


@pytest.mark.asyncio
async def test_classification_level_0_ok():
    """A normal check-in should classify as level 0 (OK)."""
    beneficiary = {"id": "B001", "first_name": "Hélène", "last_initial": "M"}
    level, signals, recommended = await _classify_anomaly(
        transcript="Mme Dupont va bien, Conversation normale, tout est OK.",
        pre_detected=None,
        beneficiary=beneficiary,
    )
    assert level == 0
    assert signals == []
    assert recommended == "ok"


@pytest.mark.asyncio
async def test_classification_level_1_weak_signal_medication():
    """A medication request should classify as level 1 with pharmacy recommendation."""
    beneficiary = {"id": "B002"}
    level, signals, recommended = await _classify_anomaly(
        transcript="Mme Martin fatiguée, demande renouvellement ordonnance antihypertenseur.",
        pre_detected=None,
        beneficiary=beneficiary,
    )
    assert level == 1
    assert "medication_request" in signals
    assert recommended == "pharmacy"


@pytest.mark.asyncio
async def test_classification_level_2_unreachable():
    """An unreachable beneficiary should classify as level 2."""
    beneficiary = {"id": "B003"}
    level, signals, recommended = await _classify_anomaly(
        transcript="No answer after 3 calls.",
        pre_detected=None,
        beneficiary=beneficiary,
    )
    assert level == 2
    assert "unreachable" in signals
    assert recommended == "escalate_coord"


@pytest.mark.asyncio
async def test_classification_level_3_critical():
    """A critical situation should classify as level 3 (SAMU)."""
    beneficiary = {"id": "B004"}
    level, signals, recommended = await _classify_anomaly(
        transcript="M. Bernard est au sol, inconscient, ne respire pas.",
        pre_detected=None,
        beneficiary=beneficiary,
    )
    assert level == 3
    assert "critical_keyword" in signals
    assert recommended == "escalate_samu"


@pytest.mark.asyncio
async def test_classification_level_2_cognitive_distress():
    """Cognitive distress (confusion, disorientation) should escalate to level 2."""
    beneficiary = {"id": "B005"}
    level, signals, recommended = await _classify_anomaly(
        transcript="Mrs Durand seems confused and disoriented, ne sait plus quel jour on est.",
        pre_detected=None,
        beneficiary=beneficiary,
    )
    assert level == 2
    assert "cognitive_distress" in signals
