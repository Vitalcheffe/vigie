"""
Vigie — Slack AI service.

Wraps Slack AI capabilities (when available in the workspace) with an
OpenAI fallback for development sandboxes where Slack AI may not be
enabled. Four tasks are exposed:

  - transcribe_audio(file_id)  -> str
  - extract_structured(text)   -> dict (state, signals, action)
  - classify_anomaly(text)     -> tuple[int, list[str], str]
  - generate_daily_report(...) -> str

The fallback is transparent to callers — they always get the same shape
of return value regardless of which backend ran.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.services.slack_ai")


# Prompts are kept short and deterministic. We want JSON out, not prose.
_TRANSCRIBE_HINT = "Transcription in English, without added punctuation, faithful to the original text."

_EXTRACT_PROMPT = """You are an assistant that structures volunteer phone check-in notes.
From the following text, produce a strict JSON with these fields:
  - state: "ok" | "weak_signal" | "needs_escalation" | "critical"
  - signals: list of keywords from [medication_request, fatigue, confusion, unreachable, fall, breathing_issue, distress, isolated, other]
  - action_required: "none" | "pharmacy_lookup" | "neighbor_referent" | "medical_coordinator" | "samu"
  - confidence: float between 0 and 1

Text:
\"\"\"{text}\"\"\"

Respond ONLY with the JSON, no surrounding text."""

_CLASSIFY_PROMPT = """Classify the severity of a volunteer check-in note into 4 levels:
  0 = OK (nothing to report)
  1 = Weak signal (fatigue, medication request, perceived isolation)
  2 = Coordinator escalation (unreachable, confusion, suspected fall)
  3 = Critical SAMU (unconscious, respiratory distress, on the ground, life-threatening emergency)

Note:
\"\"\"{text}\"\"\"

Respond with JSON: {{"level": 0|1|2|3, "signals": ["..."], "recommended": "ok"|"pharmacy"|"escalade_coord"|"escalade_samu", "confidence": 0.0-1.0}}"""

_REPORT_PROMPT = """You write the daily Vigie crisis cell report.

Today's data:
- Date: {date}
- Beneficiaries to contact: {total}
- Beneficiaries contacted: {contacted} ({coverage_pct}%)
- Check-in OK: {ok_count}
- Weak signals: {weak_count}
- Coordinator escalations: {coord_count}
- Critical escalations (SAMU): {samu_count}
- Average escalation latency: {avg_escalade_latency}
- Beneficiaries not contacted > 72h: {unreachable_72h}
- Weak signals to monitor tomorrow: {weak_signals_list}

Fresh health directives (RTS):
{rts_directives}

Write a report in 4 paragraphs:
1. Today's summary (1-2 sentences)
2. Points of attention (bullet list)
3. Recommendations for tomorrow (bullet list)
4. Cited sources (bullet list)

