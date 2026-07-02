"""Tests: Block Kit builders."""

from __future__ import annotations

import json

from app.blocks.canvas import build_cellule_crise_canvas
from app.blocks.checkin import build_checkin_message, build_volunteer_dm
from app.blocks.dashboard import build_app_home
from app.blocks.escalation import build_escalation_message, build_escalation_thread_reply
from app.blocks.reports import build_daily_report

_BENEFICIARY = {
    "id": "B023",
    "first_name": "Hélène",
    "last_initial": "M",
    "age": 82,
    "sector": 11,
    "phone": "+33 6 12 34 56 78",
    "address": {"street": "12 Rue des Lilas", "postal_code": "75011", "city": "Paris"},
    "medical_conditions": ["hypertension"],
    "medications": ["antihypertenseur"],
}


def test_checkin_message_has_header_with_anomaly_emoji():
    msg = build_checkin_message(
        beneficiary=_BENEFICIARY,
        volunteer_id="U123",
        transcript="Mme Dupont fatiguée",
        anomaly_level=1,
        signals=["medication_request"],
        recommended_action="pharmacy",
        suggested_pois=[{"id": "p1", "name": "Pharmacie", "type": "pharmacy", "distance_m": 200}],
        checkin_id="C-B023-1234",
    )
    header = msg["blocks"][0]
    assert header["type"] == "header"
    assert "Check-in" in header["text"]["text"]
    assert "Hélène" in header["text"]["text"]


def test_checkin_message_level_3_has_samu_button():
    msg = build_checkin_message(
        beneficiary=_BENEFICIARY,
        volunteer_id="U123",
        transcript="Au sol, inconscient",
        anomaly_level=3,
        signals=["critical_keyword"],
        recommended_action="escalade_samu",
    )
    actions = [b for b in msg["blocks"] if b["type"] == "actions"][0]
    button_texts = [el["text"]["text"] for el in actions["elements"]]
    assert any("SAMU" in t for t in button_texts)


def test_checkin_message_button_values_are_json():
    msg = build_checkin_message(
        beneficiary=_BENEFICIARY,
        volunteer_id="U123",
        transcript="OK",
        anomaly_level=0,
        signals=[],
        recommended_action="ok",
    )
    actions = [b for b in msg["blocks"] if b["type"] == "actions"][0]
    for el in actions["elements"]:
        if "value" in el:
            parsed = json.loads(el["value"])
            assert "beneficiary_id" in parsed


def test_volunteer_dm_lists_all_assignments():
    assignments = [
        {**_BENEFICIARY, "id": "B001", "first_name": "Marie", "last_initial": "D"},
        {**_BENEFICIARY, "id": "B002", "first_name": "Pierre", "last_initial": "L"},
    ]
    msg = build_volunteer_dm(
        volunteer_id="U123",
        volunteer_name="Marie Dupont",
        assignments=assignments,
        alert_level="orange",
        date="2026-07-15",
    )
    text_blocks = [b for b in msg["blocks"] if b["type"] == "section"]
    # Header + intro + 2 beneficiaries + (action button is in actions block)
    assert len(text_blocks) >= 3


def test_escalation_message_includes_samu_call_button_for_level_3():
    msg = build_escalation_message(
        beneficiary=_BENEFICIARY,
        level=3,
        triggered_by="U123",
        reason="Au sol, consciente",
        context_summary="Mme Martin, 81 ans, secteur 3. Dernier check-in il y a 2h.",
        neighbor_notified=True,
        coordinator_notified=True,
        samu_triggered=True,
        escalation_id="E-B003-L3-1234",
    )
    actions = [b for b in msg["blocks"] if b["type"] == "actions"][0]
    samu_buttons = [el for el in actions["elements"] if "url" in el and el.get("url") == "tel:15"]
    assert len(samu_buttons) == 1


def test_escalation_thread_reply_has_metadata():
    reply = build_escalation_thread_reply(
        escalation_id="E-123",
        update_type="samu_arrived",
        author="U456",
        message="SAMU arrivé sur site à 14h02",
    )
    assert reply["metadata"]["event_type"] == "vigie_escalation_update"
    assert reply["metadata"]["event_payload"]["escalation_id"] == "E-123"


def test_daily_report_has_kpi_grid():
    msg = build_daily_report(
        date="2026-07-15",
        total=50,
        contacted=47,
        ok_count=40,
        weak_count=5,
        coord_count=1,
        samu_count=1,
        avg_checkin_time="2 min 10 s",
        avg_escalade_latency="4 min 30 s",
        unreachable_72h=0,
        weak_signals_list=["fatigue B023", "confusion B014"],
        rts_directives=[{"source": "ARS", "title": "Canicule niveau 3", "url": "https://example.org", "summary": "Recommandations", "published_at": "2026-07-15"}],
        ai_report_text="Synthèse du jour.",
    )
    fields_blocks = [b for b in msg["blocks"] if b.get("type") == "section" and "fields" in b]
    assert len(fields_blocks) >= 2  # KPI grid + counts


def test_canvas_has_alert_banner():
    blocks = build_cellule_crise_canvas(
        date="2026-07-15",
        alert_level="orange",
        alert_phenomenon="heatwave",
        alert_departments=["75", "93"],
        total_beneficiaries=50,
        contacted=47,
        ok_count=40,
        weak_count=5,
        coord_count=1,
        samu_count=1,
        avg_checkin_time="2 min 10 s",
        avg_escalade_latency="4 min 30 s",
        unreachable_72h=0,
    )
    callout = [b for b in blocks if b.get("type") == "callout"][0]
    assert "orange" in callout["text"]
    assert "75" in callout["text"]


def test_app_home_has_greeting_and_actions():
    view = build_app_home(
        user_id="U123",
        user_name="Marie Dupont",
        assignments=[_BENEFICIARY],
        alert={"level": "orange", "phenomenon": "heatwave", "department_name": "Paris", "max_temperature": 38, "valid_to": "2026-07-18"},
        kpis={"coverage_pct": 95, "avg_checkin_time": "2 min 10 s", "avg_escalade_latency": "4 min 30 s", "unreachable_72h": 0, "coord_count": 1, "samu_count": 1},
    )
    assert view["type"] == "home"
    actions = [b for b in view["blocks"] if b["type"] == "actions"]
    assert len(actions) >= 1
