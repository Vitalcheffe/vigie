"""Tests: Modal view builders."""

from __future__ import annotations

from app.blocks.modals import (
    build_anomaly_modal,
    build_checkin_modal,
    build_escalate_modal,
    build_reassign_modal,
)


def test_checkin_modal_has_required_fields():
    modal = build_checkin_modal(
        beneficiary_id="B023",
        beneficiary_name="Hélène M.",
        sector=11,
    )
    assert modal["callback_id"] == "vigie_modal_checkin"
    assert modal["private_metadata"] == "checkin:B023"
    block_ids = [b["block_id"] for b in modal["blocks"] if "block_id" in b]
    assert "state_block" in block_ids
    assert "notes_block" in block_ids
    assert "action_block" in block_ids


def test_checkin_modal_state_options_match_5_levels():
    modal = build_checkin_modal(beneficiary_id="B001", beneficiary_name="X")
    state_block = next(b for b in modal["blocks"] if b.get("block_id") == "state_block")
    options = state_block["element"]["options"]
    assert len(options) == 5
    values = [o["value"] for o in options]
    assert "ok" in values
    assert "critical" in values


def test_anomaly_modal_metadata_carries_trigger():
    modal = build_anomaly_modal(trigger_message_ts="1234567890.123456", trigger_channel="C123")
    assert modal["callback_id"] == "vigie_modal_anomaly"
    assert modal["private_metadata"] == "anomaly:C123:1234567890.123456"


def test_reassign_modal_metadata_carries_beneficiary():
    modal = build_reassign_modal(beneficiary_id="B042")
    assert modal["callback_id"] == "vigie_modal_reassign"
    assert modal["private_metadata"] == "reassign:B042"


def test_escalate_modal_has_3_levels():
    modal = build_escalate_modal(beneficiary_id="B003")
    assert modal["callback_id"] == "vigie_modal_escalate"
    level_block = next(b for b in modal["blocks"] if b.get("block_id") == "level_block")
    options = level_block["element"]["options"]
    assert len(options) == 3
    values = [o["value"] for o in options]
    assert "1" in values
    assert "2" in values
    assert "3" in values


def test_all_modals_have_submit_and_close():
    for builder in [
        lambda: build_checkin_modal("B001", "X"),
        lambda: build_anomaly_modal("ts", "C1"),
        lambda: build_reassign_modal("B001"),
        lambda: build_escalate_modal("B001"),
    ]:
        modal = builder()
        assert "submit" in modal
        assert "close" in modal
        assert modal["submit"]["text"]  # plain_text text is a string
        assert modal["close"]["text"]
