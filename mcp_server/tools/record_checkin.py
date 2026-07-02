"""
Vigie MCP tool — record_checkin.

Records a volunteer's check-in return for a beneficiary.
The return can be:
  - text (typed note from volunteer)
  - voice (transcribed by Slack AI beforehand)
  - structured (button click: OK / unreachable / weak signal)

The tool:
  1. Stores the check-in record
  2. Updates beneficiary status
  3. Triggers Slack AI analysis (anomaly classification)
  4. Optionally triggers community_pois lookup (pharmacy, neighbor)
  5. Returns a structured message ready to post in the sector channel
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.utils.logging import get_logger
from mcp_server.resources.beneficiary_registry import (
    get_beneficiary_by_id,
    update_beneficiary_status,
)

log = get_logger("vigie.mcp.tools.record_checkin")


async def record_checkin(
    beneficiary_id: str,
    volunteer_id: str,
    transcript: str,
    channel_type: str = "voice",  # voice | text | button
    detected_signals: list[str] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Record a check-in for a beneficiary.

    Args:
        beneficiary_id: e.g., "B001"
        volunteer_id: Slack user ID of the volunteer
        transcript: The volunteer's note (text or transcribed voice)
        channel_type: How the check-in was captured (voice/text/button)
        detected_signals: Pre-detected signals from Slack AI (optional)
        timestamp: ISO timestamp. Defaults to now.

    Returns:
        {
            "beneficiary": {...},
            "checkin_id": "...",
            "anomaly_level": 0-3,
            "detected_signals": [...],
            "recommended_action": "ok" | "pharmacy" | "escalate_coord" | "escalate_samu",
            "suggested_pois": [...],
            "sector_message": "Message ready to post in #secteur-N",
            "timestamp": "..."
        }
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    log.info(
        "vigie.mcp.tool.record_checkin",
        beneficiary=beneficiary_id,
        volunteer=volunteer_id,
        channel=channel_type,
    )

    beneficiary = get_beneficiary_by_id(beneficiary_id)
    if not beneficiary:
        return {
            "error": "beneficiary_not_found",
            "beneficiary_id": beneficiary_id,
        }

    # 1. Classify the anomaly (stub: Slack AI)
    anomaly_level, signals, recommended = await _classify_anomaly(
        transcript, detected_signals, beneficiary
    )

    # 2. Update beneficiary status based on anomaly level
    status_map = {
        0: "ok",
        1: "ok",  # weak signal, but not urgent
        2: "escalated",
        3: "critical",
    }
    new_status = status_map.get(anomaly_level, "ok")
    update_beneficiary_status(
        beneficiary_id,
        status=new_status,
        notes=transcript[:500],  # truncate for storage
        last_checkin_at=timestamp,
    )

    # 3. Fetch suggested POIs if needed (pharmacy for medication request, etc.)
    suggested_pois = []
    if recommended == "pharmacy":
        suggested_pois = await _suggest_pois(beneficiary, "pharmacy")
    elif recommended in ("escalate_coord", "escalate_samu"):
        suggested_pois = await _suggest_pois(beneficiary, "hospital")

    # 4. Build the sector channel message
    sector_message = _build_sector_message(
        beneficiary=beneficiary,
        volunteer_id=volunteer_id,
        transcript=transcript,
        anomaly_level=anomaly_level,
        signals=signals,
        recommended=recommended,
        suggested_pois=suggested_pois,
    )

    checkin_id = f"C-{beneficiary_id}-{int(datetime.now(timezone.utc).timestamp())}"

    result = {
        "checkin_id": checkin_id,
        "beneficiary": {
            "id": beneficiary["id"],
            "name": f"{beneficiary['first_name']} {beneficiary['last_initial']}.",
            "sector": beneficiary.get("sector"),
            "age": beneficiary.get("age"),
        },
        "anomaly_level": anomaly_level,
        "anomaly_label": _ANOMALY_LABELS[anomaly_level],
        "detected_signals": signals,
        "recommended_action": recommended,
        "suggested_pois": suggested_pois,
        "sector_message": sector_message,
        "timestamp": timestamp,
    }

    log.info(
        "vigie.mcp.tool.record_checkin.done",
        beneficiary=beneficiary_id,
        anomaly=anomaly_level,
        recommended=recommended,
    )
    return result


# ============================================================
# Slack AI integration (stub — full implementation)
# ============================================================

_ANOMALY_LABELS = {
    0: "OK",
    1: "Signal faible",
    2: "Escalade coordinateur",
    3: "Escalade critique (SAMU)",
}


async def _classify_anomaly(
    transcript: str,
    pre_detected: list[str] | None,
    beneficiary: dict,
) -> tuple[int, list[str], str]:
    """
    Classify the anomaly level from the transcript.

    Levels:
      0 = OK, no signal
      1 = Weak signal (fatigue, mild confusion, request for help)
      2 = Coordinator escalation (unreachable, persistent confusion, fall risk)
      3 = Critical (SAMU — unconscious, severe distress, fall)

    TODO: replace stub with Slack AI call (Slack AI classification
    or OpenAI fallback) with structured prompt for 4-level classification.
    """
    # TODO: keyword-based classification
    text = transcript.lower()

    # Critical signals
    critical_keywords = ["au sol", "inconscient", "ne respire pas", "samu", "15", "112", "urgence vitale"]
    if any(k in text for k in critical_keywords):
        return 3, ["critical_keyword"], "escalate_samu"

    # Coordinator escalation
    coord_keywords = ["pas de réponse", "pas répondu", "injoignable", "confuse", "désorientée", "chute"]
    if any(k in text for k in coord_keywords):
        signals = ["unreachable"] if "pas de réponse" in text or "pas répondu" in text else ["cognitive_distress"]
        return 2, signals, "escalate_coord"

    # Weak signals
    weak_keywords = ["fatiguée", "fatigue", "médicament", "ordonnance", "difficile", "seule", "peur"]
    weak_hits = [k for k in weak_keywords if k in text]
    if weak_hits:
        if any(k in weak_hits for k in ["médicament", "ordonnance"]):
            return 1, ["medication_request"], "pharmacy"
        return 1, ["weak_signal"], "ok"

    # Default OK
    return 0, [], "ok"


async def _suggest_pois(beneficiary: dict, poi_type: str) -> list[dict[str, Any]]:
    """Suggest POIs near the beneficiary's address."""
    from mcp_server.resources.community_pois import fetch_pois_around

    address = beneficiary.get("address", {})
    lat = address.get("lat")
    lon = address.get("lon")
    if lat is None or lon is None:
        return []

    pois = await fetch_pois_around(lat, lon, 1500)
    return [p for p in pois if p.get("type") == poi_type][:3]


