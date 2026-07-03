"""
Vigie — Z-AI powered Slack AI service.

Uses the z-ai-web-dev-sdk (via subprocess) as the AI backend for:
  - Daily report narrative generation
  - Anomaly classification from volunteer notes
  - Structured JSON extraction

This replaces the OpenAI fallback with a free, always-available AI
backend that doesn't require an API key.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.services.zai")


async def zai_chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
    """Call the z-ai CLI to generate a chat completion.

    Runs the z-ai CLI as a subprocess and returns the response text.
    Falls back to empty string on error.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "z-ai", "chat",
            "--prompt", prompt,
            "--system", system,
            "-o", "/tmp/zai_output.json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

        if proc.returncode != 0:
            log.warning("zai.chat_failed", returncode=proc.returncode, stderr=stderr.decode()[:200])
            return ""

        # Read the output file
        try:
            with open("/tmp/zai_output.json", "r") as f:
                data = json.load(f)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            # Try parsing stdout directly
            try:
                data = json.loads(stdout.decode())
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception:
                return stdout.decode().strip()

    except asyncio.TimeoutError:
        log.warning("zai.chat_timeout")
        return ""
    except Exception as e:
        log.warning("zai.chat_error", error=str(e))
        return ""


async def generate_report_narrative(
    date: str,
    total: int,
    contacted: int,
    ok_count: int,
    weak_count: int,
    coord_count: int,
    samu_count: int,
    avg_escalade_latency: str,
    unreachable_72h: int,
    weak_signals_list: list[str],
) -> str:
    """Generate a human narrative for the daily report using Z-AI."""

    coverage_pct = int((contacted / total) * 100) if total > 0 else 0

    prompt = f"""Write a brief, warm, human daily report narrative for a heatwave elder watch network.

Date: {date}
Coverage: {coverage_pct}% ({contacted}/{total} elders contacted)
Check-in OK: {ok_count}
Weak signals: {weak_count}
Coordinator escalations: {coord_count}
SAMU escalations: {samu_count}
Avg escalation latency: {avg_escalade_latency}
Not contacted > 72h: {unreachable_72h}
Weak signals to watch: {', '.join(weak_signals_list[:3]) if weak_signals_list else 'none'}

Write 3 short paragraphs:
1. Summary of the day (2 sentences)
2. Points of attention (bullet points)
3. Recommendations for tomorrow (bullet points)

Tone: warm, caring, professional. Like a nurse handing over to the next shift.
Do NOT use markdown headers. Just plain text with bullet points using •."""

    result = await zai_chat(prompt, system="You are a caring healthcare coordinator writing a daily handover report.")
    
    if not result:
        # Fallback narrative
        result = (
            f"Today, {contacted} out of {total} isolated elders were contacted. "
            f"Coverage reached {coverage_pct}%.\n\n"
            f"• {ok_count} check-ins were OK\n"
            f"• {weak_count} weak signals were detected early\n"
            f"• {coord_count} coordinator interventions\n"
            f"• {samu_count} critical SAMU escalations\n\n"
            f"Tomorrow, prioritize the {unreachable_72h} elders not yet contacted. "
            f"Continue monitoring the weak signals."
        )

    return result


async def classify_anomaly_zai(transcript: str) -> tuple[int, list[str], str]:
    """Classify a volunteer check-in note using Z-AI.

    Returns (level, signals, recommended_action).
    """
    prompt = f"""Classify the severity of this volunteer check-in note for an isolated elderly person during a heatwave.

Note: "{transcript}"

Respond with ONLY a JSON object:
{{"level": 0|1|2|3, "signals": ["keyword1", ...], "recommended": "ok"|"pharmacy"|"escalate_coord"|"escalate_samu"}}

Levels:
0 = OK (everything fine)
1 = Weak signal (tired, medication request, mild concern)
2 = Needs coordinator (no answer, confused, fall risk)
3 = Critical SAMU (unconscious, on the ground, not breathing)"""

    result = await zai_chat(prompt, system="You are a medical triage AI. Respond only with JSON.")

    if not result:
        # Fallback to keyword classification
        return await _keyword_classify(transcript)

    try:
        # Clean up the response
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        parsed = json.loads(result)
        level = max(0, min(3, int(parsed.get("level", 0))))
        signals = parsed.get("signals", []) or []
        recommended = parsed.get("recommended", "ok")

        valid = {"ok", "pharmacy", "escalate_coord", "escalate_samu"}
        if recommended not in valid:
            recommended = "ok" if level == 0 else "escalate_coord" if level == 2 else "escalate_samu"

        return level, signals, recommended
    except Exception:
        return await _keyword_classify(transcript)


async def _keyword_classify(transcript: str) -> tuple[int, list[str], str]:
    """Fallback keyword-based classification."""
    text = transcript.lower()

    critical = ["on the ground", "unconscious", "not breathing", "samu", "15", "112", "emergency", "au sol", "inconscient"]
    if any(k in text for k in critical):
        return 3, ["critical_keyword"], "escalate_samu"

    coord = ["no answer", "unreachable", "confused", "disoriented", "fall", "pas de réponse", "injoignable"]
    if any(k in text for k in coord):
        return 2, ["unreachable"], "escalate_coord"

    weak = ["tired", "medication", "fatigue", "requests", "alone", "afraid", "fatiguée", "médicament"]
    if any(k in text for k in weak):
        if any(k in text for k in ["medication", "médicament"]):
            return 1, ["medication_request"], "pharmacy"
        return 1, ["weak_signal"], "ok"

    return 0, [], "ok"