No Slack mark-up, just structured plain text."""


class SlackAIService:
    """Cognitive layer for Vigie — transcription, extraction, classification, reports."""

    def __init__(self) -> None:
        cfg = get_config().slack_ai
        self.use_native_slack_ai = cfg.enabled
        self.openai_key = cfg.openai_api_key.get_secret_value() if cfg.openai_api_key else None
        self.openai_model = cfg.openai_model
        self.whisper_model = cfg.openai_whisper_model

        if not self.use_native_slack_ai and not self.openai_key:
            log.warning("slack_ai.no_backend_configured")
        else:
            log.info(
                "slack_ai.configured",
                backend="slack_native" if self.use_native_slack_ai else "openai_fallback",
                model=cfg.model if self.use_native_slack_ai else self.openai_model,
            )

    async def transcribe_audio(self, file_bytes: bytes, filename: str) -> str:
        """
        Transcribe a voice note (audio file) to text.

        Tries Slack AI audio translation first, falls back to OpenAI Whisper.
        """
        if self.use_native_slack_ai:
            try:
                return await self._slack_ai_transcribe(file_bytes, filename)
            except Exception as e:
                log.warning("slack_ai.native_transcribe_failed", error=str(e))

        if self.openai_key:
            return await self._openai_whisper(file_bytes, filename)

        log.error("slack_ai.no_transcription_backend")
        raise RuntimeError("No transcription backend available")

    async def extract_structured(self, text: str) -> dict[str, Any]:
        """
        Extract structured data (state, signals, action) from a free-text note.

        Returns:
            {
                "state": "ok" | "weak_signal" | "needs_escalation" | "critical",
                "signals": [...],
                "action_required": "none" | "pharmacy_lookup" | ...,
                "confidence": 0.0-1.0
            }
        """
        prompt = _EXTRACT_PROMPT.format(text=text[:2000])
        raw = await self._chat_complete(prompt, json_mode=True)
        return _safe_json(raw, default={"state": "ok", "signals": [], "action_required": "none", "confidence": 0.5})

    async def classify_anomaly(self, text: str) -> tuple[int, list[str], str]:
        """
        Classify the anomaly level of a check-in note.

        Returns (level, signals, recommended_action).
        level: 0 (OK) / 1 (weak) / 2 (escalate coord) / 3 (SAMU)
        recommended: "ok" / "pharmacy" / "escalade_coord" / "escalade_samu"
        """
        prompt = _CLASSIFY_PROMPT.format(text=text[:2000])
        raw = await self._chat_complete(prompt, json_mode=True)
        parsed = _safe_json(
            raw,
            default={"level": 0, "signals": [], "recommended": "ok", "confidence": 0.5},
        )

        level = int(parsed.get("level", 0))
        level = max(0, min(3, level))
        signals = parsed.get("signals", []) or []
        recommended = parsed.get("recommended", "ok")
        valid_actions = {"ok", "pharmacy", "escalade_coord", "escalade_samu"}
        if recommended not in valid_actions:
            recommended = "ok" if level == 0 else "escalade_coord" if level == 2 else "escalade_samu"

        return level, signals, recommended

    async def generate_daily_report(
        self,
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
        rts_directives: list[str],
    ) -> str:
        """Generate the daily Vigie report for the crisis cell."""
        coverage_pct = int((contacted / total) * 100) if total > 0 else 0
        prompt = _REPORT_PROMPT.format(
            date=date,
            total=total,
            contacted=contacted,
            coverage_pct=coverage_pct,
            ok_count=ok_count,
            weak_count=weak_count,
            coord_count=coord_count,
            samu_count=samu_count,
            avg_escalade_latency=avg_escalade_latency,
            unreachable_72h=unreachable_72h,
            weak_signals_list=", ".join(weak_signals_list) or "none",
            rts_directives="\n".join(f"- {d}" for d in rts_directives) or "- (no fresh directives)",
        )
        return await self._chat_complete(prompt, json_mode=False, max_tokens=800)

    # ============================================================
    # Backend implementations
    # ============================================================

    async def _slack_ai_transcribe(self, file_bytes: bytes, filename: str) -> str:
        """
        Transcribe a voice note using Slack AI's native Assistant API.

        Slack's Assistant threads API (slack_sdk.web.async_client) lets
        a bot create a thread, post a file, and ask Slack AI to process
        it. We use this for transcription when the workspace has Slack AI
        enabled (assistant:write scope is in the manifest).

        If the workspace does not have Slack AI enabled, this raises
        SlackApiError, which the caller catches and falls back to OpenAI
        Whisper.
        """
        from slack_sdk.errors import SlackApiError
        from slack_sdk.web.async_client import AsyncWebClient

        cfg = get_config()
        client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())

        try:
            # Step 1: Upload the file to Slack
            upload_resp = await client.files_upload_v2(
                file=file_bytes,
                filename=filename,
                title=f"Voice note — {filename}",
                initial_comment="Transcription request via Vigie Slack AI.",
            )
            file_id = upload_resp.get("file", {}).get("id")
            if not file_id:
                raise RuntimeError("files_upload_v2 did not return a file id")

            # Step 2: Open an Assistant thread and ask Slack AI to transcribe
            # Slack AI Assistant uses the `assistant_threads` API.
            thread_resp = await client.assistant_threads_create(
                channel_id=cfg.slack.cellule_crise_channel_id or "",
                thread_ts="",  # New thread
            )
            thread_id = thread_resp.get("thread", {}).get("thread_ts") or thread_resp.get("ok")

            # Post the prompt to the thread
            prompt = (
                f"Transcribe this voice note in English, without added punctuation, "
                f"faithful to the original text. The file is `{filename}` (id: {file_id})."
            )
            await client.chat_postMessage(
                channel=cfg.slack.cellule_crise_channel_id or "",
                thread_ts=thread_id if isinstance(thread_id, str) else None,
                text=prompt,
            )

            # Poll for Slack AI's response (best-effort, with timeout)
            return await self._poll_slack_ai_response(client, cfg.slack.cellule_crise_channel_id or "", thread_id if isinstance(thread_id, str) else "", timeout=30.0)

        except SlackApiError as e:
            log.warning(
                "slack_ai.native_transcribe_failed",
                error=e.response.get("error") if e.response else str(e),
            )
            raise

    async def _poll_slack_ai_response(
        self,
        client,
        channel_id: str,
        thread_ts: str,
        timeout: float = 30.0,
    ) -> str:
        """Poll a Slack thread for the assistant's reply."""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                history = await client.conversations_replies(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    limit=10,
                )
                for msg in history.get("messages", []):
                    # Slack AI's responses are tagged with bot_id matching our app
                    if msg.get("subtype") == "slack_ai_response" or msg.get("bot_id"):
                        return msg.get("text", "")
            except Exception as e:
                log.debug("slack_ai.poll.error", error=str(e))
            await asyncio.sleep(1.5)

        raise RuntimeError("Slack AI response timeout")

    async def _openai_whisper(self, file_bytes: bytes, filename: str) -> str:
        """Transcribe with OpenAI Whisper-1."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_key)
        log.debug("slack_ai.whisper.call", filename=filename, bytes=len(file_bytes))
        try:
            result = await client.audio.transcriptions.create(
                model=self.whisper_model,
                file=(filename, file_bytes),
                language="en",
                prompt=_TRANSCRIBE_HINT,
            )
            return result.text
        finally:
            await client.close()

    async def _chat_complete(self, prompt: str, *, json_mode: bool, max_tokens: int = 400) -> str:
        """Chat completion via OpenAI (fallback for Slack AI native chat)."""
        if not self.openai_key:
            raise RuntimeError("No chat backend available (openai_api_key not set)")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_key)
        try:
            kwargs: dict[str, Any] = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = await client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        finally:
            await client.close()


def _safe_json(text: str, *, default: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON from a possibly-noisy model output. Returns default on failure."""
    if not text:
        return default
    text = text.strip()
    # Strip ```json fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        log.warning("slack_ai.json_parse_failed", text_preview=text[:200])
        return default


# Singleton accessor
_service: SlackAIService | None = None


def get_slack_ai_service() -> SlackAIService:
    """Return the shared SlackAIService instance."""
    global _service
    if _service is None:
        _service = SlackAIService()
    return _service
