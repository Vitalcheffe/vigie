"""Tests: Orchestrator helpers (beneficiary ID extraction)."""

from __future__ import annotations

import pytest

from app.orchestrator import _extract_beneficiary_id


@pytest.mark.parametrize(
    "text, expected",
    [
        ("B023: Mme Dupont fatiguée", "B023"),
        ("B023 Mme Dupont fatiguée", "B023"),
        ("Check B7 OK", "B007"),
        ("B9999999999", None),  # too long to be a valid beneficiary id
        ("Pas d'ID dans ce message", None),
        ("b023 (minuscule)", "B023"),
        ("Beneficiary B42 needs help", "B042"),
        ("", None),
    ],
)
def test_extract_beneficiary_id(text, expected):
    assert _extract_beneficiary_id(text) == expected