def _build_sector_message(
    beneficiary: dict,
    volunteer_id: str,
    transcript: str,
    anomaly_level: int,
    signals: list[str],
    recommended: str,
    suggested_pois: list[dict],
) -> str:
    """
    Build a Slack-ready message for the sector channel.

    Format: structured text with the beneficiary's name, age, sector,
    the volunteer's note, the detected anomaly level, and recommended actions.
    """
    name = f"{beneficiary['first_name']} {beneficiary['last_initial']}."
    sector = beneficiary.get("sector", "?")
    age = beneficiary.get("age", "?")

    level_emoji = {0: ":large_green_circle:", 1: ":large_yellow_circle:", 2: ":large_orange_circle:", 3: ":red_circle:"}
    emoji = level_emoji.get(anomaly_level, ":white_circle:")

    msg_parts = [
        f"{emoji} *Check-in — {name}*, {age} ans, secteur {sector}",
        f"_Bénévole : <@{volunteer_id}>_",
        "",
        f"> {transcript}",
        "",
        f"*Niveau anomalie :* {_ANOMALY_LABELS.get(anomaly_level, '?')}",
    ]

    if signals:
        msg_parts.append(f"*Signaux détectés :* {', '.join(signals)}")

    if suggested_pois:
        msg_parts.append("")
        msg_parts.append("*POIs suggérés :*")
        for poi in suggested_pois:
            distance = poi.get("distance_m")
            distance_str = f" ({distance:.0f} m)" if distance else ""
            msg_parts.append(f"  • {poi.get('name', '?')} — {poi.get('type', '?')}{distance_str}")

    return "\n".join(msg_parts)


def register(mcp) -> None:
    """Register the record_checkin tool on the MCP server."""

    @mcp.tool()
    async def record_checkin_tool(
        beneficiary_id: str,
        volunteer_id: str,
        transcript: str,
        channel_type: str = "voice",
        detected_signals: list[str] | None = None,
    ) -> str:
        """
        Record a volunteer's check-in return for a beneficiary.

        Stores the record, runs anomaly classification, updates beneficiary
        status, and returns a structured message ready to post in the sector channel.

        Args:
            beneficiary_id: Beneficiary ID (e.g., "B001")
            volunteer_id: Slack user ID of the volunteer
            transcript: The volunteer's note (typed or transcribed voice)
            channel_type: "voice" | "text" | "button"
            detected_signals: Pre-detected signals from Slack AI (optional)

        Returns JSON with anomaly level, recommended action, suggested POIs,
        and the sector channel message.
        """
        result = await record_checkin(
            beneficiary_id=beneficiary_id,
            volunteer_id=volunteer_id,
            transcript=transcript,
            channel_type=channel_type,
            detected_signals=detected_signals,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    log.debug("vigie.mcp.tool.record_checkin.registered")
